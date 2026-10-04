import json
from fastapi import APIRouter, File, UploadFile, Form, Depends, Header, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from backend.app.core.database import get_db
from backend.app.core.rate_limit import rate_limit_guard
from backend.app.modules.analysis.pipeline import AnalysisPipeline
from backend.app.schemas.analysis import AnalysisResponse, AnalysisMetadata

router = APIRouter(prefix="/food", tags=["analysis"])

@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_food(
    image: UploadFile = File(..., description="Food image file (JPEG, PNG, WebP)"),
    meta: Optional[str] = Form(None, description="Metadata JSON string"),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
    _rate_limit: bool = Depends(rate_limit_guard(limit=30, window_seconds=3600, quota_name="food_analyze")),
):
    image_bytes = await image.read()
    meta_obj = None
    if meta:
        try:
            parsed = json.loads(meta)
            meta_obj = AnalysisMetadata(**parsed)
        except Exception:
            pass

    pipeline = AnalysisPipeline(db)
    response = pipeline.run_pipeline(image_bytes=image_bytes, meta=meta_obj)
    return response
