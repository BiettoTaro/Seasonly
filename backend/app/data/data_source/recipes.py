from app.data.contracts import DataSourceMetadata, DataSourceRegistration
from app.data.data_key import DataKey
from app.data.data_target import EU_RECIPE_TARGETS
from app.data.enums import DataDomain

EU_RECIPE_REGISTRATION = DataSourceRegistration(
    metadata=DataSourceMetadata(
        data_key=DataKey.EU_RECIPES,
        domain=DataDomain.RECIPES,
        name="EU recipes",
        notes="Placeholder registration until recipe source licensing is confirmed.",
    ),
    targets=EU_RECIPE_TARGETS,
)
