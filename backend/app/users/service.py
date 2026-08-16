import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.session_revocation import revoke_user_refresh_tokens
from app.models import User, UserProfile
from app.schemas.user import UserCreate, UserProfileCreate, UserProfileUpdate, UserUpdate
from app.users.geolocation import CoarseLocation
from app.users.security import DUMMY_PASSWORD_HASH, hash_password, verify_password


class DuplicateUserEmailError(ValueError):
    pass


async def create_user(
    session: AsyncSession,
    payload: UserCreate,
    coarse_location: CoarseLocation | None = None,
) -> User:
    user = User(email=payload.email.lower(), password_hash=hash_password(payload.password))
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
    password_hash = user.password_hash if user is not None else DUMMY_PASSWORD_HASH
    password_matches = verify_password(password, password_hash)
    if user is None or not user.is_active or not password_matches:
        return None
    return user


async def get_user(session: AsyncSession, user_id: uuid.UUID) -> User | None:
    result = await session.execute(
        select(User)
        .options(
            selectinload(User.profile).selectinload(UserProfile.allergens),
            selectinload(User.profile).selectinload(UserProfile.dietary_rules),
            selectinload(User.profile).selectinload(UserProfile.cuisine_preferences),
        )
        .where(User.id == user_id)
    )
    return result.scalar_one_or_none()


async def get_user_by_email(session: AsyncSession, email: str) -> User | None:
    result = await session.execute(
        select(User)
        .options(
            selectinload(User.profile).selectinload(UserProfile.allergens),
            selectinload(User.profile).selectinload(UserProfile.dietary_rules),
            selectinload(User.profile).selectinload(UserProfile.cuisine_preferences),
        )
        .where(User.email == email.lower())
    )
    return result.scalar_one_or_none()


async def update_user(session: AsyncSession, user: User, payload: UserUpdate) -> User:
    if payload.email is not None:
        user.email = payload.email.lower()
    if payload.password is not None:
        user.password_hash = hash_password(payload.password)
        await revoke_user_refresh_tokens(session, user)
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
    profile = _get_or_create_profile(user)
    profile.country_code = coarse_location.country_code
    profile.region_code = coarse_location.region_code
    profile.location_source = coarse_location.source

    await session.commit()
    return await get_user(session, user.id) or user


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


def _get_or_create_profile(user: User) -> UserProfile:
    profile = user.profile
    if profile is None:
        profile = UserProfile()
        user.profile = profile
    return profile


def _apply_profile_update(user: User, payload: UserProfileUpdate) -> None:
    profile = _get_or_create_profile(user)

    if "display_name" in payload.model_fields_set:
        profile.display_name = payload.display_name
    if "country_code" in payload.model_fields_set:
        profile.country_code = payload.country_code
    if "region_code" in payload.model_fields_set:
        profile.region_code = payload.region_code
    if "location_source" in payload.model_fields_set:
        profile.location_source = payload.location_source
