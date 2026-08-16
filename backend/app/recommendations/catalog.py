import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    Ingredient,
    Produce,
    ProduceSeason,
    Recipe,
    RecipeIngredient,
)
from app.recipes.normalization import MEALDB_PROVIDER
from app.recipes.service import seasonal_ingredient_match
from app.recommendations.synthetic import RecipeFeature


async def load_recommendation_recipe_catalog(
    session: AsyncSession,
) -> list[RecipeFeature]:
    recipe_result = await session.execute(
        select(Recipe)
        .options(
            selectinload(Recipe.ingredients),
            selectinload(Recipe.allergen_assessments),
        )
        .where(
            Recipe.provider == MEALDB_PROVIDER,
            Recipe.is_active.is_(True),
        )
        .order_by(Recipe.id)
    )
    recipes = list(recipe_result.scalars().unique().all())

    seasonal_result = await session.execute(
        select(
            Recipe.id,
            ProduceSeason.country_code,
            ProduceSeason.month,
            func.count(func.distinct(Produce.id)),
        )
        .select_from(Recipe)
        .join(RecipeIngredient, RecipeIngredient.recipe_id == Recipe.id)
        .outerjoin(Ingredient, Ingredient.id == RecipeIngredient.ingredient_id)
        .join(Produce, seasonal_ingredient_match())
        .join(ProduceSeason, ProduceSeason.produce_id == Produce.id)
        .where(
            Recipe.provider == MEALDB_PROVIDER,
            Recipe.is_active.is_(True),
        )
        .group_by(
            Recipe.id,
            ProduceSeason.country_code,
            ProduceSeason.month,
        )
    )
    seasonal_counts: dict[uuid.UUID, dict[tuple[str, int], int]] = {}
    for recipe_id, country_code, month, matched_count in seasonal_result.tuples().all():
        seasonal_counts.setdefault(recipe_id, {})[(country_code, month)] = matched_count

    return [
        RecipeFeature(
            recipe_id=recipe.id,
            name=recipe.name,
            area=recipe.area,
            category=recipe.category_name_raw,
            ingredient_names=tuple(
                ingredient.ingredient_name_raw for ingredient in recipe.ingredients
            ),
            seasonal_match_counts=seasonal_counts.get(recipe.id, {}),
            allergen_statuses={
                assessment.allergen: assessment.status for assessment in recipe.allergen_assessments
            },
        )
        for recipe in recipes
        if seasonal_counts.get(recipe.id)
    ]
