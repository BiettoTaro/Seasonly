import json
import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import cast

import pytest
from fastapi.testclient import TestClient

from app.api.v1.routes import recommendations as recommendation_routes
from app.auth.dependencies import get_current_user
from app.data.enums import CountryCode, Month, RecommendationRankingStrategy
from app.db.session import get_db_session
from app.main import create_app
from app.models import User
from app.recommendations.events import PersonalizationConsentRequiredError
from app.schemas.recipe import SeasonalRecipeResponse
from app.schemas.recommendation import (
    PersonalizationConsentResponse,
    RecommendationFeedResponse,
    RecommendationImpressionBatchCreate,
)


async def dummy_db_session() -> AsyncGenerator[object, None]:
    yield object()


def authenticated_user() -> User:
    return User(
        id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
        email="user@example.com",
        password_hash="unused",
        is_active=True,
        is_verified=False,
        created_at=datetime(2026, 7, 24, tzinfo=UTC),
        updated_at=datetime(2026, 7, 24, tzinfo=UTC),
    )


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("get", "/api/v1/me/recommendations/consent"),
        ("get", "/api/v1/me/recommendations/feed"),
        ("put", "/api/v1/me/recommendations/consent"),
        ("delete", "/api/v1/me/recommendations/consent"),
        ("post", "/api/v1/me/recommendations/impressions"),
    ],
)
def test_recommendation_routes_require_authentication(method: str, path: str) -> None:
    client = TestClient(create_app())
    match method:
        case "get":
            response = client.get(path)
        case "put":
            response = client.put(path, json={"explicit_consent": True})
        case "delete":
            response = client.delete(path)
        case "post":
            response = client.post(path, json={"impressions": []})
        case _:
            raise AssertionError(f"Unsupported test method {method}")

    assert response.status_code == 401


def test_personalization_consent_route_uses_current_user(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = create_app()
    user = authenticated_user()

    async def override_current_user() -> User:
        return user

    async def override_grant(
        session: object,
        *,
        user_id: uuid.UUID,
    ) -> PersonalizationConsentResponse:
        assert session is not None
        assert user_id == user.id
        return PersonalizationConsentResponse(
            active=True,
            notice_version="2026-07-24",
            granted_at=datetime(2026, 7, 24, tzinfo=UTC),
            retention_days=365,
        )

    app.dependency_overrides[get_current_user] = override_current_user
    app.dependency_overrides[get_db_session] = dummy_db_session
    monkeypatch.setattr(
        recommendation_routes,
        "grant_personalization_consent",
        override_grant,
    )

    response = TestClient(app).put(
        "/api/v1/me/recommendations/consent",
        json={"explicit_consent": True},
    )

    assert response.status_code == 200
    assert response.json()["active"] is True
    assert response.json()["retention_days"] == 365


def test_recommendation_feed_uses_current_user_and_query(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = create_app()
    user = authenticated_user()
    recipe_id = uuid.UUID("00000000-0000-0000-0000-000000000002")

    async def override_current_user() -> User:
        return user

    async def override_build_feed(
        session: object,
        *,
        user: User,
        month: Month,
        limit: int,
        ranking_mode: RecommendationRankingStrategy,
    ) -> RecommendationFeedResponse:
        assert session is not None
        assert user.id == authenticated_user().id
        assert month == Month.JULY
        assert limit == 12
        assert ranking_mode is RecommendationRankingStrategy.SEASONAL_TFIDF_V1
        return RecommendationFeedResponse(
            slate_id=uuid.UUID("00000000-0000-0000-0000-000000000003"),
            country_code=CountryCode.UNITED_KINGDOM,
            month=Month.JULY,
            ranking_strategy=RecommendationRankingStrategy.SEASONAL_TFIDF_V1,
            personalized=True,
            total=1,
            items=[
                SeasonalRecipeResponse(
                    id=recipe_id,
                    name="Recommended pasta",
                    category="Main",
                    area="Italian",
                    country_of_origin="Italy",
                    thumbnail_url=None,
                    instructions="Cook it.",
                    matched_seasonal_produce=["tomato"],
                    matched_seasonal_produce_count=1,
                )
            ],
        )

    app.dependency_overrides[get_current_user] = override_current_user
    app.dependency_overrides[get_db_session] = dummy_db_session
    monkeypatch.setattr(
        recommendation_routes,
        "build_recommendation_feed",
        override_build_feed,
    )

    response = TestClient(app).get("/api/v1/me/recommendations/feed?month=7&limit=12")

    assert response.status_code == 200
    assert response.json()["ranking_strategy"] == "seasonal_tfidf_v1"
    assert response.json()["personalized"] is True
    assert response.json()["items"][0]["id"] == str(recipe_id)


def test_recommendation_feed_logs_only_privacy_safe_measurement_fields(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    app = create_app()
    user = authenticated_user()

    async def override_current_user() -> User:
        return user

    async def override_build_feed(
        session: object,
        *,
        user: User,
        month: Month,
        limit: int,
        ranking_mode: RecommendationRankingStrategy,
    ) -> RecommendationFeedResponse:
        _ = session, user, limit
        return RecommendationFeedResponse(
            slate_id=uuid.UUID("00000000-0000-0000-0000-000000000003"),
            country_code=CountryCode.UNITED_KINGDOM,
            month=month,
            ranking_strategy=ranking_mode,
            personalized=False,
            total=0,
            items=[],
        )

    app.dependency_overrides[get_current_user] = override_current_user
    app.dependency_overrides[get_db_session] = dummy_db_session
    monkeypatch.setattr(
        recommendation_routes,
        "build_recommendation_feed",
        override_build_feed,
    )

    with caplog.at_level("INFO", logger=recommendation_routes.__name__):
        response = TestClient(app).get("/api/v1/me/recommendations/feed?month=7")

    assert response.status_code == 200
    metric = cast(dict[str, object], json.loads(caplog.records[-1].message))
    assert set(metric) == {
        "duration_ms",
        "eligible_count",
        "empty_feed",
        "event",
        "personalized",
        "ranking_strategy",
        "returned_count",
    }
    assert metric["event"] == "recommendation_feed_built"
    assert metric["ranking_strategy"] == "seasonal_tfidf_v1"
    assert metric["empty_feed"] is True


def test_impressions_are_rejected_without_consent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = create_app()
    user = authenticated_user()
    recipe_id = uuid.UUID("00000000-0000-0000-0000-000000000002")

    async def override_current_user() -> User:
        return user

    async def override_record(
        session: object,
        *,
        user_id: uuid.UUID,
        payload: RecommendationImpressionBatchCreate,
    ) -> int:
        _ = session, user_id, payload
        raise PersonalizationConsentRequiredError("Consent required.")

    app.dependency_overrides[get_current_user] = override_current_user
    app.dependency_overrides[get_db_session] = dummy_db_session
    monkeypatch.setattr(
        recommendation_routes,
        "record_recommendation_impressions",
        override_record,
    )

    response = TestClient(app).post(
        "/api/v1/me/recommendations/impressions",
        json={
            "slate_id": str(uuid.uuid4()),
            "impressions": [
                {
                    "event_id": str(uuid.uuid4()),
                    "recipe_id": str(recipe_id),
                    "position": 1,
                }
            ],
        },
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Consent required."}
