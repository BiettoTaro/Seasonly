import asyncio
import string
from collections.abc import Mapping
from typing import cast, final

import httpx

from app.core.config import settings


class MealDBClientError(RuntimeError):
    pass


class MealDBConfigurationError(MealDBClientError):
    pass


class MealDBResponseError(MealDBClientError):
    pass


@final
class MealDBClient:
    def __init__(
        self,
        *,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout_seconds: float | None = None,
        retries: int | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        resolved_api_key = api_key if api_key is not None else settings.recipes_api_key
        if resolved_api_key is None or not resolved_api_key.strip():
            raise MealDBConfigurationError("RECIPES_API_KEY is required")

        resolved_base_url = base_url if base_url is not None else settings.recipes_base_url
        self._api_root = f"{resolved_base_url.rstrip('/')}/{resolved_api_key.strip()}/"
        self._timeout_seconds: float = float(
            timeout_seconds
            if timeout_seconds is not None
            else settings.recipes_request_timeout_seconds
        )
        self._retries: int = int(
            retries if retries is not None else settings.recipes_request_retries
        )
        self._http_client = http_client

    async def fetch_categories(self) -> list[dict[str, object]]:
        return await self._request_collection("categories.php", collection="categories")

    async def fetch_ingredients(self) -> list[dict[str, object]]:
        return await self._request_collection(
            "list.php",
            params={"i": "list"},
            collection="meals",
        )

    async def fetch_all_recipes(self) -> list[dict[str, object]]:
        recipes_by_id: dict[str, dict[str, object]] = {}
        for first_character in string.ascii_lowercase + string.digits:
            recipes = await self._request_collection(
                "search.php",
                params={"f": first_character},
                collection="meals",
                null_is_empty=True,
            )
            for recipe in recipes:
                provider_id = recipe.get("idMeal")
                if not isinstance(provider_id, str) or not provider_id.strip():
                    raise MealDBResponseError("Recipe response contains no valid idMeal")
                recipes_by_id[provider_id] = recipe
        return list(recipes_by_id.values())

    async def _request_collection(
        self,
        endpoint: str,
        *,
        collection: str,
        params: Mapping[str, str] | None = None,
        null_is_empty: bool = False,
    ) -> list[dict[str, object]]:
        response_data = await self._request_json(endpoint, params=params)
        value = response_data.get(collection)
        if value is None and null_is_empty:
            return []
        if not isinstance(value, list):
            raise MealDBResponseError(f"Expected {collection!r} to be a list")
        items: list[dict[str, object]] = []
        for item in cast(list[object], value):
            if not isinstance(item, dict):
                raise MealDBResponseError(f"Expected every {collection!r} item to be an object")
            items.append(_string_keyed_object(cast(dict[object, object], item)))
        return items

    async def _request_json(
        self,
        endpoint: str,
        *,
        params: Mapping[str, str] | None = None,
    ) -> dict[str, object]:
        for attempt in range(self._retries + 1):
            try:
                if self._http_client is not None:
                    response = await self._http_client.get(
                        f"{self._api_root}{endpoint}",
                        params=params,
                        timeout=self._timeout_seconds,
                    )
                else:
                    async with httpx.AsyncClient() as client:
                        response = await client.get(
                            f"{self._api_root}{endpoint}",
                            params=params,
                            timeout=self._timeout_seconds,
                        )
                _ = response.raise_for_status()
                payload = cast(object, response.json())
                if not isinstance(payload, dict):
                    raise MealDBResponseError("Expected a JSON object response")
                return _string_keyed_object(cast(dict[object, object], payload))
            except (httpx.HTTPError, ValueError, MealDBResponseError):
                if attempt < self._retries:
                    await asyncio.sleep(0.25)

        raise MealDBClientError(f"MealDB request failed for {endpoint}") from None


def _string_keyed_object(value: dict[object, object]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, item in value.items():
        if not isinstance(key, str):
            raise MealDBResponseError("Expected every JSON object key to be a string")
        result[key] = item
    return result
