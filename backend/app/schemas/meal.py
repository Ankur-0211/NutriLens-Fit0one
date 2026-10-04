from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime, date
from backend.app.schemas.food import ItemNutrition, NutritionTotals

class MealItemCreate(BaseModel):
    food_id: str
    variant_id: Optional[str] = None
    grams: float
    unit: Optional[str] = "g"
    unit_qty: Optional[float] = None
    source: Optional[str] = "user_corrected"  # ai, user_corrected, manual
    item_key: Optional[str] = None

class MealCreateRequest(BaseModel):
    analysis_id: Optional[str] = None
    meal_type: str  # 'breakfast', 'lunch', 'dinner', 'snack'
    eaten_at: Optional[datetime] = None
    items: List[MealItemCreate]
    notes: Optional[str] = None

class MealItemResponse(BaseModel):
    id: str
    food_id: str
    food_name: str
    variant_id: Optional[str]
    grams: float
    unit: Optional[str]
    unit_qty: Optional[float]
    source: str
    nutrition_snapshot: ItemNutrition
    item_key: Optional[str]

class MealResponse(BaseModel):
    id: str
    user_id: Optional[str]
    analysis_id: Optional[str]
    meal_type: str
    eaten_at: datetime
    local_date: date
    notes: Optional[str]
    totals: NutritionTotals
    items: List[MealItemResponse]
    nutrition_db_version: str
    created_at: datetime

class DailyMealBreakdown(BaseModel):
    energy_kcal: float
    protein_g: float
    carbs_g: float
    fat_g: float
    items_count: int

class DailyNutritionResponse(BaseModel):
    date: str
    totals: NutritionTotals
    by_meal: Dict[str, DailyMealBreakdown]
    meals: List[MealResponse]
    micro_coverage: float
