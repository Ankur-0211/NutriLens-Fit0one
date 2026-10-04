from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, ConfigDict

class FeedbackReviewSubmitRequest(BaseModel):
    correction_id: str
    decision: str = Field(..., description="accepted, rejected, or escalated")
    cause: Optional[str] = Field(None, description="visual_misrecognition, mapping_error, variant_ambiguity, taxonomy_gap, user_error")
    final_label: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None

class FeedbackReviewResponse(BaseModel):
    id: str
    correction_event_id: Optional[str]
    decision: str
    cause: Optional[str]
    notes: Optional[str]
    reviewed_at: Optional[str]

    model_config = ConfigDict(from_attributes=True)

class DatasetBuildRequest(BaseModel):
    version_id: str = Field(..., description="e.g. ds-2026.02")
    notes: Optional[str] = "Versioned dataset snapshot generated from reviewed corrections"
    train_ratio: Optional[float] = 0.70
    val_ratio: Optional[float] = 0.15
    test_ratio: Optional[float] = 0.15

class ModelStageTransitionRequest(BaseModel):
    model_id: str
    target_stage: str = Field(..., description="staging, shadow, canary, production, or archived")
    traffic_pct: Optional[float] = Field(0.0, description="Canary traffic percentage (0.0 to 100.0)")

class IdentityMapWeightUpdateRequest(BaseModel):
    visual_class_id: str
    food_variant_id: str
    weight: float = Field(..., ge=0.0, le=1.0)
    is_default: Optional[bool] = False

class UserConsentUpdateRequest(BaseModel):
    training_consent: bool
