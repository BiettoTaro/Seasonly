import uuid
from typing import cast

from sqlalchemy import Select, and_, exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased
from sqlalchemy.sql.elements import ColumnElement

from app.data.enums import Allergen, CountryCode, DietaryRule, DietPattern, Month
from app.models import Ingredient, Produce, ProduceSeason, Recipe, RecipeCategory, RecipeIngredient
from app.recipes.allergens import allergen_patterns, allergen_terms
from app.recipes.dietary import diet_excluded_terms, dietary_patterns, dietary_rule_excluded_terms
from app.recipes.normalization import MEALDB_PROVIDER
from app.schemas.recipe import SeasonalRecipeListResponse, SeasonalRecipeResponse

type SeasonalRecipeRow = tuple[
    uuid.UUID,
    str,
    str | None,
    str | None,
    str | None,
    str | None,
    str,
    list[str],
    int,
]


async def list_seasonal_recipes(
    session: AsyncSession,
    *,
    country_code: CountryCode,
    month: Month,
    page: int,
    page_size: int,
    category: str | None = None,
    area: str | None = None,
    country_of_origin: str | None = None,
    excluded_allergens: set[Allergen] | None = None,
    diet_pattern: DietPattern | None = None,
    dietary_rules: set[DietaryRule] | None = None,
) -> SeasonalRecipeListResponse:
    filters = [
        Recipe.is_active.is_(True),
        Recipe.provider == MEALDB_PROVIDER,
        ProduceSeason.country_code == country_code.value,
        ProduceSeason.month == month.value,
    ]
    if category is not None:
        filters.append(func.lower(RecipeCategory.name) == category.casefold())
    if area is not None:
        filters.append(func.lower(Recipe.area) == area.casefold())
    if country_of_origin is not None:
        filters.append(func.lower(Recipe.country_of_origin) == country_of_origin.casefold())
    if excluded_allergens:
        filters.append(~_recipe_contains_allergen(excluded_allergens))
    excluded_dietary_terms = _excluded_dietary_terms(diet_pattern, dietary_rules)
    if excluded_dietary_terms:
        filters.append(~_recipe_contains_terms(excluded_dietary_terms))

    base_query = _seasonal_recipe_query().where(*filters)
    total_result = await session.execute(
        select(func.count()).select_from(
            base_query.with_only_columns(Recipe.id).distinct().subquery()
        )
    )
    total = total_result.scalar_one()

    matched_produce = func.array_agg(func.distinct(Produce.name)).label("matched_produce")
    matched_count = func.count(func.distinct(Produce.id)).label("matched_count")
    result = await session.execute(
        base_query.with_only_columns(
            Recipe.id,
            Recipe.name,
            Recipe.category_name_raw,
            Recipe.area,
            Recipe.country_of_origin,
            Recipe.thumbnail_url,
            Recipe.instructions,
            matched_produce,
            matched_count,
        )
        .group_by(
            Recipe.id,
            Recipe.name,
            Recipe.category_name_raw,
            Recipe.area,
            Recipe.country_of_origin,
            Recipe.thumbnail_url,
            Recipe.instructions,
        )
        .order_by(matched_count.desc(), Recipe.name)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items: list[SeasonalRecipeResponse] = []
    for row in result.all():
        (
            recipe_id,
            name,
            category_name,
            recipe_area,
            recipe_country_of_origin,
            thumbnail_url,
            instructions,
            produce_names,
            produce_count,
        ) = cast(SeasonalRecipeRow, row.tuple())
        items.append(
            SeasonalRecipeResponse(
                id=recipe_id,
                name=name,
                category=category_name,
                area=recipe_area,
                country_of_origin=recipe_country_of_origin,
                thumbnail_url=thumbnail_url,
                instructions=instructions,
                matched_seasonal_produce=sorted(produce_names),
                matched_seasonal_produce_count=produce_count,
            )
        )
    return SeasonalRecipeListResponse(
        country_code=country_code,
        month=month,
        page=page,
        page_size=page_size,
        total=total,
        items=items,
    )


def _seasonal_recipe_query() -> Select[tuple[Recipe]]:
    return (
        select(Recipe)
        .join(RecipeIngredient, RecipeIngredient.recipe_id == Recipe.id)
        .outerjoin(Ingredient, Ingredient.id == RecipeIngredient.ingredient_id)
        .join(Produce, _seasonal_ingredient_match())
        .join(ProduceSeason, ProduceSeason.produce_id == Produce.id)
        .outerjoin(RecipeCategory, RecipeCategory.id == Recipe.category_id)
    )


def _seasonal_ingredient_match() -> ColumnElement[bool]:
    produce_name = _normalized_text(Produce.name)
    mealdb_name = _normalized_text(Produce.mealdb_name)
    raw_ingredient_name = _normalized_text(RecipeIngredient.ingredient_name_raw)

    return or_(
        and_(Ingredient.provider == MEALDB_PROVIDER, Ingredient.normalized_name == mealdb_name),
        and_(Ingredient.provider == MEALDB_PROVIDER, Ingredient.normalized_name == produce_name),
        raw_ingredient_name == mealdb_name,
        raw_ingredient_name == produce_name,
    )


def _recipe_contains_allergen(allergens: set[Allergen]) -> ColumnElement[bool]:
    return _recipe_contains_terms(allergen_terms(allergens), allergen_patterns(allergens))


def _recipe_contains_terms(
    terms: set[str],
    patterns: list[str] | None = None,
) -> ColumnElement[bool]:
    recipe_ingredient = aliased(RecipeIngredient)
    ingredient = aliased(Ingredient)
    ingredient_name = _normalized_text(ingredient.normalized_name)
    raw_ingredient_name = _normalized_text(recipe_ingredient.ingredient_name_raw)

    matchers: list[ColumnElement[bool]] = []
    if terms:
        matchers.append(ingredient_name.in_(terms))
    for pattern in patterns if patterns is not None else dietary_patterns(terms):
        matchers.append(raw_ingredient_name.op("~")(pattern))
        matchers.append(ingredient_name.op("~")(pattern))

    return exists(
        select(1)
        .select_from(recipe_ingredient)
        .outerjoin(ingredient, ingredient.id == recipe_ingredient.ingredient_id)
        .where(
            recipe_ingredient.recipe_id == Recipe.id,
            or_(*matchers),
        )
    )


def _excluded_dietary_terms(
    diet_pattern: DietPattern | None,
    dietary_rules: set[DietaryRule] | None,
) -> set[str]:
    return diet_excluded_terms(diet_pattern) | dietary_rule_excluded_terms(dietary_rules or set())


def _normalized_text(value: object) -> ColumnElement[str]:
    return cast(ColumnElement[str], func.lower(func.trim(value)))
