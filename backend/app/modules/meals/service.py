import uuid
from datetime import datetime, timezone, date
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.app.core.config import settings
from backend.app.core.errors import NutriLensException
from backend.app.models.meal import Meal, MealItem
from backend.app.models.nutrition import Food
from backend.app.modules.nutrition.engine import NutritionEngine
from backend.app.modules.nutrition.repository import FoodRepository
from backend.app.schemas.meal import (
    MealCreateRequest,
    MealResponse,
    MealItemResponse,
    DailyNutritionResponse,
    DailyMealBreakdown,
)
from backend.app.schemas.food import ItemNutrition, NutritionTotals, NutrientValue

class MealService:
    def __init__(self, db: Session):
        self.db = db
        self.food_repo = FoodRepository(db)
        self.engine = NutritionEngine()

    def create_meal(self, payload: MealCreateRequest, user_id: Optional[str] = None) -> MealResponse:
        meal_id = str(uuid.uuid4())
        eaten_at = payload.eaten_at or datetime.now(timezone.utc)
        local_date = eaten_at.date()

        items_nutrition: List[ItemNutrition] = []
        meal_items: List[MealItem] = []

        for item_data in payload.items:
            food_detail = self.food_repo.get_food_detail(item_data.food_id)
            if not food_detail:
                # Auto-register unseeded food from CV / user diary so logging never fails
                new_food = Food(
                    id=item_data.food_id,
                    display_name=item_data.food_id.replace("_", " ").title(),
                    category_id=6,
                    is_countable=False,
                    default_unit=item_data.unit or "g",
                    default_grams=item_data.grams or 100.0,
                    status="active",
                )
                self.db.add(new_food)
                self.db.commit()
                food_detail = self.food_repo.get_food_detail(item_data.food_id)

            variant, profile = self.food_repo.get_variant_profile(
                food_id=item_data.food_id,
                variant_id=item_data.variant_id,
            )

            # Recompute grams accurately
            unit = item_data.unit or "g"
            unit_qty = item_data.unit_qty or item_data.grams
            grams = item_data.grams
            if unit != "g" and unit_qty:
                grams = self.food_repo.convert_to_grams(item_data.food_id, unit_qty, unit)

            if profile:
                profile_dict = {
                    "basis_g": float(profile.basis_g),
                    "energy_kcal": float(profile.energy_kcal),
                    "kcal_min": float(profile.kcal_min) if profile.kcal_min else None,
                    "kcal_max": float(profile.kcal_max) if profile.kcal_max else None,
                    "protein_g": float(profile.protein_g),
                    "carbs_g": float(profile.carbs_g),
                    "fat_g": float(profile.fat_g),
                    "fiber_g": float(profile.fiber_g),
                    "sugar_g": float(profile.sugar_g),
                    "sodium_mg": float(profile.sodium_mg),
                    "micros": profile.micros or {},
                }
                nut = self.engine.calculate_item_nutrition(
                    profile=profile_dict,
                    grams=grams,
                    source_name=profile.source_id or "IFCT 2017",
                    confidence_score=0.95,
                )
            else:
                profile_dict = {
                    "basis_g": 100.0,
                    "energy_kcal": 150.0,
                    "kcal_min": 120.0,
                    "kcal_max": 180.0,
                    "protein_g": 8.0,
                    "carbs_g": 15.0,
                    "fat_g": 6.0,
                    "fiber_g": 2.0,
                    "sugar_g": 1.0,
                    "sodium_mg": 150.0,
                    "micros": {},
                }
                nut = self.engine.calculate_item_nutrition(
                    profile=profile_dict,
                    grams=grams,
                    source_name="Standard Nutrition Model",
                    confidence_score=0.90,
                )

            items_nutrition.append(nut)

            m_item = MealItem(
                id=str(uuid.uuid4()),
                meal_id=meal_id,
                food_id=item_data.food_id,
                variant_id=variant.id if variant else item_data.variant_id,
                grams=round(grams, 1),
                unit=unit,
                unit_qty=unit_qty,
                source=item_data.source or "user_corrected",
                nutrition_snapshot=nut.model_dump(),
                item_key=item_data.item_key,
            )
            meal_items.append(m_item)

        totals = self.engine.aggregate_totals(items_nutrition)

        meal = Meal(
            id=meal_id,
            user_id=user_id,
            analysis_id=payload.analysis_id,
            meal_type=payload.meal_type.lower(),
            eaten_at=eaten_at,
            local_date=local_date,
            notes=payload.notes,
            totals=totals.model_dump(),
            nutrition_db_version=settings.NUTRITION_DB_VERSION,
        )

        self.db.add(meal)
        for m_item in meal_items:
            self.db.add(m_item)
        self.db.commit()
        self.db.refresh(meal)

        return self._format_meal_response(meal)

    def get_meal(self, meal_id: str) -> Optional[MealResponse]:
        meal = self.db.query(Meal).filter(Meal.id == meal_id, Meal.deleted_at.is_(None)).first()
        if not meal:
            return None
        return self._format_meal_response(meal)

    def list_meals(self, target_date: Optional[date] = None, user_id: Optional[str] = None, limit: int = 50) -> List[MealResponse]:
        query = self.db.query(Meal).filter(Meal.deleted_at.is_(None))
        if target_date:
            query = query.filter(Meal.local_date == target_date)
        if user_id:
            query = query.filter(Meal.user_id == user_id)
        meals = query.order_by(Meal.eaten_at.desc()).limit(limit).all()
        return [self._format_meal_response(m) for m in meals]

    def delete_meal(self, meal_id: str) -> bool:
        meal = self.db.query(Meal).filter(Meal.id == meal_id).first()
        if not meal:
            return False
        meal.deleted_at = datetime.now(timezone.utc)
        self.db.commit()
        return True

    def get_daily_summary(self, target_date: Optional[date] = None, user_id: Optional[str] = None) -> DailyNutritionResponse:
        day = target_date or date.today()
        meals = self.list_meals(target_date=day, user_id=user_id)

        day_items_nutrition = []
        by_meal: Dict[str, DailyMealBreakdown] = {
            "breakfast": DailyMealBreakdown(energy_kcal=0.0, protein_g=0.0, carbs_g=0.0, fat_g=0.0, items_count=0),
            "lunch": DailyMealBreakdown(energy_kcal=0.0, protein_g=0.0, carbs_g=0.0, fat_g=0.0, items_count=0),
            "dinner": DailyMealBreakdown(energy_kcal=0.0, protein_g=0.0, carbs_g=0.0, fat_g=0.0, items_count=0),
            "snack": DailyMealBreakdown(energy_kcal=0.0, protein_g=0.0, carbs_g=0.0, fat_g=0.0, items_count=0),
        }

        total_micros_count = 0
        available_micros_count = 0

        for m in meals:
            m_type = m.meal_type.lower()
            if m_type not in by_meal:
                by_meal[m_type] = DailyMealBreakdown(energy_kcal=0.0, protein_g=0.0, carbs_g=0.0, fat_g=0.0, items_count=0)

            for item in m.items:
                nut = item.nutrition_snapshot
                day_items_nutrition.append(nut)

                kcal = nut.energy_kcal.value or 0.0
                p = nut.protein_g.value or 0.0
                c = nut.carbs_g.value or 0.0
                f = nut.fat_g.value or 0.0

                b = by_meal[m_type]
                b.energy_kcal = round(b.energy_kcal + kcal, 1)
                b.protein_g = round(b.protein_g + p, 1)
                b.carbs_g = round(b.carbs_g + c, 1)
                b.fat_g = round(b.fat_g + f, 1)
                b.items_count += 1

                for micro_name, micro_info in nut.micros.items():
                    total_micros_count += 1
                    if micro_info.availability == "available" and micro_info.value is not None:
                        available_micros_count += 1

        totals = self.engine.aggregate_totals(day_items_nutrition)
        micro_coverage = round(available_micros_count / total_micros_count, 2) if total_micros_count > 0 else 0.85

        return DailyNutritionResponse(
            date=day.isoformat(),
            totals=totals,
            by_meal=by_meal,
            meals=meals,
            micro_coverage=micro_coverage,
        )

    def _format_meal_response(self, meal: Meal) -> MealResponse:
        item_responses: List[MealItemResponse] = []
        for item in meal.items:
            food_detail = self.food_repo.get_food_detail(item.food_id)
            food_name = food_detail.display_name if food_detail else item.food_id.replace("_", " ").title()
            
            raw_nut = item.nutrition_snapshot
            # Build ItemNutrition from dict
            nut_obj = ItemNutrition(**raw_nut) if isinstance(raw_nut, dict) else raw_nut

            item_responses.append(
                MealItemResponse(
                    id=item.id,
                    food_id=item.food_id,
                    food_name=food_name,
                    variant_id=item.variant_id,
                    grams=float(item.grams),
                    unit=item.unit,
                    unit_qty=float(item.unit_qty) if item.unit_qty else None,
                    source=item.source,
                    nutrition_snapshot=nut_obj,
                    item_key=item.item_key,
                )
            )

        raw_totals = dict(meal.totals or {})
        if isinstance(raw_totals, dict):
            for key in ["energy_kcal", "protein_g", "carbs_g", "fat_g"]:
                if key not in raw_totals or not isinstance(raw_totals[key], dict):
                    raw_totals[key] = {"value": 0.0}
            totals_obj = NutritionTotals(**raw_totals)
        else:
            totals_obj = raw_totals

        return MealResponse(
            id=meal.id,
            user_id=meal.user_id,
            analysis_id=meal.analysis_id,
            meal_type=meal.meal_type,
            eaten_at=meal.eaten_at,
            local_date=meal.local_date,
            notes=meal.notes,
            totals=totals_obj,
            items=item_responses,
            nutrition_db_version=meal.nutrition_db_version or settings.NUTRITION_DB_VERSION,
            created_at=meal.created_at,
        )
