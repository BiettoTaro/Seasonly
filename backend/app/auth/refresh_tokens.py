import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy import update as sqlalchemy_update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.models import User, UserRefreshToken

REFRESH_TOKEN_BYTES = 32


class RefreshTokenError(ValueError):
    pass


def generate_refresh_token() -> str:
    return secrets.token_urlsafe(REFRESH_TOKEN_BYTES)


def hash_refresh_token(refresh_token: str) -> str:
    return hashlib.sha256(refresh_token.encode("utf-8")).hexdigest()


async def create_refresh_token(
    session: AsyncSession,
    user: User,
    now: datetime | None = None,
) -> str:
    issued_at = now or datetime.now(UTC)
    refresh_token = generate_refresh_token()
    session.add(
        UserRefreshToken(
            user_id=user.id,
            token_hash=hash_refresh_token(refresh_token),
            created_at=issued_at,
            expires_at=issued_at + timedelta(days=settings.auth_refresh_token_expire_days),
        )
    )
    await session.commit()
    return refresh_token


async def rotate_refresh_token(
    session: AsyncSession,
    refresh_token: str,
    now: datetime | None = None,
) -> tuple[User, str]:
    current_time = now or datetime.now(UTC)
    token_record = await _get_valid_refresh_token_record(session, refresh_token, current_time)
    token_record.revoked_at = current_time

    new_refresh_token = generate_refresh_token()
    session.add(
        UserRefreshToken(
            user_id=token_record.user_id,
            token_hash=hash_refresh_token(new_refresh_token),
            created_at=current_time,
            expires_at=current_time + timedelta(days=settings.auth_refresh_token_expire_days),
        )
    )
    await session.commit()

    return token_record.user, new_refresh_token


async def revoke_refresh_token(
    session: AsyncSession,
    refresh_token: str,
    now: datetime | None = None,
) -> None:
    current_time = now or datetime.now(UTC)
    token_record = await _get_refresh_token_record(session, refresh_token)
    if token_record is None or token_record.revoked_at is not None:
        return

    token_record.revoked_at = current_time
    await session.commit()


async def revoke_user_refresh_tokens(
    session: AsyncSession,
    user: User,
    now: datetime | None = None,
) -> None:
    current_time = now or datetime.now(UTC)
    _ = await session.execute(
        sqlalchemy_update(UserRefreshToken)
        .where(UserRefreshToken.user_id == user.id)
        .where(UserRefreshToken.revoked_at.is_(None))
        .values(revoked_at=current_time)
    )


async def _get_valid_refresh_token_record(
    session: AsyncSession,
    refresh_token: str,
    now: datetime,
) -> UserRefreshToken:
    token_record = await _get_refresh_token_record(session, refresh_token)
    if token_record is None:
        raise RefreshTokenError("Refresh token is invalid")
    if token_record.revoked_at is not None:
        raise RefreshTokenError("Refresh token has been revoked")
    if token_record.expires_at < now:
        raise RefreshTokenError("Refresh token has expired")
    if not token_record.user.is_active:
        raise RefreshTokenError("User is inactive")

    return token_record


async def _get_refresh_token_record(
    session: AsyncSession,
    refresh_token: str,
) -> UserRefreshToken | None:
    result = await session.execute(
        select(UserRefreshToken)
        .options(selectinload(UserRefreshToken.user))
        .where(UserRefreshToken.token_hash == hash_refresh_token(refresh_token))
    )
    return result.scalar_one_or_none()
