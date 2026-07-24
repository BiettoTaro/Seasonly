import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select, update
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
    _ = await session.execute(
        delete(UserRefreshToken)
        .where(UserRefreshToken.user_id == user.id)
        .where(UserRefreshToken.expires_at <= issued_at)
    )
    refresh_token = generate_refresh_token()
    family_id = uuid.uuid4()
    session.add(
        UserRefreshToken(
            user_id=user.id,
            family_id=family_id,
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
    token_record = await _get_refresh_token_record(session, refresh_token, for_update=True)
    if token_record is None:
        raise RefreshTokenError("Refresh token is invalid")
    if token_record.revoked_at is not None:
        _ = await session.execute(
            update(UserRefreshToken)
            .where(UserRefreshToken.family_id == token_record.family_id)
            .where(UserRefreshToken.revoked_at.is_(None))
            .values(revoked_at=current_time)
        )
        await session.commit()
        raise RefreshTokenError("Refresh token reuse was detected")
    _validate_refresh_token_record(token_record, current_time)
    token_record.revoked_at = current_time

    new_refresh_token = generate_refresh_token()
    session.add(
        UserRefreshToken(
            user_id=token_record.user_id,
            family_id=token_record.family_id,
            parent_token_id=token_record.id,
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


def _validate_refresh_token_record(token_record: UserRefreshToken, now: datetime) -> None:
    if token_record.expires_at <= now:
        raise RefreshTokenError("Refresh token has expired")
    if not token_record.user.is_active:
        raise RefreshTokenError("User is inactive")


async def _get_refresh_token_record(
    session: AsyncSession,
    refresh_token: str,
    *,
    for_update: bool = False,
) -> UserRefreshToken | None:
    statement = (
        select(UserRefreshToken)
        .options(selectinload(UserRefreshToken.user))
        .where(UserRefreshToken.token_hash == hash_refresh_token(refresh_token))
    )
    if for_update:
        statement = statement.with_for_update(of=UserRefreshToken)
    result = await session.execute(statement)
    return result.scalar_one_or_none()
