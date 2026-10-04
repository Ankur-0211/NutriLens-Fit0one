from backend.app.core.database import Base
from backend.app.models.user import AppUser
from backend.app.models.nutrition import (
    NutritionSource,
    FoodCategory,
    Food,
    FoodAlias,
    FoodVariant,
    ServingUnit,
    NutritionProfile,
    Ingredient,
    Recipe,
    RecipeIngredient,
)
from backend.app.models.identity import (
    LabelsetVersion,
    VisualClass,
    IdentityMapVersion,
    VisualClassMapping,
)
from backend.app.models.image import ImageRecord
from backend.app.models.analysis import AnalysisRecord, PredictionItem
from backend.app.models.correction import CorrectionEvent
from backend.app.models.meal import Meal, MealItem
from backend.app.models.audit import AuditLog
from backend.app.models.improvement import (
    ModelVersion,
    DatasetVersion,
    DatasetSample,
    FeedbackReview,
)

__all__ = [
    "Base",
    "AppUser",
    "NutritionSource",
    "FoodCategory",
    "Food",
    "FoodAlias",
    "FoodVariant",
    "ServingUnit",
    "NutritionProfile",
    "Ingredient",
    "Recipe",
    "RecipeIngredient",
    "LabelsetVersion",
    "VisualClass",
    "IdentityMapVersion",
    "VisualClassMapping",
    "ImageRecord",
    "AnalysisRecord",
    "PredictionItem",
    "CorrectionEvent",
    "Meal",
    "MealItem",
    "AuditLog",
    "ModelVersion",
    "DatasetVersion",
    "DatasetSample",
    "FeedbackReview",
]
