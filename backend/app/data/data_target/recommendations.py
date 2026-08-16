from app.data.contracts import DataTarget
from app.data.enums import DataTargetType

RECOMMENDATION_EVENT_TARGETS: tuple[DataTarget, ...] = (
    DataTarget(
        target_type=DataTargetType.NORMALIZED_TABLE,
        name="recommendation_events",
        description=(
            "Consented operational personalization events. Private-pilot events are excluded "
            "from current ML training and effectiveness evaluation."
        ),
    ),
    DataTarget(
        target_type=DataTargetType.ML_FEATURE_SET,
        name="recommendation_features",
        description=(
            "Prototype features derived only from explicitly synthetic, versioned datasets."
        ),
    ),
)
