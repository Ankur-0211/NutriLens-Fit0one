import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Boolean, Numeric, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from backend.app.core.database import Base

def generate_uuid():
    return str(uuid.uuid4())

class NutritionSource(Base):
    __tablename__ = "nutrition_source"

    id = Column(String(50), primary_key=True)  # 'IFCT2017', 'USDA_FDC', 'RECIPE_CALC', 'NUTRITIONIST'
    name = Column(String(100), nullable=False)
    url = Column(String(255), nullable=True)
    license = Column(String(100), nullable=True)
    version = Column(String(50), nullable=True)
    notes = Column(String(255), nullable=True)

class FoodCategory(Base):
    __tablename__ = "food_category"

    id = Column(Integer, primary_key=True, autoincrement=True)
    parent_id = Column(Integer, ForeignKey("food_category.id"), nullable=True)
    slug = Column(String(50), unique=True, nullable=False)
    name = Column(String(100), nullable=False)

    children = relationship("FoodCategory")
    foods = relationship("Food", back_populates="category")

class Food(Base):
    __tablename__ = "food"

    id = Column(String(100), primary_key=True)  # canonical slug e.g. 'paneer_butter_masala'
    display_name = Column(String(150), nullable=False)
    category_id = Column(Integer, ForeignKey("food_category.id"), nullable=True)
    is_countable = Column(Boolean, default=False)
    default_unit = Column(String(50), default="g")
    default_grams = Column(Numeric(7, 2), default=100.0)
    density_g_per_ml = Column(Numeric(5, 3), nullable=True)
    status = Column(String(20), default="active")
    merged_into = Column(String(100), ForeignKey("food.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    category = relationship("FoodCategory", back_populates="foods")
    aliases = relationship("FoodAlias", back_populates="food", cascade="all, delete-orphan")
    variants = relationship("FoodVariant", back_populates="food", cascade="all, delete-orphan")
    serving_units = relationship("ServingUnit", back_populates="food", cascade="all, delete-orphan")

class FoodAlias(Base):
    __tablename__ = "food_alias"

    id = Column(Integer, primary_key=True, autoincrement=True)
    food_id = Column(String(100), ForeignKey("food.id"), nullable=False)
    alias = Column(String(150), nullable=False, index=True)
    lang = Column(String(10), default="en")
    script = Column(String(20), nullable=True)

    food = relationship("Food", back_populates="aliases")

class FoodVariant(Base):
    __tablename__ = "food_variant"

    id = Column(String(120), primary_key=True)  # e.g. 'paneer_butter_masala:default', 'paneer_butter_masala:home_light'
    food_id = Column(String(100), ForeignKey("food.id"), nullable=False)
    label = Column(String(100), nullable=False)  # 'Default', 'Home Style (Light)', 'Restaurant Style'
    preparation = Column(String(100), nullable=True)  # 'curry', 'dry', 'raw', 'deep_fried'
    recipe_id = Column(Integer, nullable=True)
    is_default = Column(Boolean, default=False)

    food = relationship("Food", back_populates="variants")
    nutrition_profiles = relationship("NutritionProfile", back_populates="variant", cascade="all, delete-orphan")

class ServingUnit(Base):
    __tablename__ = "serving_unit"

    id = Column(Integer, primary_key=True, autoincrement=True)
    food_id = Column(String(100), ForeignKey("food.id"), nullable=True)  # NULL = generic
    unit = Column(String(50), nullable=False)  # 'katori', 'roti', 'piece', 'cup', 'tablespoon', 'g', 'ml'
    grams = Column(Numeric(8, 2), nullable=False)
    label = Column(String(100), nullable=True)  # '1 Standard Katori (150g)'
    source_id = Column(String(50), ForeignKey("nutrition_source.id"), nullable=True)
    confidence = Column(String(20), default="high")

    food = relationship("Food", back_populates="serving_units")

class NutritionProfile(Base):
    __tablename__ = "nutrition_profile"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    food_variant_id = Column(String(120), ForeignKey("food_variant.id"), nullable=True)
    ingredient_id = Column(Integer, nullable=True)
    basis_g = Column(Numeric(6, 1), default=100.0, nullable=False)
    energy_kcal = Column(Numeric(7, 2), nullable=False)
    protein_g = Column(Numeric(6, 2), default=0.0)
    carbs_g = Column(Numeric(6, 2), default=0.0)
    fat_g = Column(Numeric(6, 2), default=0.0)
    fiber_g = Column(Numeric(6, 2), default=0.0)
    sugar_g = Column(Numeric(6, 2), default=0.0)
    sodium_mg = Column(Numeric(8, 2), default=0.0)
    micros = Column(JSON, default=dict)  # {"calcium_mg": {"value": 210}, "iron_mg": {"value": 1.4}, ...}
    kcal_min = Column(Numeric(7, 2), nullable=True)
    kcal_max = Column(Numeric(7, 2), nullable=True)
    source_id = Column(String(50), ForeignKey("nutrition_source.id"), nullable=True)
    source_ref = Column(String(100), nullable=True)
    method = Column(String(50), default="analytical")  # 'analytical', 'recipe_calc', 'estimated'
    version = Column(String(50), default="nut-2026.01")
    reviewed_by = Column(String(100), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    is_current = Column(Boolean, default=True)

    variant = relationship("FoodVariant", back_populates="nutrition_profiles")

class Ingredient(Base):
    __tablename__ = "ingredient"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False)
    category = Column(String(50), nullable=True)

class Recipe(Base):
    __tablename__ = "recipe"

    id = Column(Integer, primary_key=True, autoincrement=True)
    food_id = Column(String(100), ForeignKey("food.id"), nullable=False)
    yield_g = Column(Numeric(8, 1), nullable=True)
    notes = Column(String(255), nullable=True)
    source_id = Column(String(50), nullable=True)

class RecipeIngredient(Base):
    __tablename__ = "recipe_ingredient"

    recipe_id = Column(Integer, ForeignKey("recipe.id"), primary_key=True)
    ingredient_id = Column(Integer, ForeignKey("ingredient.id"), primary_key=True)
    grams = Column(Numeric(8, 2), nullable=False)
    retention_factor = Column(JSON, default=dict)
