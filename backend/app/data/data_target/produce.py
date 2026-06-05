from app.data.contracts import DataTarget
from app.data.enums import DataTargetType

EU_SEASONAL_PRODUCE_TARGETS: tuple[DataTarget, ...] = (
    DataTarget(
        target_type=DataTargetType.RAW_FILE,
        name="data/raw/produce",
        description="Original seasonal produce dataset files.",
    ),
    DataTarget(
        target_type=DataTargetType.NORMALIZED_TABLE,
        name="seasonal_produce",
        description="Validated produce records ready for API use.",
    ),
)
