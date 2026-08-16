import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from app.api.v1.routes import onboarding as onboarding_routes
from app.api.v1.routes import reference as reference_routes
from app.auth.dependencies import get_current_user
from app.data.enums import (
    AllergyProfileStatus,
    CountryCode,
    CuisinePreferenceStatus,
    LocationSource,
    OnboardingStatus,
    OnboardingStep,
)
from app.db.session import get_db_session
from app.main import create_app
from app.models import User
from app.schemas.onboarding import OnboardingProfileResponse
from app.users.onboarding import IncompleteOnboardingError, InvalidOnboardingUpdateError


class DummySession:
    def __init__(self) -> None:
        self.rolled_back: bool = False

    async def rollback(self) -> None:
        self.rolled_back = True


async def dummy_db_session() -> AsyncGenerator[DummySession, None]:
    yield DummySession()


def authenticated_user() -> User:
    return User(
        id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
        email="user@example.com",
        password_hash="unused",
        is_active=True,
        is_verified=False,
        created_at=datetime(2026, 6, 26, tzinfo=UTC),
        updated_at=datetime(2026, 6, 26, tzinfo=UTC),
    )


def profile_response(user: User) -> OnboardingProfileResponse:
    return OnboardingProfileResponse(
        status=OnboardingStatus.IN_PROGRESS,
        next_step=OnboardingStep.DIET,
        user_id=user.id,
        country_code=CountryCode.UNITED_KINGDOM,
        region_code="GB-ENG",
        location_source=LocationSource.MANUAL,
        privacy_notice_version="2026-06-26",
        privacy_notice_acknowledged_at=datetime(2026, 6, 26, tzinfo=UTC),
        diet_pattern=None,
        allergy_status=AllergyProfileStatus.NOT_PROVIDED,
        allergens=[],
        dietary_rules=[],
        cuisine_preference_status=CuisinePreferenceStatus.NOT_PROVIDED,
        cuisine_areas=[],
        proteins=[],
        completed_at=None,
        updated_at=datetime(2026, 6, 26, tzinfo=UTC),
    )


def test_onboarding_profile_requires_authentication() -> None:
    client = TestClient(create_app())

    response = client.get("/api/v1/me/onboarding")

    assert response.status_code == 401


def test_onboarding_location_route_returns_profile(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = create_app()
    user = authenticated_user()

    async def override_current_user() -> User:
        return user

    async def override_update_location(
        session: object,
        current_user: User,
        payload: object,
    ) -> OnboardingProfileResponse:
        assert session is not None
        assert current_user == user
        assert payload is not None
        return profile_response(user)

    app.dependency_overrides[get_current_user] = override_current_user
    app.dependency_overrides[get_db_session] = dummy_db_session
    monkeypatch.setattr(onboarding_routes, "update_location", override_update_location)
    client = TestClient(app)

    response = client.put(
        "/api/v1/me/onboarding/location",
        json={"country_code": "GB", "region_code": "GB-ENG", "source": "manual"},
    )

    assert response.status_code == 200
    assert response.json()["country_code"] == "GB"
    assert response.json()["next_step"] == "diet"


def test_onboarding_update_validation_errors_return_422(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = create_app()
    user = authenticated_user()

    async def override_current_user() -> User:
        return user

    async def override_update_proteins(
        session: object,
        current_user: User,
        payload: object,
    ) -> OnboardingProfileResponse:
        _ = session, current_user, payload
        raise InvalidOnboardingUpdateError("Pork protein conflicts with avoid_pork.")

    app.dependency_overrides[get_current_user] = override_current_user
    app.dependency_overrides[get_db_session] = dummy_db_session
    monkeypatch.setattr(onboarding_routes, "update_proteins", override_update_proteins)
    client = TestClient(app)

    response = client.put("/api/v1/me/onboarding/proteins", json={"proteins": ["pork"]})

    assert response.status_code == 422
    assert response.json() == {"detail": "Pork protein conflicts with avoid_pork."}


def test_onboarding_complete_returns_field_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = create_app()
    user = authenticated_user()

    async def override_current_user() -> User:
        return user

    async def override_complete_onboarding(
        session: object,
        current_user: User,
    ) -> OnboardingProfileResponse:
        _ = session, current_user
        raise IncompleteOnboardingError(["Country is required."])

    app.dependency_overrides[get_current_user] = override_current_user
    app.dependency_overrides[get_db_session] = dummy_db_session
    monkeypatch.setattr(onboarding_routes, "complete_onboarding", override_complete_onboarding)
    client = TestClient(app)

    response = client.post("/api/v1/me/onboarding/complete")

    assert response.status_code == 422
    assert response.json() == {"detail": {"errors": ["Country is required."]}}


def test_reference_routes_return_onboarding_options(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = create_app()

    async def override_list_countries_with_seasonal_data(
        session: object,
    ) -> set[CountryCode]:
        assert session is not None
        return {CountryCode.UNITED_KINGDOM}

    async def override_list_cuisine_areas(session: object) -> list[str]:
        assert session is not None
        return ["British", "Italian"]

    app.dependency_overrides[get_db_session] = dummy_db_session
    monkeypatch.setattr(
        reference_routes,
        "list_countries_with_seasonal_data",
        override_list_countries_with_seasonal_data,
    )
    monkeypatch.setattr(reference_routes, "list_cuisine_areas", override_list_cuisine_areas)
    client = TestClient(app)

    countries = client.get("/api/v1/reference/countries")
    cuisines = client.get("/api/v1/reference/cuisines")
    allergens = client.get("/api/v1/reference/allergens")
    proteins = client.get("/api/v1/reference/proteins")

    assert countries.status_code == 200
    assert {
        "code": "GB",
        "name": "United Kingdom",
        "seasonal_data_available": True,
        "availability_message": None,
    } in countries.json()
    assert {
        "code": "SI",
        "name": "Slovenia",
        "seasonal_data_available": False,
        "availability_message": "Seasonal data not available",
    } in countries.json()
    assert cuisines.json() == [{"area": "British"}, {"area": "Italian"}]
    assert {"value": "peanuts", "label": "Peanuts"} in allergens.json()
    assert {"value": "chicken", "label": "Chicken"} in proteins.json()
