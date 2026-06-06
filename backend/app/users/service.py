import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import User, UserProfile
from app.schemas.user import UserCreate, UserProfileCreate, UserProfileUpdate, UserUpdate
from app.users.geolocation import CoarseLocation
from app.users.security import hash_password, verify_password


class DuplicateUserEmailError(ValueError):
    pass


async def create_user(
    session: AsyncSession,
    payload: UserCreate,
    coarse_location: CoarseLocation | None = None,
) -> User:
    user = User(email=str(payload.email).lower(), password_hash=hash_password(payload.password))
    if payload.profile is not None or coarse_location is not None:
        user.profile = _build_profile(payload.profile, coarse_location)

    session.add(user)
    try:
        await session.commit()
    except IntegrityError as e:
        await session.rollback()
        raise DuplicateUserEmailError("A user with this email already exists") from e

    return await get_user(session, user.id) or user


async def authenticate_user(session: AsyncSession, email: str, password: str) -> User | None:
    user = await get_user_by_email(session, email)
    if user is None or not user.is_active:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


async def get_user(session: AsyncSession, user_id: uuid.UUID) -> User | None:
    result = await session.execute(
        select(User).options(selectinload(User.profile)).where(User.id == user_id)
    )
    return result.scalar_one_or_none()


async def get_user_by_email(session: AsyncSession, email: str) -> User | None:
    result = await session.execute(
        select(User).options(selectinload(User.profile)).where(User.email == email.lower())
    )
    return result.scalar_one_or_none()


async def update_user(session: AsyncSession, user: User, payload: UserUpdate) -> User:
    if payload.email is not None:
        user.email = str(payload.email).lower()
    if payload.password is not None:
        user.password_hash = hash_password(payload.password)
    if payload.profile is not None:
        _apply_profile_update(user, payload.profile)

    try:
        await session.commit()
    except IntegrityError as e:
        await session.rollback()
        raise DuplicateUserEmailError("A user with this email already exists") from e

    return await get_user(session, user.id) or user


async def apply_coarse_location(
    session: AsyncSession,
    user: User,
    coarse_location: CoarseLocation,
) -> User:
    if user.profile is None:
        user.profile = UserProfile()

    user.profile.country_code = coarse_location.country_code
    user.profile.region_code = coarse_location.region_code
    user.profile.location_source = coarse_location.source

    await session.commit()
    return await get_user(session, user.id) or user


async def delete_user(session: AsyncSession, user: User) -> None:
    await session.delete(user)
    await session.commit()


def _build_profile(
    payload: UserProfileCreate | None,
    coarse_location: CoarseLocation | None,
) -> UserProfile:
    return UserProfile(
        display_name=payload.display_name if payload is not None else None,
        country_code=(
            payload.country_code
            if payload is not None and payload.country_code is not None
            else coarse_location.country_code
            if coarse_location is not None
            else None
        ),
        region_code=(
            payload.region_code
            if payload is not None and payload.region_code is not None
            else coarse_location.region_code
            if coarse_location is not None
            else None
        ),
        location_source=(
            payload.location_source
            if payload is not None and payload.location_source is not None
            else coarse_location.source
            if coarse_location is not None
            else None
        ),
    )


def _apply_profile_update(user: User, payload: UserProfileUpdate) -> None:
    if user.profile is None:
        user.profile = UserProfile()

    if "display_name" in payload.model_fields_set:
        user.profile.display_name = payload.display_name
    if "country_code" in payload.model_fields_set:
        user.profile.country_code = payload.country_code
    if "region_code" in payload.model_fields_set:
        user.profile.region_code = payload.region_code
    if "location_source" in payload.model_fields_set:
        user.profile.location_source = payload.location_source
