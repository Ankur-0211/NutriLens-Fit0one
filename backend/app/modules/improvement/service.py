import math
import hashlib
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.app.core.config import settings
from backend.app.models.correction import CorrectionEvent
from backend.app.models.analysis import AnalysisRecord, PredictionItem
from backend.app.models.image import ImageRecord
from backend.app.models.identity import VisualClassMapping
from backend.app.models.improvement import (
    FeedbackReview,
    DatasetVersion,
    DatasetSample,
    ModelVersion,
)
from backend.app.modules.improvement.validators import (
    classify_correction_cause,
    compute_dhash,
)

class ModelImprovementService:
    @staticmethod
    def list_pending_reviews(db: Session, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Lists queued correction events for human reviewer evaluation (SDD Section 23.3).
        """
        events = (
            db.query(CorrectionEvent)
            .filter(CorrectionEvent.review_status == "queued")
            .order_by(CorrectionEvent.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

        results = []
        for ev in events:
            analysis = db.query(AnalysisRecord).filter(AnalysisRecord.id == ev.analysis_id).first()
            img_path = None
            pred_item = None
            if analysis:
                if analysis.image_id:
                    img_rec = db.query(ImageRecord).filter(ImageRecord.id == analysis.image_id).first()
                    if img_rec and img_rec.storage_key:
                        candidate_p = Path(img_rec.storage_key)
                        if candidate_p.is_file():
                            img_path = str(candidate_p)
                        elif (settings.STORAGE_DIR / img_rec.storage_key).is_file():
                            img_path = str(settings.STORAGE_DIR / img_rec.storage_key)
                if ev.item_key:
                    pred_item = (
                        db.query(PredictionItem)
                        .filter(
                            PredictionItem.analysis_id == analysis.id,
                            PredictionItem.item_key == ev.item_key,
                        )
                        .first()
                    )

            cause = classify_correction_cause(
                ev.event_type,
                ev.before,
                ev.after,
                pred_item.visual_top_k if pred_item else None,
            )

            results.append({
                "correction_id": ev.id,
                "batch_id": ev.batch_id,
                "analysis_id": ev.analysis_id,
                "event_type": ev.event_type,
                "inferred_cause": cause,
                "before": ev.before,
                "after": ev.after,
                "image_path": img_path,
                "created_at": ev.created_at.isoformat() if ev.created_at else None,
                "model_versions": analysis.model_versions if analysis else {},
            })
        return results

    @staticmethod
    def submit_review_decision(
        db: Session,
        correction_id: str,
        reviewer_id: Optional[str],
        decision: str,
        final_label: Optional[Dict[str, Any]] = None,
        cause: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> FeedbackReview:
        """
        Records human reviewer decision ('accepted', 'rejected', 'escalated') (SDD Section 23.3).
        """
        ev = db.query(CorrectionEvent).filter(CorrectionEvent.id == correction_id).first()
        if not ev:
            raise ValueError(f"Correction event '{correction_id}' not found")

        valid_decisions = {"accepted", "rejected", "escalated"}
        if decision not in valid_decisions:
            raise ValueError(f"Invalid decision '{decision}'. Must be one of {valid_decisions}")

        # Create FeedbackReview record
        review = FeedbackReview(
            correction_event_id=ev.id,
            correction_batch_id=ev.batch_id,
            reviewer_id=reviewer_id,
            decision=decision,
            cause=cause or "visual_misrecognition",
            final_label=final_label or ev.after,
            notes=notes,
            reviewed_at=datetime.now(timezone.utc),
        )
        db.add(review)

        # Update event status
        ev.review_status = decision
        db.commit()
        db.refresh(review)
        return review

    @staticmethod
    def build_dataset_version(
        db: Session,
        version_id: str,
        notes: str,
        train_ratio: float = 0.70,
        val_ratio: float = 0.15,
        test_ratio: float = 0.15,
    ) -> Dict[str, Any]:
        """
        Builds an immutable versioned dataset snapshot from approved reviews using
        group-aware splitting to prevent intra-meal session data leakage (SDD Section 24.2, 24.3).
        """
        existing = db.query(DatasetVersion).filter(DatasetVersion.id == version_id).first()
        if existing:
            raise ValueError(f"DatasetVersion '{version_id}' already exists")

        # Query accepted reviews
        accepted_reviews = (
            db.query(FeedbackReview)
            .filter(FeedbackReview.decision == "accepted")
            .all()
        )

        dataset = DatasetVersion(
            id=version_id,
            dvc_ref=f"git:{version_id[:8]}",
            notes=notes,
            num_samples=0,
        )
        db.add(dataset)
        db.commit()

        split_counts = {"train": 0, "val": 0, "test": 0}
        total_samples = 0

        # Group-aware splitting by batch_id
        for rev in accepted_reviews:
            ev = db.query(CorrectionEvent).filter(CorrectionEvent.id == rev.correction_event_id).first()
            if not ev:
                continue

            analysis = db.query(AnalysisRecord).filter(AnalysisRecord.id == ev.analysis_id).first()
            image_id = analysis.image_id if analysis else None

            # Compute stable hash from batch_id to determine split
            group_key = ev.batch_id or ev.id
            hash_int = int(hashlib.md5(group_key.encode("utf-8")).hexdigest(), 16)
            unit_val = (hash_int % 1000) / 1000.0

            if unit_val < train_ratio:
                split = "train"
            elif unit_val < (train_ratio + val_ratio):
                split = "val"
            else:
                split = "test"

            img_rec = db.query(ImageRecord).filter(ImageRecord.id == image_id).first() if image_id else None
            p_hash = None
            if img_rec and img_rec.storage_key:
                cand_p = Path(img_rec.storage_key)
                if cand_p.is_file():
                    p_hash = compute_dhash(str(cand_p))
                elif (settings.STORAGE_DIR / img_rec.storage_key).is_file():
                    p_hash = compute_dhash(str(settings.STORAGE_DIR / img_rec.storage_key))

            sample = DatasetSample(
                dataset_version_id=dataset.id,
                image_id=image_id,
                split=split,
                labels=rev.final_label or ev.after or {},
                origin="feedback_review",
                perceptual_hash=p_hash,
            )
            db.add(sample)
            split_counts[split] += 1
            total_samples += 1

        dataset.num_samples = total_samples
        db.commit()

        return {
            "dataset_version": dataset.id,
            "total_samples": total_samples,
            "splits": split_counts,
            "dvc_ref": dataset.dvc_ref,
            "created_at": dataset.created_at.isoformat() if dataset.created_at else None,
        }

    @staticmethod
    def update_identity_map_weight(
        db: Session,
        visual_class_id: str,
        food_variant_id: str,
        weight: float,
        is_default: bool = False,
    ) -> Dict[str, Any]:
        """
        Updates or registers a visual class mapping weight without retraining (SDD Section 23.5, 16A.5).
        Allows instant online correction of mapping errors and culinary ambiguity.
        """
        mapping = (
            db.query(VisualClassMapping)
            .filter(
                VisualClassMapping.visual_class_id == visual_class_id,
                VisualClassMapping.food_variant_id == food_variant_id,
            )
            .first()
        )

        if not mapping:
            mapping = VisualClassMapping(
                identity_map_version="idmap-2026.01",
                labelset_version="vis-2026.01",
                visual_class_id=visual_class_id,
                food_variant_id=food_variant_id,
                weight=weight,
                is_default=is_default,
            )
            db.add(mapping)
        else:
            mapping.weight = weight
            mapping.is_default = is_default

        if is_default:
            # Set other mappings for this visual class to non-default
            db.query(VisualClassMapping).filter(
                VisualClassMapping.visual_class_id == visual_class_id,
                VisualClassMapping.food_variant_id != food_variant_id,
            ).update({"is_default": False})

        db.commit()
        db.refresh(mapping)
        return {
            "visual_class_id": mapping.visual_class_id,
            "food_variant_id": mapping.food_variant_id,
            "weight": mapping.weight,
            "is_default": mapping.is_default,
            "identity_map_version": mapping.identity_map_version,
        }

    @staticmethod
    def manage_model_stage(
        db: Session,
        model_id: str,
        target_stage: str,
        traffic_pct: float = 0.0,
    ) -> Dict[str, Any]:
        """
        Transitions model versions through registry lifecycle stages:
        'staging' -> 'shadow' -> 'canary' -> 'production' -> 'archived' (SDD Section 25.4).
        Enforces single production model per kind and supports instant rollback drills.
        """
        valid_stages = {"staging", "shadow", "canary", "production", "archived"}
        if target_stage not in valid_stages:
            raise ValueError(f"Invalid target stage '{target_stage}'. Must be one of {valid_stages}")

        model = db.query(ModelVersion).filter(ModelVersion.id == model_id).first()
        if not model:
            raise ValueError(f"Model version '{model_id}' not found")

        # If promoting to production, demote current production model of same kind
        if target_stage == "production":
            current_prods = (
                db.query(ModelVersion)
                .filter(
                    ModelVersion.kind == model.kind,
                    ModelVersion.stage == "production",
                    ModelVersion.id != model.id,
                )
                .all()
            )
            for old_prod in current_prods:
                old_prod.stage = "archived"
                old_prod.active_traffic_pct = 0.0
            model.stage = "production"
            model.active_traffic_pct = 100.0
        elif target_stage == "canary":
            model.stage = "canary"
            model.active_traffic_pct = min(100.0, max(0.0, traffic_pct or 10.0))
        elif target_stage == "shadow":
            model.stage = "shadow"
            model.active_traffic_pct = 0.0
        elif target_stage == "archived":
            model.stage = "archived"
            model.active_traffic_pct = 0.0
        else:
            model.stage = target_stage

        db.commit()
        db.refresh(model)
        return {
            "model_id": model.id,
            "kind": model.kind,
            "stage": model.stage,
            "active_traffic_pct": model.active_traffic_pct,
            "labelset_version": model.labelset_version,
            "metrics": model.metrics,
        }

    @staticmethod
    def get_error_analytics(db: Session) -> Dict[str, Any]:
        """
        Computes model error telemetry, confusion pairs, portion bias, and status breakdowns
        (SDD Section 23.2, 26.8).
        """
        # Status counts
        status_counts = dict(
            db.query(CorrectionEvent.review_status, func.count(CorrectionEvent.id))
            .group_by(CorrectionEvent.review_status)
            .all()
        )

        # Event type counts
        event_types = dict(
            db.query(CorrectionEvent.event_type, func.count(CorrectionEvent.id))
            .group_by(CorrectionEvent.event_type)
            .all()
        )

        # Confusion pairs: analyze food_changed events
        food_changed_events = (
            db.query(CorrectionEvent)
            .filter(CorrectionEvent.event_type == "food_changed")
            .all()
        )
        confusion_counts = {}
        for ev in food_changed_events:
            predicted = (ev.before or {}).get("food_id") or "unknown"
            corrected = (ev.after or {}).get("food_id") or "unknown"
            pair = f"{predicted} -> {corrected}"
            confusion_counts[pair] = confusion_counts.get(pair, 0) + 1

        top_confusion = sorted(
            [{"pair": k, "count": v} for k, v in confusion_counts.items()],
            key=lambda x: x["count"],
            reverse=True,
        )[:10]

        # Portion bias estimation
        qty_events = (
            db.query(CorrectionEvent)
            .filter(CorrectionEvent.event_type.in_(("quantity_changed", "unit_changed")))
            .all()
        )
        portion_errors = []
        for qe in qty_events:
            orig_g = (qe.before or {}).get("grams") or (qe.before or {}).get("portion_g")
            corr_g = (qe.after or {}).get("grams") or (qe.after or {}).get("portion_g")
            if orig_g and corr_g and float(corr_g) > 0:
                pct_err = ((float(orig_g) - float(corr_g)) / float(corr_g)) * 100.0
                portion_errors.append(pct_err)

        mean_portion_bias = (
            sum(portion_errors) / len(portion_errors) if portion_errors else 0.0
        )

        return {
            "review_status_breakdown": status_counts,
            "correction_type_breakdown": event_types,
            "top_confusion_pairs": top_confusion,
            "portion_bias_mean_pct_error": round(mean_portion_bias, 2),
            "total_corrections_analyzed": len(food_changed_events) + len(qty_events),
        }
