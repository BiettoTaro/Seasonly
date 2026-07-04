import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import Protocol, cast

import pytest
from fastapi.testclient import TestClient
from httpx import Response

from app.api.v1.routes import me as me_routes
from app.auth.dependencies import get_current_user
from app.db.session import get_db_session
from app.main import create_app
from app.models import User
from app.schemas.user_recipe import (
    FavouriteRecipeResponse,
    PlannedMealCreate,
    PlannedMealResponse,
    RecipeHistoryResponse,
    RecipeSummaryResponse,
)


class SyncTestClient(Protocol):
    def delete(self, url: str) -> Response: ...
    def get(self, url: str) -> Response: ...
    def post(self, url: str, *, json: object) -> Response: ...
    def put(self, url: str) -> Response: ...


async def dummy_db_session() -> AsyncGenerator[object, None]:
    yield object()


def authenticated_user() -> User:
    user_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    return User(
        id=user_id,
        email="user@example.com",
        password_hash="unused",
        is_active=True,
        is_verified=False,
        created_at=datetime(2026, 6, 10, tzinfo=UTC),
        updated_at=datetime(2026, 6, 10, tzinfo=UTC),
    )


def recipe_summary() -> RecipeSummaryResponse:
    return RecipeSummaryResponse(
        id=uuid.UUID("00000000-0000-0000-0000-000000000002"),
        name="Seasonal Pasta",
        category="Vegetarian",
        area="Italian",
        country_of_origin="Italy",
        thumbnail_url=None,
    )


@pytest.mark.parametrize(
    ("method", "url"),
    [
        ("get", "/api/v1/me/favourites"),
        ("put", "/api/v1/me/favourites/00000000-0000-0000-0000-000000000002"),
        ("get", "/api/v1/me/history/recipes"),
        ("get", "/api/v1/me/planner"),
    ],
)
def test_user_recipe_routes_require_authentication(method: str, url: str) -> None:
    client = cast(SyncTestClient, TestClient(create_app()))

    response = getattr(client, method)(url)

    assert response.status_code == 401


def test_favourite_routes_use_current_user(monkeypatch: pytest.MonkeyPatch) -> None:
    app = create_app()
    user = authenticated_user()
    recipe_id = uuid.UUID("00000000-0000-0000-0000-000000000002")

    async def override_current_user() -> User:
        return user

    async def override_add_favourite(
        session: object,
        *,
        user_id: uuid.UUID,
        recipe_id: uuid.UUID,
    ) -> FavouriteRecipeResponse:
        assert session is not None
        assert user_id == user.id
        assert recipe_id == recipe_summary().id
        return FavouriteRecipeResponse(
            recipe=recipe_summary(),
            created_at=datetime(2026, 6, 30, tzinfo=UTC),
        )

    app.dependency_overrides[get_current_user] = override_current_user
    app.dependency_overrides[get_db_session] = dummy_db_session
    monkeypatch.setattr(me_routes, "add_favourite", override_add_favourite)

    client = cast(SyncTestClient, TestClient(app))

    response = client.put(f"/api/v1/me/favourites/{recipe_id}")

    assert response.status_code == 200
    assert response.json()["recipe"]["name"] == "Seasonal Pasta"


def test_history_limit_is_validated() -> None:
    app = create_app()
    user = authenticated_user()

    async def override_current_user() -> User:
        return user

    app.dependency_overrides[get_current_user] = override_current_user
    app.dependency_overrides[get_db_session] = dummy_db_session

    client = cast(SyncTestClient, TestClient(app))

    response = client.get("/api/v1/me/history/recipes?limit=0")

    assert response.status_code == 422


def test_history_route_records_recipe_view(monkeypatch: pytest.MonkeyPatch) -> None:
    app = create_app()
    user = authenticated_user()
    recipe_id = uuid.UUID("00000000-0000-0000-0000-000000000002")

    async def override_current_user() -> User:
        return user

    async def override_record_history(
        session: object,
        *,
        user_id: uuid.UUID,
        recipe_id: uuid.UUID,
    ) -> RecipeHistoryResponse:
        assert session is not None
        assert user_id == user.id
        assert recipe_id == recipe_summary().id
        return RecipeHistoryResponse(
            recipe=recipe_summary(),
            viewed_at=datetime(2026, 6, 30, tzinfo=UTC),
        )

    app.dependency_overrides[get_current_user] = override_current_user
    app.dependency_overrides[get_db_session] = dummy_db_session
    monkeypatch.setattr(me_routes, "record_history", override_record_history)

    client = cast(SyncTestClient, TestClient(app))

    response = client.put(f"/api/v1/me/history/recipes/{recipe_id}")

    assert response.status_code == 200
    assert response.json()["viewed_at"] == "2026-06-30T00:00:00Z"


def test_planner_route_creates_meal(monkeypatch: pytest.MonkeyPatch) -> None:
    app = create_app()
    user = authenticated_user()
    meal_id = uuid.UUID("00000000-0000-0000-0000-000000000003")
    recipe_id = recipe_summary().id

    async def override_current_user() -> User:
        return user

    async def override_add_planned_meal(
        session: object,
        *,
        user_id: uuid.UUID,
        payload: PlannedMealCreate,
    ) -> PlannedMealResponse:
        assert session is not None
        assert user_id == user.id
        assert payload.recipe_id == recipe_id
        assert payload.day_of_week == 1
        assert payload.meal_slot == "dinner"
        return PlannedMealResponse(
            id=meal_id,
            recipe=recipe_summary(),
            day_of_week=payload.day_of_week,
            meal_slot=payload.meal_slot,
            created_at=datetime(2026, 6, 30, tzinfo=UTC),
        )

    app.dependency_overrides[get_current_user] = override_current_user
    app.dependency_overrides[get_db_session] = dummy_db_session
    monkeypatch.setattr(me_routes, "add_planned_meal", override_add_planned_meal)

    client = cast(SyncTestClient, TestClient(app))

    response = client.post(
        "/api/v1/me/planner",
        json={
            "recipe_id": str(recipe_id),
            "day_of_week": 1,
            "meal_slot": "dinner",
        },
    )

    assert response.status_code == 201
    assert response.json()["id"] == str(meal_id)
