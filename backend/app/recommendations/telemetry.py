import json
from dataclasses import asdict, dataclass

from app.data.enums import RecommendationRankingStrategy

RECOMMENDATION_FEED_METRIC_EVENT = "recommendation_feed_built"


@dataclass(frozen=True)
class RecommendationFeedMeasurement:
    ranking_strategy: RecommendationRankingStrategy
    duration_ms: float
    eligible_count: int
    returned_count: int
    personalized: bool
    empty_feed: bool

    def __post_init__(self) -> None:
        if self.duration_ms < 0:
            raise ValueError("Recommendation feed duration cannot be negative")
        if self.eligible_count < 0 or self.returned_count < 0:
            raise ValueError("Recommendation feed counts cannot be negative")
        if self.returned_count > self.eligible_count:
            raise ValueError("Returned recommendation count cannot exceed eligible count")
        if self.empty_feed is not (self.returned_count == 0):
            raise ValueError("Empty-feed status must match the returned count")

    def to_json(self) -> str:
        payload = {
            "event": RECOMMENDATION_FEED_METRIC_EVENT,
            **asdict(self),
            "duration_ms": round(self.duration_ms, 3),
        }
        return json.dumps(payload, separators=(",", ":"), sort_keys=True)
