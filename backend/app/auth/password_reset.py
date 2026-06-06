import hashlib
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.refresh_tokens import revoke_user_refresh_tokens
from app.core.config import settings
from app.models import User, UserPasswordResetToken
from app.users.security import hash_password
from app.users.service import get_user_by_email

PASSWORD_RESET_TOKEN_BYTES = 32


class PasswordResetTokenError(ValueError):
    pass


@dataclass(frozen=True)
class PasswordResetTokenIssue:
    token: str
    user: User


def generate_password_reset_token() -> str:
    return secrets.token_urlsafe(PASSWORD_RESET_TOKEN_BYTES)


def hash_password_reset_token(reset_token: str) -> str:
    return hashlib.sha256(reset_token.encode("utf-8")).hexdigest()


async def request_password_reset(
    session: AsyncSession,
    email: str,
    now: datetime | None = None,
) -> PasswordResetTokenIssue | None:
    user = await get_user_by_email(session, email)
    if user is None or not user.is_active:
        return None

    issued_at = now or datetime.now(UTC)
    reset_token = generate_password_reset_token()
    session.add(
        UserPasswordResetToken(
            user_id=user.id,
            token_hash=hash_password_reset_token(reset_token),
            created_at=issued_at,
            expires_at=issued_at
            + timedelta(minutes=settings.auth_password_reset_token_expire_minutes),
        )
    )
    await session.commit()

    # TODO: Send this token through an email provider instead of exposing it.
    # TODO: Add a local/dev-only delivery sink so manual testing can inspect reset links safely.
    return PasswordResetTokenIssue(token=reset_token, user=user)


async def reset_password(
    session: AsyncSession,
    reset_token: str,
    new_password: str,
    now: datetime | None = None,
) -> User:
    current_time = now or datetime.now(UTC)
    token_record = await _get_valid_password_reset_token_record(
        session,
        reset_token,
        current_time,
    )

    token_record.used_at = current_time
    token_record.user.password_hash = hash_password(new_password)
    await revoke_user_refresh_tokens(session, token_record.user, current_time)
    await session.commit()

    return token_record.user


async def _get_valid_password_reset_token_record(
    session: AsyncSession,
    reset_token: str,
    now: datetime,
) -> UserPasswordResetToken:
    result = await session.execute(
        select(UserPasswordResetToken)
        .options(selectinload(UserPasswordResetToken.user))
        .where(UserPasswordResetToken.token_hash == hash_password_reset_token(reset_token))
    )
    token_record = result.scalar_one_or_none()
    if token_record is None:
        raise PasswordResetTokenError("Password reset token is invalid")
    if token_record.used_at is not None:
        raise PasswordResetTokenError("Password reset token has already been used")
    if token_record.expires_at < now:
        raise PasswordResetTokenError("Password reset token has expired")
    if not token_record.user.is_active:
        raise PasswordResetTokenError("User is inactive")

    return token_record
