from app.data.data_key import DataKey
from app.data.enums import DataDomain, DataTargetType
from app.data.schemas import DataSourceMetadata, DataSourceRegistration, DataTarget

DATA_CATALOG: dict[DataKey, DataSourceRegistration] = {
    DataKey.EU_SEASONAL_PRODUCE: DataSourceRegistration(
        metadata=DataSourceMetadata(
            data_key=DataKey.EU_SEASONAL_PRODUCE,
            domain=DataDomain.PRODUCE,
            name="EU seasonal produce",
            notes="Placeholder registration until a licensed dataset is selected.",
        ),
        targets=(
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
        ),
    ),
    DataKey.EU_RECIPES: DataSourceRegistration(
        metadata=DataSourceMetadata(
            data_key=DataKey.EU_RECIPES,
            domain=DataDomain.RECIPES,
            name="EU recipes",
            notes="Placeholder registration until recipe source licensing is confirmed.",
        ),
        targets=(
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
        ),
    ),
    DataKey.RECOMMENDATION_EVENTS: DataSourceRegistration(
        metadata=DataSourceMetadata(
            data_key=DataKey.RECOMMENDATION_EVENTS,
            domain=DataDomain.RECOMMENDATIONS,
            name="Recommendation events",
            notes="Internal event data for future recommendation features.",
        ),
        targets=(
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
        ),
    ),
}


def list_data_registrations() -> tuple[DataSourceRegistration, ...]:
    return tuple(DATA_CATALOG.values())


def get_data_registration(data_key: DataKey) -> DataSourceRegistration:
    try:
        return DATA_CATALOG[data_key]
    except KeyError as e:
        raise ValueError(f"Unknown data key: {data_key}") from e


def get_data_targets(data_key: DataKey) -> tuple[DataTarget, ...]:
    return get_data_registration(data_key).targets
