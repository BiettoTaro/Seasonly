from app.data.contracts import DataTarget
from app.data.enums import DataTargetType

EU_RECIPE_TARGETS: tuple[DataTarget, ...] = (
    DataTarget(
        target_type=DataTargetType.RAW_FILE,
        name="data/raw/recipes",
        description="Original recipe dataset files.",
    ),
    DataTarget(
        target_type=DataTargetType.NORMALIZED_TABLE,
        name="recipes",
        description="Validated recipe records ready for search and recommendation.",
    ),
)
