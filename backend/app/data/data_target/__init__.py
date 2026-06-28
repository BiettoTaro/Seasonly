from app.data.data_target.produce import EU_SEASONAL_PRODUCE_TARGETS
from app.data.data_target.recipes import THEMEALDB_RECIPE_TARGETS
from app.data.data_target.recommendations import RECOMMENDATION_EVENT_TARGETS
from app.data.data_target.user import USER_ONBOARDING_PROFILE_TARGET, USER_PROFILE_TARGET
from app.data.enums import DataTargetType

__all__ = [
    "DataTargetType",
    "EU_SEASONAL_PRODUCE_TARGETS",
    "RECOMMENDATION_EVENT_TARGETS",
    "THEMEALDB_RECIPE_TARGETS",
    "USER_ONBOARDING_PROFILE_TARGET",
    "USER_PROFILE_TARGET",
]
