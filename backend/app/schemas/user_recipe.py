import uuid
from datetime import datetime
from enum import IntEnum, StrEnum
from typing import ClassVar

from pydantic import BaseModel, ConfigDict


class Weekday(IntEnum):
    MONDAY = 1
    TUESDAY = 2
    WEDNESDAY = 3
    THURSDAY = 4
    FRIDAY = 5
    SATURDAY = 6
    SUNDAY = 7


class MealSlot(StrEnum):
    BREAKFAST = "breakfast"
    LUNCH = "lunch"
    DINNER = "dinner"
    SNACK = "snack"


class RecipeSummaryResponse(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    category: str | None
    area: str | None
    country_of_origin: str | None
    thumbnail_url: str | None


class FavouriteRecipeResponse(BaseModel):
    recipe: RecipeSummaryResponse
    created_at: datetime


class RecipeHistoryResponse(BaseModel):
    recipe: RecipeSummaryResponse
    viewed_at: datetime


class PlannedMealCreate(BaseModel):
    recipe_id: uuid.UUID
    day_of_week: Weekday
    meal_slot: MealSlot


class PlannedMealResponse(BaseModel):
    id: uuid.UUID
    recipe: RecipeSummaryResponse
    day_of_week: Weekday
    meal_slot: MealSlot
    created_at: datetime
