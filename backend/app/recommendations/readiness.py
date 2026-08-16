from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.data.enums import Allergen, CountryCode
from app.models import (
    Ingredient,
    Produce,
    ProduceSeason,
    Recipe,
    RecipeAllergenAssessment,
    RecipeIngredient,
)
from app.recipes.normalization import MEALDB_PROVIDER
from app.recipes.service import seasonal_ingredient_match


async def build_recommendation_readiness_report(
    session: AsyncSession,
) -> dict[str, object]:
    active_recipe_count = await _active_recipe_count(session)
    produce_count, mapped_produce_count = await _produce_mapping_counts(session)
    seasonally_matchable_recipe_count = await _seasonally_matchable_recipe_count(session)
    country_coverage = await _country_coverage(session)
    allergen_coverage = await _allergen_coverage(session, active_recipe_count)

    return {
        "recipes": {
            "active": active_recipe_count,
            "seasonally_matchable": seasonally_matchable_recipe_count,
        },
        "produce_mapping": {
            "total": produce_count,
            "mapped_to_themealdb_ingredient": mapped_produce_count,
        },
        "country_coverage": country_coverage,
        "allergen_assessments": allergen_coverage,
    }


async def _active_recipe_count(session: AsyncSession) -> int:
    result = await session.execute(
        select(func.count(Recipe.id)).where(
            Recipe.provider == MEALDB_PROVIDER,
            Recipe.is_active.is_(True),
        )
    )
    return result.scalar_one()


async def _produce_mapping_counts(session: AsyncSession) -> tuple[int, int]:
    total_result = await session.execute(select(func.count(Produce.id)))
    mapped_result = await session.execute(
        select(func.count(func.distinct(Produce.id)))
        .select_from(Produce)
        .join(Ingredient, _produce_matches_ingredient())
        .where(Ingredient.provider == MEALDB_PROVIDER)
    )
    return total_result.scalar_one(), mapped_result.scalar_one()


def _produce_matches_ingredient() -> ColumnElement[bool]:
    ingredient_name = func.lower(func.trim(Ingredient.normalized_name))
    produce_name = func.lower(func.trim(Produce.name))
    mealdb_name = func.lower(func.trim(Produce.mealdb_name))
    return or_(ingredient_name == mealdb_name, ingredient_name == produce_name)


async def _seasonally_matchable_recipe_count(session: AsyncSession) -> int:
    result = await session.execute(
        select(func.count(func.distinct(Recipe.id)))
        .select_from(Recipe)
        .join(RecipeIngredient, RecipeIngredient.recipe_id == Recipe.id)
        .outerjoin(Ingredient, Ingredient.id == RecipeIngredient.ingredient_id)
        .join(Produce, seasonal_ingredient_match())
        .where(
            Recipe.provider == MEALDB_PROVIDER,
            Recipe.is_active.is_(True),
        )
    )
    return result.scalar_one()


async def _country_coverage(session: AsyncSession) -> list[dict[str, object]]:
    result = await session.execute(
        select(
            ProduceSeason.country_code,
            func.count(func.distinct(ProduceSeason.month)),
            func.count(func.distinct(ProduceSeason.produce_id)),
        )
        .group_by(ProduceSeason.country_code)
        .order_by(ProduceSeason.country_code)
    )
    rows = {
        country_code: (month_count, produce_count)
        for country_code, month_count, produce_count in result.tuples().all()
    }
    return [
        {
            "country_code": country.value,
            "country_name": country.name.replace("_", " ").title(),
            "seasonal_data_available": country.value in rows,
            "months": rows.get(country.value, (0, 0))[0],
            "produce": rows.get(country.value, (0, 0))[1],
        }
        for country in CountryCode
    ]


async def _allergen_coverage(
    session: AsyncSession,
    active_recipe_count: int,
) -> dict[str, object]:
    result = await session.execute(
        select(
            RecipeAllergenAssessment.status,
            RecipeAllergenAssessment.method,
            func.count(),
        )
        .join(Recipe, Recipe.id == RecipeAllergenAssessment.recipe_id)
        .where(
            Recipe.provider == MEALDB_PROVIDER,
            Recipe.is_active.is_(True),
        )
        .group_by(
            RecipeAllergenAssessment.status,
            RecipeAllergenAssessment.method,
        )
        .order_by(
            RecipeAllergenAssessment.status,
            RecipeAllergenAssessment.method,
        )
    )
    assessment_rows = result.tuples().all()
    grouped_counts = [
        {
            "status": status,
            "method": method,
            "count": count,
        }
        for status, method, count in assessment_rows
    ]
    stored_assessments = sum(count for _, _, count in assessment_rows)
    expected_assessments = active_recipe_count * len(Allergen)
    return {
        "expected": expected_assessments,
        "stored": stored_assessments,
        "missing": max(expected_assessments - stored_assessments, 0),
        "by_status_and_method": grouped_counts,
    }
