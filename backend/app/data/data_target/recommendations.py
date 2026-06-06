from app.data.contracts import DataTarget
from app.data.enums import DataTargetType

RECOMMENDATION_EVENT_TARGETS: tuple[DataTarget, ...] = (
    DataTarget(
        target_type=DataTargetType.NORMALIZED_TABLE,
        name="recommendation_events",
        description="User interaction events used by recommendation logic.",
    ),
    DataTarget(
        target_type=DataTargetType.ML_FEATURE_SET,
        name="recommendation_features",
        description="Derived features for model training and evaluation.",
    ),
)
