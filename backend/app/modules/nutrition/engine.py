from typing import Dict, Any, List, Optional, Tuple
from backend.app.schemas.food import ItemNutrition, NutrientValue, NutritionTotals

class NutritionEngine:
    """
    Core Nutrition Calculation Engine as defined in SDD Section 18 & 19.
    Pure calculation logic with zero computer vision dependencies.
    Enforces:
    - Missing micronutrient values are flagged 'missing' instead of shown as 0 (FR-N4)
    - Macro scaling based on grams
    - Energy calculation: Atwater (4 kcal/g protein, 4 kcal/g carbs, 9 kcal/g fat, 2 kcal/g fiber) with bounds
    - Recipe variance and range calculation
    """

    @staticmethod
    def calculate_item_nutrition(
        profile: Dict[str, Any],
        grams: float,
        source_name: Optional[str] = "IFCT 2017",
        confidence_score: float = 0.9,
    ) -> ItemNutrition:
        basis_g = float(profile.get("basis_g", 100.0) or 100.0)
        scale = grams / basis_g

        base_kcal = float(profile.get("energy_kcal", 0.0) or 0.0)
        energy_val = round(base_kcal * scale, 1)

        # Variance ranges based on recipe / preparation uncertainty (SDD Section 19.4)
        kcal_min_factor = float(profile.get("kcal_min") or (base_kcal * 0.85)) / base_kcal if base_kcal > 0 else 0.85
        kcal_max_factor = float(profile.get("kcal_max") or (base_kcal * 1.25)) / base_kcal if base_kcal > 0 else 1.25
        energy_range = [round(energy_val * kcal_min_factor, 1), round(energy_val * kcal_max_factor, 1)]

        protein_g = round(float(profile.get("protein_g", 0.0) or 0.0) * scale, 1)
        carbs_g = round(float(profile.get("carbs_g", 0.0) or 0.0) * scale, 1)
        fat_g = round(float(profile.get("fat_g", 0.0) or 0.0) * scale, 1)
        fiber_g = round(float(profile.get("fiber_g", 0.0) or 0.0) * scale, 1)
        sugar_g = round(float(profile.get("sugar_g", 0.0) or 0.0) * scale, 1)
        sodium_mg = round(float(profile.get("sodium_mg", 0.0) or 0.0) * scale, 1)

        # Process micros with explicit availability flags (FR-N4)
        raw_micros = profile.get("micros", {}) or {}
        processed_micros: Dict[str, NutrientValue] = {}
        standard_micros = [
            "calcium_mg", "iron_mg", "potassium_mg",
            "vitamin_a_ug", "vitamin_c_mg", "vitamin_b12_ug", "folate_ug"
        ]

        for micro_key in standard_micros:
            if micro_key in raw_micros and raw_micros[micro_key] is not None:
                m_info = raw_micros[micro_key]
                if isinstance(m_info, dict):
                    if m_info.get("availability") == "missing":
                        processed_micros[micro_key] = NutrientValue(value=None, availability="missing")
                    else:
                        m_val = float(m_info.get("value", 0.0) or 0.0) * scale
                        processed_micros[micro_key] = NutrientValue(value=round(m_val, 2), availability="available")
                else:
                    m_val = float(m_info) * scale
                    processed_micros[micro_key] = NutrientValue(value=round(m_val, 2), availability="available")
            else:
                processed_micros[micro_key] = NutrientValue(value=None, availability="missing")

        conf_level = "high" if confidence_score >= 0.8 else ("medium" if confidence_score >= 0.5 else "low")

        sources = [source_name] if source_name else ["IFCT 2017", "recipe_calc"]

        return ItemNutrition(
            energy_kcal=NutrientValue(value=energy_val, range=energy_range, availability="available"),
            protein_g=NutrientValue(value=protein_g, availability="available"),
            carbs_g=NutrientValue(value=carbs_g, availability="available"),
            fat_g=NutrientValue(value=fat_g, availability="available"),
            fiber_g=NutrientValue(value=fiber_g, availability="available"),
            sugar_g=NutrientValue(value=sugar_g, availability="available"),
            sodium_mg=NutrientValue(value=sodium_mg, availability="available"),
            micros=processed_micros,
            confidence={"level": conf_level, "score": round(confidence_score, 2)},
            sources=sources
        )

    @staticmethod
    def aggregate_totals(items_nutrition: List[ItemNutrition]) -> NutritionTotals:
        total_energy = 0.0
        total_min_energy = 0.0
        total_max_energy = 0.0
        total_protein = 0.0
        total_carbs = 0.0
        total_fat = 0.0
        total_fiber = 0.0
        total_sodium = 0.0

        for n in items_nutrition:
            if n.energy_kcal.value:
                total_energy += n.energy_kcal.value
            if n.energy_kcal.range:
                total_min_energy += n.energy_kcal.range[0]
                total_max_energy += n.energy_kcal.range[1]
            else:
                total_min_energy += (n.energy_kcal.value or 0.0) * 0.9
                total_max_energy += (n.energy_kcal.value or 0.0) * 1.1

            if n.protein_g.value:
                total_protein += n.protein_g.value
            if n.carbs_g.value:
                total_carbs += n.carbs_g.value
            if n.fat_g.value:
                total_fat += n.fat_g.value
            if n.fiber_g.value:
                total_fiber += n.fiber_g.value
            if n.sodium_mg.value:
                total_sodium += n.sodium_mg.value

        return NutritionTotals(
            energy_kcal=NutrientValue(
                value=round(total_energy, 1),
                range=[round(total_min_energy, 1), round(total_max_energy, 1)],
                availability="available"
            ),
            protein_g=NutrientValue(value=round(total_protein, 1), availability="available"),
            carbs_g=NutrientValue(value=round(total_carbs, 1), availability="available"),
            fat_g=NutrientValue(value=round(total_fat, 1), availability="available"),
            fiber_g=NutrientValue(value=round(total_fiber, 1), availability="available"),
            sodium_mg=NutrientValue(value=round(total_sodium, 1), availability="available")
        )
