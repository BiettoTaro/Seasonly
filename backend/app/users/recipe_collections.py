import uuid

from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Recipe, UserPlannedMeal, UserRecipeFavourite, UserRecipeHistory
from app.models.user_recipe import utc_now
from app.schemas.user_recipe import (
    FavouriteRecipeResponse,
    MealSlot,
    PlannedMealCreate,
    PlannedMealResponse,
    RecipeHistoryResponse,
    RecipeSummaryResponse,
    Weekday,
)


async def list_favourites(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
) -> list[FavouriteRecipeResponse]:
    result = await session.execute(
        select(UserRecipeFavourite, Recipe)
        .join(Recipe, Recipe.id == UserRecipeFavourite.recipe_id)
        .where(UserRecipeFavourite.user_id == user_id, Recipe.is_active.is_(True))
        .order_by(UserRecipeFavourite.created_at.desc())
    )
    return [
        FavouriteRecipeResponse(recipe=_recipe_summary(recipe), created_at=favourite.created_at)
        for favourite, recipe in result.tuples()
    ]


async def add_favourite(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    recipe_id: uuid.UUID,
) -> FavouriteRecipeResponse:
    recipe = await _get_active_recipe(session, recipe_id)
    favourite = await session.get(
        UserRecipeFavourite,
        {"user_id": user_id, "recipe_id": recipe_id},
    )
    if favourite is None:
        favourite = UserRecipeFavourite(user_id=user_id, recipe_id=recipe_id)
        session.add(favourite)
        await session.commit()
        await session.refresh(favourite)
    return FavouriteRecipeResponse(recipe=_recipe_summary(recipe), created_at=favourite.created_at)


async def remove_favourite(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    recipe_id: uuid.UUID,
) -> None:
    _ = await session.execute(
        delete(UserRecipeFavourite).where(
            UserRecipeFavourite.user_id == user_id,
            UserRecipeFavourite.recipe_id == recipe_id,
        )
    )
    await session.commit()


async def list_history(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    limit: int,
) -> list[RecipeHistoryResponse]:
    result = await session.execute(
        select(UserRecipeHistory, Recipe)
        .join(Recipe, Recipe.id == UserRecipeHistory.recipe_id)
        .where(UserRecipeHistory.user_id == user_id, Recipe.is_active.is_(True))
        .order_by(UserRecipeHistory.viewed_at.desc())
        .limit(limit)
    )
    return [
        RecipeHistoryResponse(recipe=_recipe_summary(recipe), viewed_at=history.viewed_at)
        for history, recipe in result.tuples()
    ]


async def record_history(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    recipe_id: uuid.UUID,
) -> RecipeHistoryResponse:
    recipe = await _get_active_recipe(session, recipe_id)
    history = await session.get(
        UserRecipeHistory,
        {"user_id": user_id, "recipe_id": recipe_id},
    )
    if history is None:
        history = UserRecipeHistory(user_id=user_id, recipe_id=recipe_id)
        session.add(history)
    else:
        history.viewed_at = utc_now()
    await session.commit()
    await session.refresh(history)
    return RecipeHistoryResponse(recipe=_recipe_summary(recipe), viewed_at=history.viewed_at)


async def clear_history(session: AsyncSession, *, user_id: uuid.UUID) -> None:
    _ = await session.execute(delete(UserRecipeHistory).where(UserRecipeHistory.user_id == user_id))
    await session.commit()


async def list_planned_meals(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
) -> list[PlannedMealResponse]:
    result = await session.execute(
        select(UserPlannedMeal, Recipe)
        .join(Recipe, Recipe.id == UserPlannedMeal.recipe_id)
        .where(UserPlannedMeal.user_id == user_id, Recipe.is_active.is_(True))
        .order_by(
            UserPlannedMeal.day_of_week,
            UserPlannedMeal.meal_slot,
            UserPlannedMeal.created_at,
        )
    )
    return [_planned_meal_response(meal, recipe) for meal, recipe in result.tuples()]


async def add_planned_meal(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    payload: PlannedMealCreate,
) -> PlannedMealResponse:
    recipe = await _get_active_recipe(session, payload.recipe_id)
    existing = await session.execute(
        select(UserPlannedMeal).where(
            UserPlannedMeal.user_id == user_id,
            UserPlannedMeal.recipe_id == payload.recipe_id,
            UserPlannedMeal.day_of_week == payload.day_of_week.value,
            UserPlannedMeal.meal_slot == payload.meal_slot.value,
        )
    )
    if meal := existing.scalar_one_or_none():
        return _planned_meal_response(meal, recipe)

    meal = UserPlannedMeal(
        user_id=user_id,
        recipe_id=payload.recipe_id,
        day_of_week=payload.day_of_week.value,
        meal_slot=payload.meal_slot.value,
    )
    session.add(meal)
    await session.commit()
    await session.refresh(meal)
    return _planned_meal_response(meal, recipe)


async def remove_planned_meal(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    planned_meal_id: uuid.UUID,
) -> None:
    meal = await session.get(UserPlannedMeal, planned_meal_id)
    if meal is None or meal.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Planned meal not found")
    await session.delete(meal)
    await session.commit()


async def _get_active_recipe(session: AsyncSession, recipe_id: uuid.UUID) -> Recipe:
    recipe = await session.get(Recipe, recipe_id)
    if recipe is None or not recipe.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recipe not found")
    return recipe


def _recipe_summary(recipe: Recipe) -> RecipeSummaryResponse:
    return RecipeSummaryResponse(
        id=recipe.id,
        name=recipe.name,
        category=recipe.category_name_raw,
        area=recipe.area,
        country_of_origin=recipe.country_of_origin,
        thumbnail_url=recipe.thumbnail_url,
    )


def _planned_meal_response(meal: UserPlannedMeal, recipe: Recipe) -> PlannedMealResponse:
    return PlannedMealResponse(
        id=meal.id,
        recipe=_recipe_summary(recipe),
        day_of_week=Weekday(meal.day_of_week),
        meal_slot=MealSlot(meal.meal_slot),
        created_at=meal.created_at,
    )
