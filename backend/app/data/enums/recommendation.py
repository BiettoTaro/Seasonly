from enum import StrEnum


class RecommendationEventSource(StrEnum):
    SEASONAL_FEED = "seasonal_feed"
    RECIPE_DETAIL = "recipe_detail"
    PLANNER = "planner"


class RecommendationEventType(StrEnum):
    IMPRESSION = "impression"
    OPEN = "open"
    FAVOURITE = "favourite"
    UNFAVOURITE = "unfavourite"
    PLAN = "plan"
    UNPLAN = "unplan"


class RecommendationRankingStrategy(StrEnum):
    SEASONAL_ONLY_V1 = "seasonal_only_v1"
    SEASONAL_TFIDF_V1 = "seasonal_tfidf_v1"
