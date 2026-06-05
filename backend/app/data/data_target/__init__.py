from app.data.data_target.produce import EU_SEASONAL_PRODUCE_TARGETS
from app.data.data_target.recipes import EU_RECIPE_TARGETS
from app.data.data_target.recommendations import RECOMMENDATION_EVENT_TARGETS
from app.data.data_target.user import USER_PROFILE_TARGET
from app.data.enums import DataTargetType

__all__ = [
    "DataTargetType",
    "EU_RECIPE_TARGETS",
    "EU_SEASONAL_PRODUCE_TARGETS",
    "RECOMMENDATION_EVENT_TARGETS",
    "USER_PROFILE_TARGET",
]
