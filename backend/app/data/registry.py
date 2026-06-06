from app.data.contracts import DataSourceRegistration, DataTarget
from app.data.data_key import DataKey
from app.data.data_source import (
    EU_RECIPE_REGISTRATION,
    EU_SEASONAL_PRODUCE_REGISTRATION,
    RECOMMENDATION_EVENT_REGISTRATION,
)

DATA_REGISTRY: dict[DataKey, DataSourceRegistration] = {
    DataKey.EU_SEASONAL_PRODUCE: EU_SEASONAL_PRODUCE_REGISTRATION,
    DataKey.EU_RECIPES: EU_RECIPE_REGISTRATION,
    DataKey.RECOMMENDATION_EVENTS: RECOMMENDATION_EVENT_REGISTRATION,
}


def list_data_registrations() -> tuple[DataSourceRegistration, ...]:
    return tuple(DATA_REGISTRY.values())


def get_data_registration(data_key: DataKey) -> DataSourceRegistration:
    try:
        return DATA_REGISTRY[data_key]
    except KeyError as e:
        raise ValueError(f"Unknown data key: {data_key}") from e


def get_data_targets(data_key: DataKey) -> tuple[DataTarget, ...]:
    return get_data_registration(data_key).targets
