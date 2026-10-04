from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from backend.app.core.database import get_db
from backend.app.core.errors import error_response
from backend.app.modules.nutrition.repository import FoodRepository
from backend.app.modules.nutrition.engine import NutritionEngine
from backend.app.schemas.food import (
    FoodSearchItemSchema,
    FoodDetailSchema,
    VariantSummarySchema,
    NutritionCalculateRequest,
    NutritionCalculateResponse,
    CalculatedItemResult,
)

router = APIRouter(tags=["nutrition"])

@router.get("/food/search", response_model=List[FoodSearchItemSchema])
def search_food(
    q: str = Query(..., min_length=1, description="Food name or alias query"),
    limit: int = Query(20, le=50),
    db: Session = Depends(get_db),
):
    repo = FoodRepository(db)
    return repo.search_foods(query=q, limit=limit)

@router.get("/food/{food_id}", response_model=FoodDetailSchema)
def get_food(food_id: str, db: Session = Depends(get_db)):
    repo = FoodRepository(db)
    detail = repo.get_food_detail(food_id)
    if not detail:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Food '{food_id}' not found",
        )
    return detail

@router.get("/food/{food_id}/variants", response_model=List[VariantSummarySchema])
def get_food_variants(food_id: str, db: Session = Depends(get_db)):
    repo = FoodRepository(db)
    detail = repo.get_food_detail(food_id)
    if not detail:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Food '{food_id}' not found",
        )
    return detail.variants

@router.post("/nutrition/calculate", response_model=NutritionCalculateResponse)
def calculate_nutrition(
    payload: NutritionCalculateRequest,
    db: Session = Depends(get_db),
):
    repo = FoodRepository(db)
    engine = NutritionEngine()

    calculated_items: List[CalculatedItemResult] = []
    items_nutrition = []

    for item in payload.items:
        detail = repo.get_food_detail(item.food_id)
        if not detail:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Food '{item.food_id}' not found in nutrition database",
            )

        variant, profile = repo.get_variant_profile(item.food_id, item.variant_id)
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No nutrition profile found for food '{item.food_id}'",
            )

        grams = repo.convert_to_grams(item.food_id, item.quantity, item.unit)

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

        item_nut = engine.calculate_item_nutrition(
            profile=profile_dict,
            grams=grams,
            source_name="IFCT 2017" if profile.source_id == "IFCT2017" else "Recipe-calculated",
            confidence_score=0.95,
        )

        items_nutrition.append(item_nut)
        calculated_items.append(
            CalculatedItemResult(
                food_id=item.food_id,
                variant_id=variant.id if variant else f"{item.food_id}:default",
                name=detail.display_name,
                quantity=item.quantity,
                unit=item.unit,
                grams=round(grams, 1),
                nutrition=item_nut,
            )
        )

    totals = engine.aggregate_totals(items_nutrition)

    return NutritionCalculateResponse(
        items=calculated_items,
        totals=totals,
        disclaimer="Nutrition values are estimates based on standard recipes and IFCT 2017.",
    )
