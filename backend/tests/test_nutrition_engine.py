import pytest
from backend.app.modules.nutrition.engine import NutritionEngine

def test_nutrition_engine_scaling():
    engine = NutritionEngine()
    profile = {
        "basis_g": 100.0,
        "energy_kcal": 200.0,
        "kcal_min": 170.0,
        "kcal_max": 240.0,
        "protein_g": 10.0,
        "carbs_g": 20.0,
        "fat_g": 5.0,
        "fiber_g": 3.0,
        "sugar_g": 2.0,
        "sodium_mg": 300.0,
        "micros": {
            "calcium_mg": {"value": 50.0},
            "iron_mg": {"value": 2.0},
            "vitamin_b12_ug": {"availability": "missing"},
        },
    }

    # Test scaling to 150g
    item_nut = engine.calculate_item_nutrition(profile, grams=150.0)
    assert item_nut.energy_kcal.value == 300.0
    assert item_nut.protein_g.value == 15.0
    assert item_nut.carbs_g.value == 30.0
    assert item_nut.fat_g.value == 7.5
    assert item_nut.fiber_g.value == 4.5
    assert item_nut.sodium_mg.value == 450.0

    # Test micronutrient availability flag (FR-N4: missing is NOT 0)
    assert item_nut.micros["calcium_mg"].value == 75.0
    assert item_nut.micros["calcium_mg"].availability == "available"
    assert item_nut.micros["vitamin_b12_ug"].value is None
    assert item_nut.micros["vitamin_b12_ug"].availability == "missing"

def test_nutrition_engine_totals_aggregation():
    engine = NutritionEngine()
    p1 = {"basis_g": 100.0, "energy_kcal": 100.0, "protein_g": 3.0, "carbs_g": 20.0, "fat_g": 1.0}
    p2 = {"basis_g": 100.0, "energy_kcal": 150.0, "protein_g": 7.0, "carbs_g": 15.0, "fat_g": 5.0}

    n1 = engine.calculate_item_nutrition(p1, grams=100.0)
    n2 = engine.calculate_item_nutrition(p2, grams=100.0)

    totals = engine.aggregate_totals([n1, n2])
    assert totals.energy_kcal.value == 250.0
    assert totals.protein_g.value == 10.0
    assert totals.carbs_g.value == 35.0
    assert totals.fat_g.value == 6.0
