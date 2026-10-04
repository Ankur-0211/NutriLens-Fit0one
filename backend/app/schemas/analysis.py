from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from backend.app.schemas.food import ItemNutrition, NutritionTotals, NutrientValue

class AnalysisClientMeta(BaseModel):
    platform: Optional[str] = "web"
    app_version: Optional[str] = "1.0.0"

class AnalysisMetadata(BaseModel):
    captured_at: Optional[str] = None
    meal_type_hint: Optional[str] = "lunch"
    client: Optional[AnalysisClientMeta] = None
    reference_object: Optional[str] = None
    consent_training: bool = False

class RegionSchema(BaseModel):
    bbox: Optional[List[float]] = None  # [ymin, xmin, ymax, xmax] or [x, y, w, h] normalized
    mask_rle: Optional[str] = None

class VisualInfo(BaseModel):
    visual_class_id: str
    score: float

class VariantAlternative(BaseModel):
    variant_id: str
    label: Optional[str] = None
    kcal: Optional[float] = None

class IdentityInfo(BaseModel):
    resolver: str = "idr-0.1.0"
    ambiguity: str = "none"  # 'variant', 'food', 'none'
    variant_alternatives: List[VariantAlternative] = []

class FoodAlternative(BaseModel):
    food_id: str
    name: Optional[str] = None
    score: float

class ConfidenceInfo(BaseModel):
    level: str = "medium"  # 'high', 'medium', 'low'
    score: float = 0.85

class FoodIdentityResult(BaseModel):
    visual: VisualInfo
    food_id: str
    variant_id: str
    name: str
    identity: IdentityInfo
    confidence: ConfidenceInfo
    alternatives: List[FoodAlternative] = []

class PortionUnit(BaseModel):
    unit: str
    qty: float

class PortionResult(BaseModel):
    grams: float
    range_g: List[float]
    unit: PortionUnit
    confidence: ConfidenceInfo
    method: str = "bowl_fill+regressor"

class AnalysisItem(BaseModel):
    item_id: str
    region: RegionSchema
    food: FoodIdentityResult
    portion: PortionResult
    nutrition: ItemNutrition
    flags: List[str] = []

class ImageQualityInfo(BaseModel):
    score: float = 0.9
    warnings: List[str] = []

class AnalysisResponse(BaseModel):
    schema_version: str = "1.0"
    analysis_id: str
    image_id: Optional[str] = None
    model_versions: Dict[str, Any]
    image_quality: ImageQualityInfo
    items: List[AnalysisItem]
    totals: NutritionTotals
    disclaimer: str = "Nutrition values are estimates."
