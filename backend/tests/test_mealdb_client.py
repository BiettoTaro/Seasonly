import json

import httpx
import pytest

from app.recipes.client import (
    MealDBClient,
    MealDBConfigurationError,
    MealDBResponseError,
)


def json_response(
    request: httpx.Request,
    payload: object,
    status_code: int = 200,
) -> httpx.Response:
    return httpx.Response(status_code, content=json.dumps(payload), request=request)


def test_mealdb_client_requires_api_key() -> None:
    with pytest.raises(MealDBConfigurationError, match="RECIPES_API_KEY is required"):
        _ = MealDBClient(api_key="")


async def test_fetch_categories_returns_category_objects() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/json/v2/test-key/categories.php"
        return json_response(request, {"categories": [{"idCategory": "1"}]})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = MealDBClient(
            base_url="https://example.com/api/json/v2/",
            api_key="test-key",
            retries=0,
            http_client=http_client,
        )

        assert await client.fetch_categories() == [{"idCategory": "1"}]


async def test_fetch_all_recipes_deduplicates_and_accepts_null_results() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        first_character = request.url.params["f"]
        meals = [{"idMeal": "1", "strMeal": "One"}] if first_character in {"a", "1"} else None
        return json_response(request, {"meals": meals})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = MealDBClient(
            base_url="https://example.com/api/json/v2/",
            api_key="test-key",
            retries=0,
            http_client=http_client,
        )

        assert await client.fetch_all_recipes() == [{"idMeal": "1", "strMeal": "One"}]


async def test_mealdb_client_rejects_invalid_collection_shape() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return json_response(request, {"categories": {"idCategory": "1"}})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = MealDBClient(
            base_url="https://example.com/api/json/v2/",
            api_key="test-key",
            retries=0,
            http_client=http_client,
        )

        with pytest.raises(MealDBResponseError, match="categories"):
            _ = await client.fetch_categories()
