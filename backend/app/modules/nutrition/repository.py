from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from backend.app.models.nutrition import (
    Food,
    FoodCategory,
    FoodAlias,
    FoodVariant,
    ServingUnit,
    NutritionProfile,
)
from backend.app.schemas.food import (
    FoodSearchItemSchema,
    FoodDetailSchema,
    ServingUnitSchema,
    VariantSummarySchema,
)

class FoodRepository:
    def __init__(self, db: Session):
        self.db = db

    def search_foods(self, query: str, limit: int = 20) -> List[FoodSearchItemSchema]:
        q = query.strip().lower()
        if not q:
            return []

        # Find matching foods directly or via aliases
        alias_matches = (
            self.db.query(FoodAlias)
            .filter(func.lower(FoodAlias.alias).contains(q))
            .limit(limit * 2)
            .all()
        )
        food_ids_from_aliases = {a.food_id: a.alias for a in alias_matches}

        foods = (
            self.db.query(Food)
            .filter(
                or_(
                    func.lower(Food.id).contains(q),
                    func.lower(Food.display_name).contains(q),
                    Food.id.in_(list(food_ids_from_aliases.keys())),
                )
            )
            .limit(limit)
            .all()
        )

        results = []
        for food in foods:
            # Get default variant profile for nutrition summary
            default_variant = (
                self.db.query(FoodVariant)
                .filter(FoodVariant.food_id == food.id, FoodVariant.is_default == True)
                .first()
            ) or (
                self.db.query(FoodVariant)
                .filter(FoodVariant.food_id == food.id)
                .first()
            )

            profile = None
            if default_variant:
                profile = (
                    self.db.query(NutritionProfile)
                    .filter(
                        NutritionProfile.food_variant_id == default_variant.id,
                        NutritionProfile.is_current == True,
                    )
                    .first()
                )

            matched_alias = food_ids_from_aliases.get(food.id)
            results.append(
                FoodSearchItemSchema(
                    food_id=food.id,
                    display_name=food.display_name,
                    category=food.category.name if food.category else "General",
                    is_countable=bool(food.is_countable),
                    default_unit=food.default_unit or "g",
                    default_grams=float(food.default_grams or 100.0),
                    energy_kcal_per_100g=float(profile.energy_kcal if profile else 0.0),
                    protein_g_per_100g=float(profile.protein_g if profile else 0.0),
                    carbs_g_per_100g=float(profile.carbs_g if profile else 0.0),
                    fat_g_per_100g=float(profile.fat_g if profile else 0.0),
                    matched_alias=matched_alias,
                )
            )
        return results

    def get_food_detail(self, food_id: str) -> Optional[FoodDetailSchema]:
        food = self.db.query(Food).filter(Food.id == food_id).first()
        if not food:
            return None

        aliases = [a.alias for a in food.aliases]
        serving_units = [
            ServingUnitSchema(
                unit=u.unit,
                grams=float(u.grams),
                label=u.label,
                confidence=u.confidence or "high",
            )
            for u in food.serving_units
        ]

        variants = []
        for v in food.variants:
            profile = (
                self.db.query(NutritionProfile)
                .filter(NutritionProfile.food_variant_id == v.id, NutritionProfile.is_current == True)
                .first()
            )
            if profile:
                variants.append(
                    VariantSummarySchema(
                        variant_id=v.id,
                        label=v.label,
                        preparation=v.preparation,
                        is_default=bool(v.is_default),
                        energy_kcal=float(profile.energy_kcal),
                        kcal_min=float(profile.kcal_min) if profile.kcal_min else None,
                        kcal_max=float(profile.kcal_max) if profile.kcal_max else None,
                        protein_g=float(profile.protein_g),
                        carbs_g=float(profile.carbs_g),
                        fat_g=float(profile.fat_g),
                    )
                )

        return FoodDetailSchema(
            food_id=food.id,
            display_name=food.display_name,
            category=food.category.name if food.category else "General",
            is_countable=bool(food.is_countable),
            default_unit=food.default_unit or "g",
            default_grams=float(food.default_grams or 100.0),
            density_g_per_ml=float(food.density_g_per_ml) if food.density_g_per_ml else None,
            aliases=aliases,
            serving_units=serving_units,
            variants=variants,
        )

    def convert_to_grams(self, food_id: str, quantity: float, unit: str) -> float:
        if unit.lower() in ["g", "grams", "gram"]:
            return quantity
        if unit.lower() in ["ml", "milliliters"]:
            food = self.db.query(Food).filter(Food.id == food_id).first()
            density = float(food.density_g_per_ml or 1.0) if food else 1.0
            return quantity * density

        # Check serving units
        serving_unit = (
            self.db.query(ServingUnit)
            .filter(ServingUnit.food_id == food_id, func.lower(ServingUnit.unit) == unit.lower())
            .first()
        )
        if serving_unit:
            return quantity * float(serving_unit.grams)

        # Check generic serving units (food_id is NULL)
        generic_unit = (
            self.db.query(ServingUnit)
            .filter(ServingUnit.food_id.is_(None), func.lower(ServingUnit.unit) == unit.lower())
            .first()
        )
        if generic_unit:
            return quantity * float(generic_unit.grams)

        # Fallback to standard estimations
        standard_map = {
            "roti": 35.0,
            "phulka": 30.0,
            "chapati": 40.0,
            "paratha": 80.0,
            "puri": 30.0,
            "katori": 150.0,
            "bowl": 200.0,
            "cup": 200.0,
            "tablespoon": 15.0,
            "teaspoon": 5.0,
            "glass": 250.0,
            "piece": 50.0,
        }
        return quantity * standard_map.get(unit.lower(), 100.0)

    def get_variant_profile(self, food_id: str, variant_id: Optional[str] = None) -> Tuple[Optional[FoodVariant], Optional[NutritionProfile]]:
        variant = None
        if variant_id:
            variant = self.db.query(FoodVariant).filter(FoodVariant.id == variant_id).first()
        if not variant:
            variant = (
                self.db.query(FoodVariant)
                .filter(FoodVariant.food_id == food_id, FoodVariant.is_default == True)
                .first()
            ) or (
                self.db.query(FoodVariant)
                .filter(FoodVariant.food_id == food_id)
                .first()
            )

        if not variant:
            return None, None

        profile = (
            self.db.query(NutritionProfile)
            .filter(NutritionProfile.food_variant_id == variant.id, NutritionProfile.is_current == True)
            .first()
        )
        return variant, profile
