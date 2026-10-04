from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from backend.app.core.database import get_db
from backend.app.core.config import settings

router = APIRouter(tags=["health"])

@router.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.PROJECT_VERSION,
        "schema_version": settings.SCHEMA_VERSION,
    }

@router.get("/ready")
def readiness_check(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    return {
        "status": "ready" if db_status == "connected" else "degraded",
        "database": db_status,
        "model_versions": {
            "detector": settings.DETECTOR_MODEL_VERSION,
            "classifier": settings.CLASSIFIER_MODEL_VERSION,
            "portion": settings.PORTION_MODEL_VERSION,
            "resolver": settings.RESOLVER_VERSION,
            "identity_map": settings.IDENTITY_MAP_VERSION,
            "nutrition_db": settings.NUTRITION_DB_VERSION,
        },
    }
