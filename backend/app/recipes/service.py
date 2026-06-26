from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.data.enums import CountryCode, Month
from app.models import Ingredient, Produce, ProduceSeason, Recipe, RecipeCategory, RecipeIngredient
from app.recipes.normalization import MEALDB_PROVIDER
from app.schemas.recipe import SeasonalRecipeListResponse, SeasonalRecipeResponse


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
) -> SeasonalRecipeListResponse:
    filters = [
        Recipe.is_active.is_(True),
        Ingredient.provider == MEALDB_PROVIDER,
        Produce.mealdb_name.is_not(None),
        func.lower(Produce.mealdb_name) == Ingredient.normalized_name,
        ProduceSeason.country_code == country_code.value,
        ProduceSeason.month == month.value,
    ]
    if category is not None:
        filters.append(func.lower(RecipeCategory.name) == category.casefold())
    if area is not None:
        filters.append(func.lower(Recipe.area) == area.casefold())
    if country_of_origin is not None:
        filters.append(func.lower(Recipe.country_of_origin) == country_of_origin.casefold())

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
        )
        .order_by(matched_count.desc(), Recipe.name)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = [
        SeasonalRecipeResponse(
            id=recipe_id,
            name=name,
            category=category_name,
            area=recipe_area,
            country_of_origin=recipe_country_of_origin,
            thumbnail_url=thumbnail_url,
            matched_seasonal_produce=sorted(produce_names),
            matched_seasonal_produce_count=produce_count,
        )
        for (
            recipe_id,
            name,
            category_name,
            recipe_area,
            recipe_country_of_origin,
            thumbnail_url,
            produce_names,
            produce_count,
        ) in (row.tuple() for row in result.all())
    ]
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
        .join(Ingredient, Ingredient.id == RecipeIngredient.ingredient_id)
        .join(Produce, func.lower(Produce.mealdb_name) == Ingredient.normalized_name)
        .join(ProduceSeason, ProduceSeason.produce_id == Produce.id)
        .outerjoin(RecipeCategory, RecipeCategory.id == Recipe.category_id)
    )
