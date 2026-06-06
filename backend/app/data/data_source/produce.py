from app.data.contracts import DataSourceMetadata, DataSourceRegistration
from app.data.data_key import DataKey
from app.data.data_target import EU_SEASONAL_PRODUCE_TARGETS
from app.data.enums import DataDomain

EU_SEASONAL_PRODUCE_REGISTRATION = DataSourceRegistration(
    metadata=DataSourceMetadata(
        data_key=DataKey.EU_SEASONAL_PRODUCE,
        domain=DataDomain.PRODUCE,
        name="EU seasonal produce",
        notes="Placeholder registration until a licensed dataset is selected.",
    ),
    targets=EU_SEASONAL_PRODUCE_TARGETS,
)
