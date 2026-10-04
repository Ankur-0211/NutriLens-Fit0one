from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
from backend.app.schemas.analysis import AnalysisResponse

class CorrectionEventItem(BaseModel):
    type: str  # food_changed, variant_changed, quantity_changed, unit_changed, item_added, item_removed, confirmed_unchanged
    item_id: Optional[str] = None
    food_id: Optional[str] = None
    variant_id: Optional[str] = None
    quantity: Optional[float] = None
    unit: Optional[str] = None
    grams: Optional[float] = None
    region_hint: Optional[List[float]] = None
    from_: Optional[Dict[str, Any]] = Field(None, alias="from")
    to: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(populate_by_name=True)

class CorrectionRequest(BaseModel):
    analysis_id: str
    events: List[CorrectionEventItem]
    client_ts: Optional[str] = None

class CorrectionResponse(BaseModel):
    correction_batch_id: str
    recalculated: AnalysisResponse
