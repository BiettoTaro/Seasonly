from app.data.contracts import DataSourceMetadata, DataSourceRegistration
from app.data.data_key import DataKey
from app.data.data_target import RECOMMENDATION_EVENT_TARGETS
from app.data.enums import DataDomain

RECOMMENDATION_EVENT_REGISTRATION = DataSourceRegistration(
    metadata=DataSourceMetadata(
        data_key=DataKey.RECOMMENDATION_EVENTS,
        domain=DataDomain.RECOMMENDATIONS,
        name="Recommendation events",
        notes="Internal event data for future recommendation features.",
    ),
    targets=RECOMMENDATION_EVENT_TARGETS,
)
