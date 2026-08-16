"""SQLAlchemy model package."""

from app.db.base import Base
from app.models.data_import import DataImportRun
from app.models.produce import Produce, ProduceSeason
from app.models.recipe import (
    Ingredient,
    Recipe,
    RecipeAllergenAssessment,
    RecipeCategory,
    RecipeIngredient,
    RecipeTag,
    Tag,
)
from app.models.recommendation import RecommendationEvent
from app.models.user import (
    User,
    UserAllergen,
    UserConsent,
    UserCuisinePreference,
    UserDietaryRule,
    UserPasswordResetToken,
    UserProfile,
    UserProteinPreference,
    UserRefreshToken,
)
from app.models.user_recipe import UserPlannedMeal, UserRecipeFavourite, UserRecipeHistory

__all__ = [
    "Base",
    "DataImportRun",
    "Ingredient",
    "Produce",
    "ProduceSeason",
    "Recipe",
    "RecommendationEvent",
    "RecipeAllergenAssessment",
    "RecipeCategory",
    "RecipeIngredient",
    "RecipeTag",
    "Tag",
    "User",
    "UserAllergen",
    "UserConsent",
    "UserCuisinePreference",
    "UserDietaryRule",
    "UserPasswordResetToken",
    "UserProfile",
    "UserProteinPreference",
    "UserRefreshToken",
    "UserPlannedMeal",
    "UserRecipeFavourite",
    "UserRecipeHistory",
]
