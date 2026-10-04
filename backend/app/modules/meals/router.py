from fastapi import APIRouter, Depends, Query, Path, status, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date
from backend.app.core.database import get_db
from backend.app.modules.meals.service import MealService
from backend.app.schemas.meal import (
    MealCreateRequest,
    MealResponse,
    DailyNutritionResponse,
)

router = APIRouter(tags=["meals"])

@router.post("/meals", response_model=MealResponse, status_code=status.HTTP_201_CREATED)
def create_meal(payload: MealCreateRequest, db: Session = Depends(get_db)):
    service = MealService(db)
    return service.create_meal(payload)

@router.get("/meals", response_model=List[MealResponse])
def list_meals(
    date_param: Optional[str] = Query(None, alias="date", description="YYYY-MM-DD format"),
    limit: int = Query(50, le=100),
    db: Session = Depends(get_db),
):
    service = MealService(db)
    target_date = date.fromisoformat(date_param) if date_param else None
    return service.list_meals(target_date=target_date, limit=limit)

@router.get("/meals/{id}", response_model=MealResponse)
def get_meal(id: str = Path(...), db: Session = Depends(get_db)):
    service = MealService(db)
    meal = service.get_meal(id)
    if not meal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Meal with ID '{id}' not found",
        )
    return meal

@router.delete("/meals/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_meal(id: str = Path(...), db: Session = Depends(get_db)):
    service = MealService(db)
    success = service.delete_meal(id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Meal with ID '{id}' not found",
        )
    return None

@router.get("/nutrition/daily", response_model=DailyNutritionResponse)
def get_daily_nutrition(
    date_param: Optional[str] = Query(None, alias="date", description="YYYY-MM-DD format (defaults to today)"),
    tz: Optional[str] = Query("Asia/Kolkata"),
    db: Session = Depends(get_db),
):
    service = MealService(db)
    target_date = date.fromisoformat(date_param) if date_param else date.today()
    return service.get_daily_summary(target_date=target_date)
