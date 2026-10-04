from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class ServingUnitSchema(BaseModel):
    unit: str
    grams: float
    label: Optional[str] = None
    confidence: Optional[str] = "high"

class VariantSummarySchema(BaseModel):
    variant_id: str
    label: str
    preparation: Optional[str] = None
    is_default: bool
    energy_kcal: float
    kcal_min: Optional[float] = None
    kcal_max: Optional[float] = None
    protein_g: float
    carbs_g: float
    fat_g: float

class FoodSearchItemSchema(BaseModel):
    food_id: str
    display_name: str
    category: Optional[str] = None
    is_countable: bool
    default_unit: str
    default_grams: float
    energy_kcal_per_100g: float
    protein_g_per_100g: float
    carbs_g_per_100g: float
    fat_g_per_100g: float
    matched_alias: Optional[str] = None

class FoodDetailSchema(BaseModel):
    food_id: str
    display_name: str
    category: Optional[str] = None
    is_countable: bool
    default_unit: str
    default_grams: float
    density_g_per_ml: Optional[float] = None
    aliases: List[str] = []
    serving_units: List[ServingUnitSchema] = []
    variants: List[VariantSummarySchema] = []

class NutritionCalculateItem(BaseModel):
    food_id: str
    variant_id: Optional[str] = None
    quantity: float = Field(..., gt=0, le=5000)
    unit: str = "g"

class NutritionCalculateRequest(BaseModel):
    items: List[NutritionCalculateItem]

class NutrientValue(BaseModel):
    value: Optional[float] = None
    range: Optional[List[float]] = None
    availability: Optional[str] = "available"  # 'available' or 'missing'

class ItemNutrition(BaseModel):
    energy_kcal: NutrientValue
    protein_g: NutrientValue
    carbs_g: NutrientValue
    fat_g: NutrientValue
    fiber_g: NutrientValue
    sugar_g: NutrientValue
    sodium_mg: NutrientValue
    micros: Dict[str, NutrientValue] = {}
    confidence: Dict[str, Any] = {"level": "high", "score": 0.9}
    sources: List[str] = []

class CalculatedItemResult(BaseModel):
    food_id: str
    variant_id: str
    name: str
    quantity: float
    unit: str
    grams: float
    nutrition: ItemNutrition

class NutritionTotals(BaseModel):
    energy_kcal: NutrientValue
    protein_g: NutrientValue
    carbs_g: NutrientValue
    fat_g: NutrientValue
    fiber_g: Optional[NutrientValue] = None
    sodium_mg: Optional[NutrientValue] = None

class NutritionCalculateResponse(BaseModel):
    items: List[CalculatedItemResult]
    totals: NutritionTotals
    disclaimer: str = "Nutrition values are estimates."
