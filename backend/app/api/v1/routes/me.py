import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.session import get_db_session
from app.models import User
from app.schemas.user_recipe import (
    FavouriteRecipeResponse,
    PlannedMealCreate,
    PlannedMealResponse,
    RecipeHistoryResponse,
)
from app.users.recipe_collections import (
    add_favourite,
    add_planned_meal,
    clear_history,
    list_favourites,
    list_history,
    list_planned_meals,
    record_history,
    remove_favourite,
    remove_planned_meal,
)

router = APIRouter(prefix="/me")


@router.get("/favourites", response_model=list[FavouriteRecipeResponse])
async def read_favourites(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[FavouriteRecipeResponse]:
    return await list_favourites(session, user_id=current_user.id)


@router.put("/favourites/{recipe_id}", response_model=FavouriteRecipeResponse)
async def save_favourite(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_user)],
    recipe_id: uuid.UUID,
) -> FavouriteRecipeResponse:
    return await add_favourite(session, user_id=current_user.id, recipe_id=recipe_id)


@router.delete("/favourites/{recipe_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_favourite(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_user)],
    recipe_id: uuid.UUID,
) -> Response:
    await remove_favourite(session, user_id=current_user.id, recipe_id=recipe_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/history/recipes", response_model=list[RecipeHistoryResponse])
async def read_recipe_history(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_user)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[RecipeHistoryResponse]:
    return await list_history(session, user_id=current_user.id, limit=limit)


@router.put("/history/recipes/{recipe_id}", response_model=RecipeHistoryResponse)
async def save_recipe_history(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_user)],
    recipe_id: uuid.UUID,
) -> RecipeHistoryResponse:
    return await record_history(session, user_id=current_user.id, recipe_id=recipe_id)


@router.delete("/history/recipes", status_code=status.HTTP_204_NO_CONTENT)
async def delete_recipe_history(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Response:
    await clear_history(session, user_id=current_user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/planner", response_model=list[PlannedMealResponse])
async def read_planner(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[PlannedMealResponse]:
    return await list_planned_meals(session, user_id=current_user.id)


@router.post(
    "/planner",
    response_model=PlannedMealResponse,
    status_code=status.HTTP_201_CREATED,
)
async def save_planned_meal(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_user)],
    payload: PlannedMealCreate,
) -> PlannedMealResponse:
    return await add_planned_meal(session, user_id=current_user.id, payload=payload)


@router.delete("/planner/{planned_meal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_planned_meal(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_user)],
    planned_meal_id: uuid.UUID,
) -> Response:
    await remove_planned_meal(session, user_id=current_user.id, planned_meal_id=planned_meal_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
