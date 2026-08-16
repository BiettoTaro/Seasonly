from fastapi.testclient import TestClient
from pydantic import TypeAdapter

from app.data.contracts import DataSourceRegistration, DataTargetResponse
from app.data.data_key import DataKey
from app.main import create_app


def test_list_data_registrations() -> None:
    client = TestClient(create_app())

    response = client.get("/api/v1/data/registrations")

    assert response.status_code == 200
    registrations = TypeAdapter(tuple[DataSourceRegistration, ...]).validate_json(response.content)
    assert {registration.metadata.data_key for registration in registrations} == {
        DataKey.EU_SEASONAL_PRODUCE,
        DataKey.THEMEALDB_RECIPES,
        DataKey.RECOMMENDATION_EVENTS,
    }


def test_read_data_targets() -> None:
    client = TestClient(create_app())

    response = client.get("/api/v1/data/targets/themealdb_recipes")

    assert response.status_code == 200
    targets = DataTargetResponse.model_validate_json(response.content)
    assert targets.data_key == DataKey.THEMEALDB_RECIPES
    assert {target.name for target in targets.targets} == {
        "recipe_categories",
        "recipes",
        "ingredients",
        "recipe_ingredients",
        "tags",
        "recipe_tags",
        "recipe_allergen_assessments",
    }
