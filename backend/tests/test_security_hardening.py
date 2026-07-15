import uuid
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.auth.rate_limit import SlidingWindowRateLimiter
from app.core.config import Settings
from app.models import User
from app.schemas.user import UserUpdate
from app.users import service as user_service
from app.users.security import DUMMY_PASSWORD_HASH


def test_production_settings_reject_insecure_defaults() -> None:
    with pytest.raises(ValidationError, match="APP_FORCE_HTTPS"):
        _ = Settings(
            app_env="production",
            app_debug=False,
            app_force_https=False,
            auth_secret_key="short",
        )


def test_production_settings_accept_explicit_secure_configuration() -> None:
    configured = Settings(
        app_env="production",
        app_debug=False,
        app_force_https=True,
        app_trusted_hosts=["api.seasonly.example"],
        database_url="postgresql+asyncpg://seasonly:unique-password@db:5432/seasonly",
        auth_secret_key="a-unique-production-secret-that-is-long-enough",
        recipes_base_url="https://www.themealdb.com/api/json/v2/",
        smtp_host="smtp.seasonly.example",
        smtp_from_email="no-reply@seasonly.example",
    )

    assert configured.app_env == "production"


@pytest.mark.asyncio
async def test_rate_limiter_rejects_requests_inside_window() -> None:
    limiter = SlidingWindowRateLimiter(requests=2, window_seconds=10)

    await limiter.check("client", now=0)
    await limiter.check("client", now=1)
    with pytest.raises(Exception) as error:
        await limiter.check("client", now=2)

    assert getattr(error.value, "status_code", None) == 429
    await limiter.check("client", now=11)


@pytest.mark.asyncio
async def test_unknown_user_authentication_runs_dummy_password_check(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    checked_hashes: list[str] = []

    async def no_user(session: object, email: str) -> None:
        _ = session
        assert email == "missing@example.com"
        return None

    def capture_password_check(password: str, password_hash: str) -> bool:
        assert password == "candidate-password"
        checked_hashes.append(password_hash)
        return False

    monkeypatch.setattr(user_service, "get_user_by_email", no_user)
    monkeypatch.setattr(user_service, "verify_password", capture_password_check)

    authenticated = await user_service.authenticate_user(
        object(),  # type: ignore[arg-type]
        "missing@example.com",
        "candidate-password",
    )

    assert authenticated is None
    assert checked_hashes == [DUMMY_PASSWORD_HASH]


@pytest.mark.asyncio
async def test_password_change_revokes_existing_refresh_tokens(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = User(
        id=uuid.uuid4(),
        email="user@example.com",
        password_hash="old-hash",
        is_active=True,
        is_verified=False,
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        updated_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    revoked_users: list[uuid.UUID] = []

    class SessionStub:
        async def commit(self) -> None:
            return None

    async def revoke(session: object, target: User) -> None:
        _ = session
        revoked_users.append(target.id)

    async def reload_user(session: object, user_id: uuid.UUID) -> None:
        _ = session
        assert user_id == user.id
        return None

    monkeypatch.setattr(user_service, "revoke_user_refresh_tokens", revoke)
    monkeypatch.setattr(user_service, "get_user", reload_user)

    updated = await user_service.update_user(
        SessionStub(),  # type: ignore[arg-type]
        user,
        UserUpdate(password="new-password"),
    )

    assert updated is user
    assert updated.password_hash != "old-hash"
    assert revoked_users == [user.id]
