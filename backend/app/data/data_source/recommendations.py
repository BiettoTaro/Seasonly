from app.data.contracts import DataSourceMetadata, DataSourceRegistration
from app.data.data_key import DataKey
from app.data.data_target import RECOMMENDATION_EVENT_TARGETS
from app.data.enums import DataDomain

RECOMMENDATION_EVENT_REGISTRATION = DataSourceRegistration(
    metadata=DataSourceMetadata(
        data_key=DataKey.RECOMMENDATION_EVENTS,
        domain=DataDomain.RECOMMENDATIONS,
        name="Recommendation events",
        notes=(
            "Consent-gated production events support live personalization only in the current "
            "phase. Offline ML accepts explicitly synthetic datasets and must not treat brief "
            "private-pilot activity as training or effectiveness evidence."
        ),
    ),
    targets=RECOMMENDATION_EVENT_TARGETS,
)
