from datetime import UTC, datetime

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User, UserRefreshToken


async def revoke_user_refresh_tokens(
    session: AsyncSession,
    user: User,
    now: datetime | None = None,
) -> None:
    current_time = now or datetime.now(UTC)
    _ = await session.execute(
        update(UserRefreshToken)
        .where(UserRefreshToken.user_id == user.id)
        .where(UserRefreshToken.revoked_at.is_(None))
        .values(revoked_at=current_time)
    )
