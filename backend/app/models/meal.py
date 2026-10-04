import uuid
from datetime import datetime, timezone, date
from sqlalchemy import Column, String, Numeric, DateTime, Date, ForeignKey, JSON
from sqlalchemy.orm import relationship
from backend.app.core.database import Base

def generate_uuid():
    return str(uuid.uuid4())

class Meal(Base):
    __tablename__ = "meal"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("app_user.id"), nullable=True)
    analysis_id = Column(String(36), ForeignKey("analysis.id"), nullable=True)
    meal_type = Column(String(50), nullable=False)  # 'breakfast', 'lunch', 'dinner', 'snack'
    eaten_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    local_date = Column(Date, nullable=False, default=date.today, index=True)
    notes = Column(String(255), nullable=True)
    totals = Column(JSON, nullable=False, default=dict)
    nutrition_db_version = Column(String(50), default="nut-2026.01")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("AppUser", back_populates="meals")
    items = relationship("MealItem", back_populates="meal", cascade="all, delete-orphan")

class MealItem(Base):
    __tablename__ = "meal_item"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    meal_id = Column(String(36), ForeignKey("meal.id"), nullable=False)
    food_id = Column(String(100), ForeignKey("food.id"), nullable=False)
    variant_id = Column(String(120), nullable=True)
    grams = Column(Numeric(8, 2), nullable=False)
    unit = Column(String(50), nullable=True)
    unit_qty = Column(Numeric(8, 2), nullable=True)
    source = Column(String(50), default="ai")  # 'ai', 'user_corrected', 'manual'
    nutrition_snapshot = Column(JSON, nullable=False, default=dict)
    item_key = Column(String(50), nullable=True)

    meal = relationship("Meal", back_populates="items")
    food = relationship("Food")
