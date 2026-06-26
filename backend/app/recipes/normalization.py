from datetime import datetime
from typing import TypedDict

MEALDB_PROVIDER = "themealdb"
MEALDB_INGREDIENT_SLOTS = range(1, 21)


class NormalizedRecipeIngredient(TypedDict):
    position: int
    ingredient_name_raw: str
    ingredient_name_normalized: str
    measure_raw: str | None


class NormalizedCategory(TypedDict):
    provider: str
    provider_category_id: str
    name: str
    description: str | None
    thumbnail_url: str | None
    raw_payload: dict[str, object]


class NormalizedIngredient(TypedDict):
    provider: str
    provider_ingredient_id: str
    name: str
    normalized_name: str
    description: str | None
    thumbnail_url: str | None
    type: str | None
    raw_payload: dict[str, object]


class NormalizedRecipe(TypedDict):
    provider: str
    provider_recipe_id: str
    name: str
    alternate_name: str | None
    category_name_raw: str | None
    area: str | None
    country_of_origin: str | None
    instructions: str
    thumbnail_url: str | None
    source_url: str | None
    youtube_url: str | None
    image_source_url: str | None
    creative_commons_confirmed: str | None
    provider_modified_at: datetime | None
    ingredients: list[NormalizedRecipeIngredient]
    tags: list[str]
    raw_payload: dict[str, object]


def normalize_mealdb_category(payload: dict[str, object]) -> NormalizedCategory:
    return NormalizedCategory(
        provider=MEALDB_PROVIDER,
        provider_category_id=normalize_required_text(
            payload.get("idCategory"),
            field="idCategory",
        ),
        name=normalize_required_text(payload.get("strCategory"), field="strCategory"),
        description=normalize_optional_text(
            payload.get("strCategoryDescription"),
            field="strCategoryDescription",
        ),
        thumbnail_url=normalize_optional_text(
            payload.get("strCategoryThumb"),
            field="strCategoryThumb",
        ),
        raw_payload=dict(payload),
    )


def normalize_mealdb_ingredient(payload: dict[str, object]) -> NormalizedIngredient:
    name = normalize_required_text(payload.get("strIngredient"), field="strIngredient")
    return NormalizedIngredient(
        provider=MEALDB_PROVIDER,
        provider_ingredient_id=normalize_required_text(
            payload.get("idIngredient"),
            field="idIngredient",
        ),
        name=name,
        normalized_name=normalize_name(name),
        description=normalize_optional_text(
            payload.get("strDescription"),
            field="strDescription",
        ),
        thumbnail_url=normalize_optional_text(payload.get("strThumb"), field="strThumb"),
        type=normalize_optional_text(payload.get("strType"), field="strType"),
        raw_payload=dict(payload),
    )


def normalize_optional_text(value: object, *, field: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string or null")
    return value.strip() or None


def normalize_required_text(value: object, *, field: str) -> str:
    normalized = normalize_optional_text(value, field=field)
    if normalized is None:
        raise ValueError(f"{field} is required")
    return normalized


def normalize_name(value: str) -> str:
    return " ".join(value.casefold().split())


def normalize_mealdb_recipe(payload: dict[str, object]) -> NormalizedRecipe:
    ingredients = _normalize_ingredients(payload)
    if not ingredients:
        raise ValueError("MealDB recipe must contain at least one ingredient")

    return NormalizedRecipe(
        provider=MEALDB_PROVIDER,
        provider_recipe_id=normalize_required_text(payload.get("idMeal"), field="idMeal"),
        name=normalize_required_text(payload.get("strMeal"), field="strMeal"),
        alternate_name=normalize_optional_text(
            payload.get("strMealAlternate"),
            field="strMealAlternate",
        ),
        category_name_raw=normalize_optional_text(
            payload.get("strCategory"),
            field="strCategory",
        ),
        area=normalize_optional_text(payload.get("strArea"), field="strArea"),
        country_of_origin=normalize_optional_text(payload.get("strCountry"), field="strCountry"),
        instructions=normalize_required_text(
            payload.get("strInstructions"),
            field="strInstructions",
        ),
        thumbnail_url=normalize_optional_text(
            payload.get("strMealThumb"),
            field="strMealThumb",
        ),
        source_url=normalize_optional_text(payload.get("strSource"), field="strSource"),
        youtube_url=normalize_optional_text(payload.get("strYoutube"), field="strYoutube"),
        image_source_url=normalize_optional_text(
            payload.get("strImageSource"),
            field="strImageSource",
        ),
        creative_commons_confirmed=normalize_optional_text(
            payload.get("strCreativeCommonsConfirmed"),
            field="strCreativeCommonsConfirmed",
        ),
        provider_modified_at=_normalize_provider_modified_at(payload.get("dateModified")),
        ingredients=ingredients,
        tags=_normalize_tags(payload.get("strTags")),
        raw_payload=dict(payload),
    )


def _normalize_ingredients(payload: dict[str, object]) -> list[NormalizedRecipeIngredient]:
    ingredients: list[NormalizedRecipeIngredient] = []
    for position in MEALDB_INGREDIENT_SLOTS:
        ingredient = normalize_optional_text(
            payload.get(f"strIngredient{position}"),
            field=f"strIngredient{position}",
        )
        measure = normalize_optional_text(
            payload.get(f"strMeasure{position}"),
            field=f"strMeasure{position}",
        )
        if ingredient is None:
            if measure is not None:
                raise ValueError(f"strMeasure{position} has no matching ingredient")
            continue
        ingredients.append(
            NormalizedRecipeIngredient(
                position=position,
                ingredient_name_raw=ingredient,
                ingredient_name_normalized=normalize_name(ingredient),
                measure_raw=measure,
            )
        )
    return ingredients


def _normalize_tags(value: object) -> list[str]:
    tag_string = normalize_optional_text(value, field="strTags")
    if tag_string is None:
        return []

    tags_by_normalized_name: dict[str, str] = {}
    for raw_tag in tag_string.split(","):
        tag = raw_tag.strip()
        if tag:
            _ = tags_by_normalized_name.setdefault(normalize_name(tag), tag)
    return list(tags_by_normalized_name.values())


def _normalize_provider_modified_at(value: object) -> datetime | None:
    timestamp = normalize_optional_text(value, field="dateModified")
    if timestamp is None:
        return None
    try:
        return datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
    except ValueError as error:
        raise ValueError("dateModified must use YYYY-MM-DD HH:MM:SS") from error
