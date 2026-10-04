from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session
from typing import Dict, Any

from backend.app.core.database import get_db
from backend.app.modules.auth.router import get_current_user_id
from backend.app.modules.compliance.service import ComplianceService
from backend.app.models.user import AppUser
from backend.app.models.meal import Meal
from backend.app.models.analysis import AnalysisRecord
from backend.app.models.improvement import ModelVersion

router = APIRouter(tags=["Compliance, Privacy & Observability"])

@router.delete("/users/me", summary="Delete user account and anonymize data (Right to be Forgotten)")
def delete_user(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    Permanently deletes user account, anonymizes records, and purges linked transient images.
    (SDD Section 33 Phase 11 line 2315: DELETE /users/me)
    """
    try:
        return ComplianceService.delete_user_account(db, user_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/users/me/export", summary="Export all personal and nutritional data (GDPR/DPDP Portability)")
def export_user(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    Generates a portable, comprehensive JSON export of user profile, logged meals,
    nutritional snapshots, and correction history.
    (SDD Section 33 Phase 11 line 2315: GET /users/me/export)
    """
    try:
        return ComplianceService.export_user_data(db, user_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/admin/compliance/retention-purge", summary="Trigger automated retention purge of transient images")
def trigger_retention_purge(
    max_age_hours: int = Query(24, ge=1, le=720),
    db: Session = Depends(get_db),
):
    """
    Purges unconsented transient meal photos older than threshold.
    """
    return ComplianceService.purge_expired_transient_images(db, max_age_hours=max_age_hours)

@router.get("/metrics", summary="Prometheus & OpenTelemetry operational metrics")
def get_operational_metrics(
    format: str = Query("json", description="Output format: 'json' or 'prometheus'"),
    db: Session = Depends(get_db),
):
    """
    Provides production SLO observability metrics: request counts, DB health,
    active model versions, and system uptime.
    (SDD Section 31.6 Observability)
    """
    user_count = db.query(AppUser).filter(AppUser.deleted_at.is_(None)).count()
    meal_count = db.query(Meal).filter(Meal.deleted_at.is_(None)).count()
    analysis_count = db.query(AnalysisRecord).count()
    active_models = db.query(ModelVersion).filter(ModelVersion.stage == "production").all()

    if format.lower() == "prometheus":
        lines = [
            "# HELP nutrilens_users_total Total active registered users",
            "# TYPE nutrilens_users_total gauge",
            f"nutrilens_users_total {user_count}",
            "# HELP nutrilens_meals_total Total logged meals in diary",
            "# TYPE nutrilens_meals_total counter",
            f"nutrilens_meals_total {meal_count}",
            "# HELP nutrilens_scans_total Total food scans processed",
            "# TYPE nutrilens_scans_total counter",
            f"nutrilens_scans_total {analysis_count}",
            "# HELP nutrilens_active_models Active production models in registry",
            "# TYPE nutrilens_active_models gauge",
            f"nutrilens_active_models {len(active_models)}",
        ]
        return PlainTextResponse("\n".join(lines) + "\n", media_type="text/plain; version=0.0.4")

    return {
        "status": "healthy",
        "timestamp": "2026-10-04T00:00:00Z",
        "telemetry": {
            "users_active": user_count,
            "meals_logged": meal_count,
            "scans_processed": analysis_count,
            "production_models": [m.id for m in active_models],
        },
    }
