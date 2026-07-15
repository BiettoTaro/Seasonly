import uuid
from collections.abc import AsyncGenerator
from typing import Protocol, cast

import pytest
from fastapi.testclient import TestClient
from httpx import Response

from app.api.v1.routes import produce as produce_routes
from app.data.enums import CountryCode, Month, ProduceType
from app.db.session import get_db_session
from app.main import create_app
from app.schemas.produce import SeasonalProduceGroupedResponse, SeasonalProduceResponse


class SyncTestClient(Protocol):
    def get(self, url: str) -> Response: ...


async def dummy_db_session() -> AsyncGenerator[object, None]:
    yield object()


def test_read_seasonal_produce_returns_database_results(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = create_app()

    async def override_list_seasonal_produce(
        session: object,
        country_code: CountryCode,
        month: Month,
    ) -> SeasonalProduceGroupedResponse:
        assert session is not None
        assert country_code == CountryCode.UNITED_KINGDOM
        assert month == Month.JUNE
        return SeasonalProduceGroupedResponse(
            fruits=[
                SeasonalProduceResponse(
                    id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
                    name="strawberry",
                    type=ProduceType.FRUIT,
                    mealdb_name="strawberries",
                    country_code=CountryCode.UNITED_KINGDOM,
                    country_name="United Kingdom",
                    month=Month.JUNE,
                    source_name="EUFIC",
                    source_url="https://www.eufic.org/",
                )
            ],
            vegetables=[],
        )

    app.dependency_overrides[get_db_session] = dummy_db_session
    monkeypatch.setattr(produce_routes, "list_seasonal_produce", override_list_seasonal_produce)
    client = cast(SyncTestClient, TestClient(app))

    response = client.get("/api/v1/produce/seasonal?country=GB&month=6")

    assert response.status_code == 200
    assert response.json() == {
        "fruits": [
            {
                "id": "00000000-0000-0000-0000-000000000001",
                "name": "strawberry",
                "type": "fruit",
                "mealdb_name": "strawberries",
                "country_code": "GB",
                "country_name": "United Kingdom",
                "month": 6,
                "source_name": "EUFIC",
                "source_url": "https://www.eufic.org/",
            }
        ],
        "vegetables": [],
    }


@pytest.mark.parametrize("query", ["country=US&month=6", "country=GB&month=13"])
def test_read_seasonal_produce_validates_query(query: str) -> None:
    client = cast(SyncTestClient, TestClient(create_app()))

    response = client.get(f"/api/v1/produce/seasonal?{query}")

    assert response.status_code == 422
