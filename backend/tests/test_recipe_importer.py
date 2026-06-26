import pytest

from app.recipes.importer import normalize_snapshot


def category_payload() -> dict[str, object]:
    return {
        "idCategory": "1",
        "strCategory": "Vegetarian",
        "strCategoryDescription": None,
        "strCategoryThumb": None,
    }


def ingredient_payload() -> dict[str, object]:
    return {
        "idIngredient": "1",
        "strIngredient": "Garlic",
        "strDescription": None,
        "strThumb": None,
        "strType": None,
    }


def recipe_payload() -> dict[str, object]:
    return {
        "idMeal": "1",
        "strMeal": "Garlic Pasta",
        "strCategory": "Vegetarian",
        "strArea": "Italian",
        "strCountry": "Italy",
        "strInstructions": "Cook it.",
        "strIngredient1": "Garlic",
        "strMeasure1": "2 cloves",
    }


def test_normalize_snapshot_validates_complete_snapshot() -> None:
    snapshot = normalize_snapshot(
        categories=[category_payload()],
        ingredients=[ingredient_payload()],
        recipes=[recipe_payload()],
    )

    assert snapshot["categories"][0]["provider_category_id"] == "1"
    assert snapshot["ingredients"][0]["normalized_name"] == "garlic"
    assert snapshot["recipes"][0]["country_of_origin"] == "Italy"


@pytest.mark.parametrize(
    ("field", "message"),
    [
        ("categories", "category snapshot is empty"),
        ("ingredients", "ingredient snapshot is empty"),
        ("recipes", "recipe snapshot is empty"),
    ],
)
def test_normalize_snapshot_rejects_empty_complete_dataset(field: str, message: str) -> None:
    payloads = {
        "categories": [category_payload()],
        "ingredients": [ingredient_payload()],
        "recipes": [recipe_payload()],
    }
    payloads[field] = []

    with pytest.raises(ValueError, match=message):
        _ = normalize_snapshot(**payloads)  # type: ignore[arg-type]
