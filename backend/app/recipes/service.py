import uuid
from collections import defaultdict
from dataclasses import dataclass
from typing import cast

from sqlalchemy import Select, and_, exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased
from sqlalchemy.sql.elements import ColumnElement

from app.data.enums import (
    Allergen,
    AllergenAssessmentStatus,
    CountryCode,
    DietaryRule,
    DietPattern,
    Month,
)
from app.models import (
    Ingredient,
    Produce,
    ProduceSeason,
    Recipe,
    RecipeAllergenAssessment,
    RecipeCategory,
    RecipeIngredient,
)
from app.recipes.dietary import diet_excluded_terms, dietary_patterns, dietary_rule_excluded_terms
from app.recipes.normalization import MEALDB_PROVIDER
from app.recommendations.ranking_types import RecipeContent
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


@dataclass(frozen=True)
class SeasonalRecipeCandidate:
    recipe: SeasonalRecipeResponse


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
    base_query = _seasonal_recipe_query().where(
        *_seasonal_recipe_filters(
            country_code=country_code,
            month=month,
            category=category,
            area=area,
            country_of_origin=country_of_origin,
            excluded_allergens=excluded_allergens,
            diet_pattern=diet_pattern,
            dietary_rules=dietary_rules,
        )
    )
    total_result = await session.execute(
        select(func.count()).select_from(
            base_query.with_only_columns(Recipe.id).distinct().subquery()
        )
    )
    total = total_result.scalar_one()
    candidates = await _load_seasonal_candidates(
        session,
        base_query=base_query,
        offset=(page - 1) * page_size,
        limit=page_size,
    )
    return SeasonalRecipeListResponse(
        country_code=country_code,
        month=month,
        page=page,
        page_size=page_size,
        total=total,
        items=[candidate.recipe for candidate in candidates],
    )


async def load_eligible_seasonal_recipe_candidates(
    session: AsyncSession,
    *,
    country_code: CountryCode,
    month: Month,
    excluded_allergens: set[Allergen] | None = None,
    diet_pattern: DietPattern | None = None,
    dietary_rules: set[DietaryRule] | None = None,
) -> list[SeasonalRecipeCandidate]:
    base_query = _seasonal_recipe_query().where(
        *_seasonal_recipe_filters(
            country_code=country_code,
            month=month,
            category=None,
            area=None,
            country_of_origin=None,
            excluded_allergens=excluded_allergens,
            diet_pattern=diet_pattern,
            dietary_rules=dietary_rules,
        )
    )
    return await _load_seasonal_candidates(
        session,
        base_query=base_query,
        offset=None,
        limit=None,
    )


async def load_active_recipe_content(
    session: AsyncSession,
) -> list[RecipeContent]:
    result = await session.execute(
        select(
            Recipe.id,
            Recipe.name,
            Recipe.area,
            Recipe.category_name_raw,
            RecipeIngredient.ingredient_name_raw,
        )
        .join(RecipeIngredient, RecipeIngredient.recipe_id == Recipe.id)
        .where(
            Recipe.is_active.is_(True),
            Recipe.provider == MEALDB_PROVIDER,
        )
        .order_by(Recipe.id, RecipeIngredient.position)
    )
    metadata: dict[uuid.UUID, tuple[str, str, str]] = {}
    ingredients_by_recipe: defaultdict[uuid.UUID, list[str]] = defaultdict(list)
    for recipe_id, name, area, category, ingredient_name in result.tuples().all():
        metadata[recipe_id] = (
            name,
            area or "unknown",
            category or "unknown",
        )
        ingredients_by_recipe[recipe_id].append(ingredient_name)
    if not metadata:
        raise ValueError("No active recipe content is available for recommendation ranking")
    return [
        RecipeContent(
            recipe_id=recipe_id,
            name=name,
            area=area,
            category=category,
            ingredient_names=tuple(ingredients_by_recipe[recipe_id]),
        )
        for recipe_id, (name, area, category) in metadata.items()
    ]


async def _load_seasonal_candidates(
    session: AsyncSession,
    *,
    base_query: Select[tuple[Recipe]],
    offset: int | None,
    limit: int | None,
) -> list[SeasonalRecipeCandidate]:
    matched_produce = func.array_agg(func.distinct(Produce.name)).label("matched_produce")
    matched_count = func.count(func.distinct(Produce.id)).label("matched_count")
    statement = (
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
    )
    if offset is not None:
        statement = statement.offset(offset)
    if limit is not None:
        statement = statement.limit(limit)
    result = await session.execute(statement)
    recipe_rows = cast(list[SeasonalRecipeRow], result.tuples().all())
    if not recipe_rows:
        return []

    candidates: list[SeasonalRecipeCandidate] = []
    for row in recipe_rows:
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
        ) = row
        candidates.append(
            SeasonalRecipeCandidate(
                recipe=SeasonalRecipeResponse(
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
        )
    return candidates


def _seasonal_recipe_filters(
    *,
    country_code: CountryCode,
    month: Month,
    category: str | None,
    area: str | None,
    country_of_origin: str | None,
    excluded_allergens: set[Allergen] | None,
    diet_pattern: DietPattern | None,
    dietary_rules: set[DietaryRule] | None,
) -> list[ColumnElement[bool]]:
    filters: list[ColumnElement[bool]] = [
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
        filters.append(recipe_is_verified_safe(excluded_allergens))
    excluded_dietary_terms = _excluded_dietary_terms(diet_pattern, dietary_rules)
    if excluded_dietary_terms:
        filters.append(~_recipe_contains_terms(excluded_dietary_terms))
    return filters


def _seasonal_recipe_query() -> Select[tuple[Recipe]]:
    return (
        select(Recipe)
        .join(RecipeIngredient, RecipeIngredient.recipe_id == Recipe.id)
        .outerjoin(Ingredient, Ingredient.id == RecipeIngredient.ingredient_id)
        .join(Produce, seasonal_ingredient_match())
        .join(ProduceSeason, ProduceSeason.produce_id == Produce.id)
        .outerjoin(RecipeCategory, RecipeCategory.id == Recipe.category_id)
    )


def seasonal_ingredient_match() -> ColumnElement[bool]:
    produce_name = _normalized_text(Produce.name)
    mealdb_name = _normalized_text(Produce.mealdb_name)
    raw_ingredient_name = _normalized_text(RecipeIngredient.ingredient_name_raw)

    return or_(
        and_(Ingredient.provider == MEALDB_PROVIDER, Ingredient.normalized_name == mealdb_name),
        and_(Ingredient.provider == MEALDB_PROVIDER, Ingredient.normalized_name == produce_name),
        raw_ingredient_name == mealdb_name,
        raw_ingredient_name == produce_name,
    )


def recipe_is_verified_safe(allergens: set[Allergen]) -> ColumnElement[bool]:
    verified_assessments: list[ColumnElement[bool]] = []
    for allergen in allergens:
        assessment = aliased(RecipeAllergenAssessment)
        verified_assessments.append(
            exists(
                select(1).where(
                    assessment.recipe_id == Recipe.id,
                    assessment.allergen == allergen.value,
                    assessment.status == AllergenAssessmentStatus.DOES_NOT_CONTAIN.value,
                )
            )
        )
    return and_(*verified_assessments)


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
