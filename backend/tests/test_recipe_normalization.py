from datetime import datetime

import pytest

from app.recipes.normalization import (
    normalize_mealdb_category,
    normalize_mealdb_ingredient,
    normalize_mealdb_recipe,
    normalize_name,
)


def full_mealdb_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "idMeal": "52771",
        "strMeal": " Spicy Arrabiata Penne ",
        "strMealAlternate": None,
        "strCategory": "Vegetarian",
        "strArea": "Italian",
        "strCountry": "Italy",
        "strInstructions": " Cook the pasta. ",
        "strMealThumb": "https://example.com/meal.jpg",
        "strTags": "Pasta, Curry, pasta, ",
        "strYoutube": "",
        "strSource": "   ",
        "strImageSource": None,
        "strCreativeCommonsConfirmed": None,
        "dateModified": "2026-05-29 20:04:18",
        "strIngredient1": " penne rigate ",
        "strMeasure1": "1 pound",
        "strIngredient2": "garlic",
        "strMeasure2": " 3 cloves ",
    }
    payload.update(overrides)
    return payload


def test_normalize_mealdb_recipe_converts_missing_values_and_numbered_slots() -> None:
    payload = full_mealdb_payload()

    recipe = normalize_mealdb_recipe(payload)

    assert recipe["provider"] == "themealdb"
    assert recipe["provider_recipe_id"] == "52771"
    assert recipe["name"] == "Spicy Arrabiata Penne"
    assert recipe["alternate_name"] is None
    assert recipe["category_name_raw"] == "Vegetarian"
    assert recipe["area"] == "Italian"
    assert recipe["country_of_origin"] == "Italy"
    assert recipe["source_url"] is None
    assert recipe["youtube_url"] is None
    assert recipe["provider_modified_at"] == datetime(2026, 5, 29, 20, 4, 18)
    assert recipe["ingredients"] == [
        {
            "position": 1,
            "ingredient_name_raw": "penne rigate",
            "ingredient_name_normalized": "penne rigate",
            "measure_raw": "1 pound",
        },
        {
            "position": 2,
            "ingredient_name_raw": "garlic",
            "ingredient_name_normalized": "garlic",
            "measure_raw": "3 cloves",
        },
    ]
    assert recipe["tags"] == ["Pasta", "Curry"]
    assert recipe["raw_payload"] == payload


def test_normalize_mealdb_recipe_allows_missing_category_area_and_country() -> None:
    recipe = normalize_mealdb_recipe(
        full_mealdb_payload(
            strCategory=" ",
            strArea=None,
            strCountry="",
        )
    )

    assert recipe["category_name_raw"] is None
    assert recipe["area"] is None
    assert recipe["country_of_origin"] is None


def test_normalize_mealdb_recipe_accepts_ingredient_without_measure() -> None:
    recipe = normalize_mealdb_recipe(full_mealdb_payload(strMeasure2=None))

    assert recipe["ingredients"][1]["measure_raw"] is None


def test_normalize_mealdb_recipe_rejects_partial_filter_response() -> None:
    with pytest.raises(ValueError, match="strInstructions is required"):
        _ = normalize_mealdb_recipe(
            {
                "idMeal": "52771",
                "strMeal": "Spicy Arrabiata Penne",
                "strMealThumb": "https://example.com/meal.jpg",
                "strIngredient1": "penne",
            }
        )


def test_normalize_mealdb_recipe_rejects_measure_without_ingredient() -> None:
    with pytest.raises(ValueError, match="strMeasure3 has no matching ingredient"):
        _ = normalize_mealdb_recipe(full_mealdb_payload(strIngredient3=" ", strMeasure3="1 cup"))


def test_normalize_mealdb_recipe_rejects_invalid_timestamp() -> None:
    with pytest.raises(ValueError, match="dateModified must use"):
        _ = normalize_mealdb_recipe(full_mealdb_payload(dateModified="29 May 2026"))


def test_normalize_name_is_case_insensitive_and_collapses_whitespace() -> None:
    assert normalize_name("  Crème   FRAÎCHE ") == "crème fraîche"


def test_normalize_mealdb_category_and_ingredient_metadata() -> None:
    category = normalize_mealdb_category(
        {
            "idCategory": "14",
            "strCategory": " Vegan ",
            "strCategoryDescription": " ",
            "strCategoryThumb": None,
        }
    )
    ingredient = normalize_mealdb_ingredient(
        {
            "idIngredient": "1",
            "strIngredient": " Crème   FRAÎCHE ",
            "strDescription": None,
            "strThumb": " ",
            "strType": None,
        }
    )

    assert category["name"] == "Vegan"
    assert category["description"] is None
    assert ingredient["name"] == "Crème   FRAÎCHE"
    assert ingredient["normalized_name"] == "crème fraîche"
    assert ingredient["thumbnail_url"] is None
