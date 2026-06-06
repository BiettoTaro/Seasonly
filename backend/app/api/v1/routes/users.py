import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.session import get_db_session
from app.models import User
from app.schemas.user import UserCreate, UserResponse, UserUpdate
from app.users.geolocation import infer_coarse_location
from app.users.service import (
    DuplicateUserEmailError,
    apply_coarse_location,
    create_user,
    delete_user,
    get_user,
    update_user,
)

router = APIRouter(prefix="/users")


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    request: Request,
    payload: UserCreate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> User:
    try:
        return await create_user(session, payload, infer_coarse_location(request))
    except DuplicateUserEmailError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e


@router.get("/me", response_model=UserResponse)
async def read_current_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    return current_user


@router.get("/{user_id}", response_model=UserResponse)
async def read_user(
    user_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    _require_same_user(user_id, current_user)
    user = await get_user(session, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.patch("/me", response_model=UserResponse)
async def update_current_user(
    payload: UserUpdate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    return await _update_user(session, current_user, payload)


@router.post("/me/location/coarse", response_model=UserResponse)
async def refresh_current_user_coarse_location(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    coarse_location = infer_coarse_location(request)
    if coarse_location is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No supported coarse location header was provided",
        )

    return await apply_coarse_location(session, current_user, coarse_location)


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user_by_id(
    user_id: uuid.UUID,
    payload: UserUpdate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    _require_same_user(user_id, current_user)
    return await _update_user(session, current_user, payload)


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_current_user(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Response:
    await delete_user(session, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_by_id(
    user_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Response:
    _require_same_user(user_id, current_user)
    await delete_user(session, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


async def _update_user(session: AsyncSession, user: User, payload: UserUpdate) -> User:
    try:
        return await update_user(session, user, payload)
    except DuplicateUserEmailError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e


def _require_same_user(user_id: uuid.UUID, current_user: User) -> None:
    if user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot access another user",
        )
