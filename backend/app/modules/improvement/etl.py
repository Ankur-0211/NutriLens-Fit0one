import os
from pathlib import Path
from typing import Dict, Any, List
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.models.user import AppUser
from backend.app.models.image import ImageRecord
from backend.app.models.analysis import AnalysisRecord, PredictionItem
from backend.app.models.correction import CorrectionEvent
from backend.app.models.improvement import DatasetSample
from backend.app.modules.improvement.validators import (
    validate_image_decodable,
    compute_dhash,
    check_duplicate_or_leakage,
    validate_correction_plausibility,
    classify_correction_cause,
)

def run_feedback_etl(db: Session) -> Dict[str, Any]:
    """
    Executes the automated Feedback ETL pipeline (SDD Section 23.3).
    Extracts pending correction events, applies automated validation filters
    (consent, image decodability, dHash deduplication, test-set leakage guards,
    and culinary plausibility), routes the technical cause, and queues
    valid candidates for human reviewer sign-off.
    """
    pending_events: List[CorrectionEvent] = (
        db.query(CorrectionEvent)
        .filter(CorrectionEvent.review_status == "pending")
        .all()
    )

    stats = {
        "processed": len(pending_events),
        "queued": 0,
        "auto_rejected": 0,
        "consent_declined": 0,
        "reasons": {},
    }

    if not pending_events:
        return stats

    # Pre-fetch existing dataset hashes to guard against leakage and duplicates
    existing_samples = db.query(DatasetSample).all()
    frozen_test_hashes = [
        s.perceptual_hash for s in existing_samples if s.split == "test" and s.perceptual_hash
    ]
    train_pool_hashes = [
        s.perceptual_hash for s in existing_samples if s.split in ("train", "val") and s.perceptual_hash
    ]

    for event in pending_events:
        # 1. User Consent Verification (SDD Section 23.3 Collection standard)
        if event.user_id:
            user = db.query(AppUser).filter(AppUser.id == event.user_id).first()
            if user and not user.training_consent:
                event.review_status = "consent_declined"
                stats["consent_declined"] += 1
                continue

        # 2. Plausibility validation on user data (quantity bounds & taxonomy)
        is_plausible, plausibility_err = validate_correction_plausibility(
            event.event_type, event.before, event.after, db
        )
        if not is_plausible:
            event.review_status = "auto_rejected"
            stats["auto_rejected"] += 1
            stats["reasons"][plausibility_err] = stats["reasons"].get(plausibility_err, 0) + 1
            continue

        # 3. Image validation & Perceptual Hashing (if linked to an image)
        analysis = db.query(AnalysisRecord).filter(AnalysisRecord.id == event.analysis_id).first()
        image_rec = None
        if analysis and analysis.image_id:
            image_rec = db.query(ImageRecord).filter(ImageRecord.id == analysis.image_id).first()

        img_path = None
        if image_rec and image_rec.storage_key:
            candidate_p = Path(image_rec.storage_key)
            if candidate_p.is_file():
                img_path = str(candidate_p)
            elif (settings.STORAGE_DIR / image_rec.storage_key).is_file():
                img_path = str(settings.STORAGE_DIR / image_rec.storage_key)

        if img_path:
            is_valid_img, img_err, _, _ = validate_image_decodable(img_path)
            if not is_valid_img:
                event.review_status = "auto_rejected"
                stats["auto_rejected"] += 1
                stats["reasons"][img_err] = stats["reasons"].get(img_err, 0) + 1
                continue

            # Perceptual hash and leakage check
            img_hash = compute_dhash(img_path)
            violates, viol_type, viol_reason = check_duplicate_or_leakage(
                img_hash, train_pool_hashes, frozen_test_hashes, threshold=5
            )
            if violates:
                event.review_status = "auto_rejected"
                stats["auto_rejected"] += 1
                stats["reasons"][viol_reason] = stats["reasons"].get(viol_reason, 0) + 1
                continue

        # 4. Technical cause routing (SDD Section 23.5)
        # Look up visual prediction details if available
        visual_top_k = None
        if analysis and event.item_key:
            pred_item = (
                db.query(PredictionItem)
                .filter(
                    PredictionItem.analysis_id == analysis.id,
                    PredictionItem.item_key == event.item_key,
                )
                .first()
            )
            if pred_item:
                visual_top_k = pred_item.visual_top_k

        cause = classify_correction_cause(
            event.event_type, event.before, event.after, visual_top_k
        )

        # 5. Passed all automated validation gates -> Queue for reviewer
        event.review_status = "queued"
        stats["queued"] += 1

    db.commit()
    return stats
