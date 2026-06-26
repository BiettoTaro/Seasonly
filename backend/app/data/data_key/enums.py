from enum import StrEnum
from typing import TYPE_CHECKING, ClassVar

from app.data.data_key.user import UserDataKey


class DataKey(StrEnum):
    EU_SEASONAL_PRODUCE = "eu_seasonal_produce"
    THEMEALDB_RECIPES = "themealdb_recipes"
    RECOMMENDATION_EVENTS = "recommendation_events"

    if TYPE_CHECKING:
        User: ClassVar[type[UserDataKey]]


DataKey.User = UserDataKey  # type: ignore[attr-defined]
