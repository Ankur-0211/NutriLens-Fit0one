from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional

from backend.app.core.database import get_db
from backend.app.modules.auth.router import get_current_user_id
from backend.app.models.user import AppUser
from backend.app.models.improvement import DatasetVersion, ModelVersion
from backend.app.schemas.improvement import (
    FeedbackReviewSubmitRequest,
    DatasetBuildRequest,
    ModelStageTransitionRequest,
    IdentityMapWeightUpdateRequest,
    UserConsentUpdateRequest,
)
from backend.app.modules.improvement.etl import run_feedback_etl
from backend.app.modules.improvement.service import ModelImprovementService

router = APIRouter(tags=["Model Improvement & Ops"])

# -------------------------------------------------------------
# 1. Feedback ETL & Reviewer Endpoints (SDD Section 23.3, 23.5)
# -------------------------------------------------------------

@router.post("/admin/feedback/etl", summary="Run automated feedback ETL pipeline")
def trigger_feedback_etl(db: Session = Depends(get_db)):
    """
    Executes automated validation (consent, image decodability, dHash deduplication,
    leakage guards against frozen test sets, and culinary plausibility) and queues
    valid correction candidates for human review.
    """
    stats = run_feedback_etl(db)
    return {"status": "success", "summary": stats}

@router.get("/admin/feedback/pending", summary="List queued correction events for human review")
def list_pending_feedback_reviews(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """
    Fetches items queued by the automated ETL awaiting reviewer verification.
    """
    items = ModelImprovementService.list_pending_reviews(db, limit=limit, offset=offset)
    return {"total": len(items), "items": items}

@router.post("/admin/feedback/review", summary="Submit reviewer decision on a correction event")
def submit_feedback_review(
    payload: FeedbackReviewSubmitRequest,
    db: Session = Depends(get_db),
):
    """
    Records human reviewer decision ('accepted', 'rejected', 'escalated') and verified labels.
    """
    try:
        review = ModelImprovementService.submit_review_decision(
            db=db,
            correction_id=payload.correction_id,
            reviewer_id=None,
            decision=payload.decision,
            final_label=payload.final_label,
            cause=payload.cause,
            notes=payload.notes,
        )
        return {
            "status": "success",
            "review_id": review.id,
            "decision": review.decision,
            "cause": review.cause,
            "reviewed_at": review.reviewed_at.isoformat() if review.reviewed_at else None,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# -------------------------------------------------------------
# 2. Versioned Dataset Management (SDD Section 24.2, 24.3)
# -------------------------------------------------------------

@router.post("/admin/datasets/build", summary="Snapshot reviewed corrections into immutable dataset version")
def build_dataset_version(
    payload: DatasetBuildRequest,
    db: Session = Depends(get_db),
):
    """
    Snapshots approved correction samples into an immutable versioned dataset with
    group-aware train/val/test splitting to prevent intra-meal session leakage.
    """
    try:
        res = ModelImprovementService.build_dataset_version(
            db=db,
            version_id=payload.version_id,
            notes=payload.notes or "Dataset snapshot from feedback review",
            train_ratio=payload.train_ratio or 0.70,
            val_ratio=payload.val_ratio or 0.15,
            test_ratio=payload.test_ratio or 0.15,
        )
        return {"status": "success", "dataset": res}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/admin/datasets", summary="List dataset versions and sample counts")
def list_datasets(db: Session = Depends(get_db)):
    datasets = db.query(DatasetVersion).order_by(DatasetVersion.created_at.desc()).all()
    return {
        "datasets": [
            {
                "id": d.id,
                "dvc_ref": d.dvc_ref,
                "notes": d.notes,
                "num_samples": d.num_samples,
                "created_at": d.created_at.isoformat() if d.created_at else None,
            }
            for d in datasets
        ]
    }

# -------------------------------------------------------------
# 3. Model Registry & Promotion/Rollback (SDD Section 25.4)
# -------------------------------------------------------------

@router.get("/admin/models", summary="List model versions and lifecycle stages")
def list_model_versions(db: Session = Depends(get_db)):
    models = db.query(ModelVersion).order_by(ModelVersion.created_at.desc()).all()
    return {
        "models": [
            {
                "id": m.id,
                "kind": m.kind,
                "stage": m.stage,
                "active_traffic_pct": m.active_traffic_pct,
                "labelset_version": m.labelset_version,
                "dataset_version": m.dataset_version,
                "metrics": m.metrics,
                "notes": m.notes,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in models
        ]
    }

@router.post("/admin/models/stage", summary="Promote, canary, or rollback model version stage")
def transition_model_stage(
    payload: ModelStageTransitionRequest,
    db: Session = Depends(get_db),
):
    """
    Transitions model version stage: 'staging' -> 'shadow' -> 'canary' -> 'production' -> 'archived'.
    Promoting to production automatically archives older production models, ensuring clean rollback trails.
    """
    try:
        res = ModelImprovementService.manage_model_stage(
            db=db,
            model_id=payload.model_id,
            target_stage=payload.target_stage,
            traffic_pct=payload.traffic_pct or 0.0,
        )
        return {"status": "success", "model": res}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# -------------------------------------------------------------
# 4. Online Error Analytics & Non-Retraining Fixes (SDD 23.5)
# -------------------------------------------------------------

@router.get("/admin/analytics/errors", summary="Get model error attribution and confusion analytics")
def get_model_error_analytics(db: Session = Depends(get_db)):
    """
    Computes top confusion pairs, portion estimation bias, and review triage statistics.
    """
    analytics = ModelImprovementService.get_error_analytics(db)
    return {"status": "success", "analytics": analytics}

@router.post("/admin/identity-map/update", summary="Update visual class mapping weights without retraining")
def update_identity_mapping(
    payload: IdentityMapWeightUpdateRequest,
    db: Session = Depends(get_db),
):
    """
    Updates or creates a VisualClassMapping (ADR-009 / SDD Section 23.5).
    Resolves mapping errors online with zero retraining required.
    """
    res = ModelImprovementService.update_identity_map_weight(
        db=db,
        visual_class_id=payload.visual_class_id,
        food_variant_id=payload.food_variant_id,
        weight=payload.weight,
        is_default=payload.is_default or False,
    )
    return {"status": "success", "mapping": res}

# -------------------------------------------------------------
# 5. User Training Consent Toggle (SDD Section 23.1, 23.3)
# -------------------------------------------------------------

@router.patch("/users/me/consent", summary="Update user training data consent")
def update_training_consent(
    payload: UserConsentUpdateRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    Toggles the user's consent for using meal images in model improvement training datasets.
    """
    user = db.query(AppUser).filter(AppUser.id == user_id).first()
    if not user:
        user = AppUser(
            id=user_id,
            email=f"{user_id}@nutrilens.ai",
            display_name="User",
            training_consent=payload.training_consent,
        )
        db.add(user)
    else:
        user.training_consent = payload.training_consent
    db.commit()
    return {
        "status": "success",
        "user_id": user.id,
        "training_consent": user.training_consent,
    }
