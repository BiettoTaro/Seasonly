from app.data.contracts import DataSourceMetadata, DataSourceRegistration
from app.data.data_key import DataKey
from app.data.data_target import THEMEALDB_RECIPE_TARGETS
from app.data.enums import DataDomain

THEMEALDB_RECIPE_REGISTRATION = DataSourceRegistration(
    metadata=DataSourceMetadata(
        data_key=DataKey.THEMEALDB_RECIPES,
        domain=DataDomain.RECIPES,
        name="TheMealDB recipes",
        notes=(
            "International recipe catalog imported from TheMealDB. Preserve attribution, provider "
            "IDs, raw payloads, and fetched timestamps."
        ),
    ),
    targets=THEMEALDB_RECIPE_TARGETS,
)
