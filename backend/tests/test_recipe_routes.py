import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import Protocol, cast

import pytest
from fastapi.testclient import TestClient
from httpx import Response

from app.api.v1.routes import recipes as recipe_routes
from app.auth.dependencies import get_current_user
from app.data.enums import Allergen, CountryCode, DietaryRule, DietPattern, Month
from app.db.session import get_db_session
from app.main import create_app
from app.models import User, UserAllergen, UserDietaryRule, UserProfile
from app.schemas.recipe import SeasonalRecipeListResponse, SeasonalRecipeResponse


class SyncTestClient(Protocol):
    def get(self, url: str) -> Response: ...


async def dummy_db_session() -> AsyncGenerator[object, None]:
    yield object()


def authenticated_user(country_code: str | None = "GB") -> User:
    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        email="user@example.com",
        password_hash="unused",
        is_active=True,
        is_verified=False,
        created_at=datetime(2026, 6, 10, tzinfo=UTC),
        updated_at=datetime(2026, 6, 10, tzinfo=UTC),
    )
    if country_code is not None:
        user.profile = UserProfile(user_id=user_id, country_code=country_code)
    return user


def test_seasonal_recipes_require_authentication() -> None:
    client = cast(SyncTestClient, TestClient(create_app()))

    response = client.get("/api/v1/recipes/seasonal")

    assert response.status_code == 401


def test_seasonal_recipes_use_profile_country_for_produce_matching(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = create_app()
    user = authenticated_user()
    assert user.profile is not None
    user.profile.allergy_status = "provided"
    user.profile.allergens = [
        UserAllergen(user_id=user.id, allergen=Allergen.PEANUTS.value),
        UserAllergen(user_id=user.id, allergen=Allergen.MILK.value),
    ]
    user.profile.diet_pattern = DietPattern.PESCATARIAN.value
    user.profile.dietary_rules = [
        UserDietaryRule(user_id=user.id, dietary_rule=DietaryRule.AVOID_BEEF.value)
    ]

    async def override_current_user() -> User:
        return user

    async def override_list_seasonal_recipes(
        session: object,
        *,
        country_code: CountryCode,
        month: Month,
        page: int,
        page_size: int,
        category: str | None,
        area: str | None,
        country_of_origin: str | None,
        excluded_allergens: set[Allergen] | None,
        diet_pattern: DietPattern | None,
        dietary_rules: set[DietaryRule] | None,
    ) -> SeasonalRecipeListResponse:
        assert session is not None
        assert country_code == CountryCode.UNITED_KINGDOM
        assert month == Month.JUNE
        assert page == 2
        assert page_size == 10
        assert category == "Vegetarian"
        assert area == "Italian"
        assert country_of_origin == "Italy"
        assert excluded_allergens == {Allergen.PEANUTS, Allergen.MILK}
        assert diet_pattern == DietPattern.PESCATARIAN
        assert dietary_rules == {DietaryRule.AVOID_BEEF}
        return SeasonalRecipeListResponse(
            country_code=country_code,
            month=month,
            page=page,
            page_size=page_size,
            total=1,
            items=[
                SeasonalRecipeResponse(
                    id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
                    name="Seasonal Pasta",
                    category="Vegetarian",
                    area="Italian",
                    country_of_origin="Italy",
                    thumbnail_url=None,
                    instructions="Cook it.",
                    matched_seasonal_produce=["tomato", "courgette"],
                    matched_seasonal_produce_count=2,
                )
            ],
        )

    app.dependency_overrides[get_current_user] = override_current_user
    app.dependency_overrides[get_db_session] = dummy_db_session
    monkeypatch.setattr(recipe_routes, "list_seasonal_recipes", override_list_seasonal_recipes)

    client = cast(SyncTestClient, TestClient(app))
    url = (
        "/api/v1/recipes/seasonal?"
        "month=6&page=2&page_size=10&category=Vegetarian&area=Italian&origin=Italy"
    )

    response = client.get(url)

    assert response.status_code == 200
    assert response.json()["country_code"] == "GB"
    assert response.json()["items"][0]["matched_seasonal_produce"] == ["tomato", "courgette"]


def test_seasonal_recipes_do_not_filter_allergens_without_provided_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = create_app()
    user = authenticated_user()

    async def override_current_user() -> User:
        return user

    async def override_list_seasonal_recipes(
        session: object,
        *,
        country_code: CountryCode,
        month: Month,
        page: int,
        page_size: int,
        category: str | None,
        area: str | None,
        country_of_origin: str | None,
        excluded_allergens: set[Allergen] | None,
        diet_pattern: DietPattern | None,
        dietary_rules: set[DietaryRule] | None,
    ) -> SeasonalRecipeListResponse:
        _ = session, category, area, country_of_origin
        assert country_code == CountryCode.UNITED_KINGDOM
        assert month == Month.JUNE
        assert page == 1
        assert page_size == 20
        assert excluded_allergens == set()
        assert diet_pattern is None
        assert dietary_rules == set()
        return SeasonalRecipeListResponse(
            country_code=country_code,
            month=month,
            page=page,
            page_size=page_size,
            total=0,
            items=[],
        )

    app.dependency_overrides[get_current_user] = override_current_user
    app.dependency_overrides[get_db_session] = dummy_db_session
    monkeypatch.setattr(recipe_routes, "list_seasonal_recipes", override_list_seasonal_recipes)

    client = cast(SyncTestClient, TestClient(app))

    response = client.get("/api/v1/recipes/seasonal?month=6")

    assert response.status_code == 200


@pytest.mark.parametrize("country_code", [None, "US"])
def test_seasonal_recipes_require_supported_profile_country(country_code: str | None) -> None:
    app = create_app()
    user = authenticated_user(country_code)

    async def override_current_user() -> User:
        return user

    app.dependency_overrides[get_current_user] = override_current_user
    app.dependency_overrides[get_db_session] = dummy_db_session

    client = cast(SyncTestClient, TestClient(app))

    response = client.get("/api/v1/recipes/seasonal?month=6")

    assert response.status_code == 422
    assert response.json() == {
        "detail": "A supported profile country is required for seasonal recipes"
    }


@pytest.mark.parametrize("query", ["month=13", "page=0", "page_size=101"])
def test_seasonal_recipes_validate_query(query: str) -> None:
    app = create_app()
    user = authenticated_user()

    async def override_current_user() -> User:
        return user

    app.dependency_overrides[get_current_user] = override_current_user
    app.dependency_overrides[get_db_session] = dummy_db_session

    client = cast(SyncTestClient, TestClient(app))

    response = client.get(f"/api/v1/recipes/seasonal?{query}")

    assert response.status_code == 422
