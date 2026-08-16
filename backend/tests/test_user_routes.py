import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from starlette.requests import Request

from app.api.v1.routes import auth as auth_routes
from app.api.v1.routes import users as user_routes
from app.auth.dependencies import get_current_user
from app.db.session import get_db_session
from app.main import create_app
from app.models import User, UserProfile
from app.schemas.privacy import (
    UserDataExport,
    UserDataExportAccount,
    UserDataExportRecipeActivity,
    UserDataExportSecurityRecords,
)
from app.users.geolocation import infer_coarse_location
from app.users.privacy import InvalidCurrentPasswordError


async def _dummy_db_session() -> AsyncGenerator[object, None]:
    yield object()


def test_infer_coarse_location_from_supported_headers() -> None:
    request = Request(
        {
            "type": "http",
            "headers": [
                (b"cf-ipcountry", b"gb"),
                (b"cf-region-code", b"lnd"),
            ],
        }
    )

    location = infer_coarse_location(request, trust_headers=True)

    assert location is not None
    assert location.country_code == "GB"
    assert location.region_code == "LND"
    assert location.source == "coarse_header"


def test_coarse_location_headers_are_ignored_unless_trusted() -> None:
    request = Request(
        {
            "type": "http",
            "headers": [(b"cf-ipcountry", b"gb")],
        }
    )

    assert infer_coarse_location(request) is None


def test_register_user_validates_email_and_password() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/api/v1/users",
        json={"email": "not-an-email", "password": "short"},
    )

    assert response.status_code == 422


def test_read_current_user_requires_authentication() -> None:
    client = TestClient(create_app())

    response = client.get("/api/v1/users/me")

    assert response.status_code == 401


def test_read_current_user_returns_authenticated_user() -> None:
    app = create_app()
    user_id = uuid.uuid4()
    now = datetime(2026, 6, 5, 12, 0, tzinfo=UTC)
    user = User(
        id=user_id,
        email="user@example.com",
        password_hash="unused",
        is_active=True,
        is_verified=False,
        created_at=now,
        updated_at=now,
    )
    user.profile = UserProfile(
        user_id=user_id,
        display_name="Seasonal Cook",
        country_code="GB",
        region_code="GB-LND",
        location_source="manual",
    )

    async def override_current_user() -> User:
        return user

    app.dependency_overrides[get_current_user] = override_current_user
    client = TestClient(app)

    response = client.get("/api/v1/users/me")

    assert response.status_code == 200
    assert response.json() == {
        "id": str(user_id),
        "email": "user@example.com",
        "is_active": True,
        "is_verified": False,
        "created_at": "2026-06-05T12:00:00Z",
        "updated_at": "2026-06-05T12:00:00Z",
        "profile": {
            "user_id": str(user_id),
            "display_name": "Seasonal Cook",
            "country_code": "GB",
            "region_code": "GB-LND",
            "location_source": "manual",
        },
    }


def test_read_user_rejects_access_to_another_user() -> None:
    app = create_app()
    current_user = User(
        id=uuid.uuid4(),
        email="user@example.com",
        password_hash="unused",
        is_active=True,
        is_verified=False,
        created_at=datetime(2026, 6, 5, 12, 0, tzinfo=UTC),
        updated_at=datetime(2026, 6, 5, 12, 0, tzinfo=UTC),
    )

    async def override_current_user() -> User:
        return current_user

    app.dependency_overrides[get_current_user] = override_current_user
    app.dependency_overrides[get_db_session] = _dummy_db_session
    client = TestClient(app)

    response = client.get(f"/api/v1/users/{uuid.uuid4()}")

    assert response.status_code == 403
    assert response.json() == {"detail": "Cannot access another user"}


def test_update_user_rejects_self_service_is_active_change() -> None:
    app = create_app()
    current_user = User(
        id=uuid.uuid4(),
        email="user@example.com",
        password_hash="unused",
        is_active=True,
        is_verified=False,
        created_at=datetime(2026, 6, 5, 12, 0, tzinfo=UTC),
        updated_at=datetime(2026, 6, 5, 12, 0, tzinfo=UTC),
    )

    async def override_current_user() -> User:
        return current_user

    app.dependency_overrides[get_current_user] = override_current_user
    app.dependency_overrides[get_db_session] = _dummy_db_session
    client = TestClient(app)

    response = client.patch("/api/v1/users/me", json={"is_active": False})

    assert response.status_code == 422


def test_logout_accepts_refresh_token_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    app = create_app()

    async def override_revoke_refresh_token(session: object, refresh_token: str) -> None:
        assert session is not None
        assert refresh_token == "refresh-token"

    app.dependency_overrides[get_db_session] = _dummy_db_session
    monkeypatch.setattr(auth_routes, "revoke_refresh_token", override_revoke_refresh_token)
    client = TestClient(app)

    response = client.post("/api/v1/auth/logout", json={"refresh_token": "refresh-token"})

    assert response.status_code == 204


def test_password_reset_request_returns_generic_message(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = create_app()

    async def override_request_password_reset(session: object, email: str) -> None:
        assert session is not None
        assert email == "user@example.com"

    app.dependency_overrides[get_db_session] = _dummy_db_session
    monkeypatch.setattr(
        auth_routes,
        "request_password_reset",
        override_request_password_reset,
    )
    client = TestClient(app)

    response = client.post(
        "/api/v1/auth/password-reset/request",
        json={"email": "user@example.com"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "message": "If an account exists for this email, password reset instructions will be sent."
    }


def test_password_reset_confirm_rejects_short_password() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"reset_token": "reset-token", "new_password": "short"},
    )

    assert response.status_code == 422


def test_data_export_requires_current_password_and_sets_download_headers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = create_app()
    current_user = User(
        id=uuid.uuid4(),
        email="user@example.com",
        password_hash="unused",
        is_active=True,
        is_verified=False,
        created_at=datetime(2026, 6, 5, 12, 0, tzinfo=UTC),
        updated_at=datetime(2026, 6, 5, 12, 0, tzinfo=UTC),
    )

    async def override_current_user() -> User:
        return current_user

    async def override_export(
        session: object,
        *,
        user: User,
        current_password: str,
    ) -> UserDataExport:
        assert session is not None
        assert user is current_user
        assert current_password == "correct-password"
        return UserDataExport(
            format_version="seasonly-user-data-v1",
            exported_at=datetime(2026, 7, 24, 12, 0, tzinfo=UTC),
            account=UserDataExportAccount(
                id=user.id,
                email=user.email,
                is_active=user.is_active,
                is_verified=user.is_verified,
                created_at=user.created_at,
                updated_at=user.updated_at,
            ),
            profile=None,
            consents=[],
            recipe_activity=UserDataExportRecipeActivity(
                favourites=[],
                history=[],
                planned_meals=[],
            ),
            recommendation_events=[],
            security_records=UserDataExportSecurityRecords(
                refresh_sessions=[],
                password_reset_requests=[],
            ),
        )

    app.dependency_overrides[get_current_user] = override_current_user
    app.dependency_overrides[get_db_session] = _dummy_db_session
    monkeypatch.setattr(user_routes, "export_user_data", override_export)

    response = TestClient(app).post(
        "/api/v1/users/me/data-export",
        json={"current_password": "correct-password"},
    )

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["content-disposition"] == (
        'attachment; filename="seasonly-user-data-export.json"'
    )
    assert response.json()["format_version"] == "seasonly-user-data-v1"


def test_data_export_rejects_incorrect_current_password(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = create_app()
    current_user = User(
        id=uuid.uuid4(),
        email="user@example.com",
        password_hash="unused",
        is_active=True,
        is_verified=False,
        created_at=datetime(2026, 6, 5, 12, 0, tzinfo=UTC),
        updated_at=datetime(2026, 6, 5, 12, 0, tzinfo=UTC),
    )

    async def override_current_user() -> User:
        return current_user

    async def reject_export(*args: object, **kwargs: object) -> None:
        _ = args, kwargs
        raise InvalidCurrentPasswordError("Current password is incorrect")

    app.dependency_overrides[get_current_user] = override_current_user
    app.dependency_overrides[get_db_session] = _dummy_db_session
    monkeypatch.setattr(user_routes, "export_user_data", reject_export)

    response = TestClient(app).post(
        "/api/v1/users/me/data-export",
        json={"current_password": "wrong-password"},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Current password is incorrect"}


def test_account_deletion_requires_exact_confirmation() -> None:
    app = create_app()
    current_user = User(
        id=uuid.uuid4(),
        email="user@example.com",
        password_hash="unused",
        is_active=True,
        is_verified=False,
        created_at=datetime(2026, 6, 5, 12, 0, tzinfo=UTC),
        updated_at=datetime(2026, 6, 5, 12, 0, tzinfo=UTC),
    )

    async def override_current_user() -> User:
        return current_user

    app.dependency_overrides[get_current_user] = override_current_user
    app.dependency_overrides[get_db_session] = _dummy_db_session

    response = TestClient(app).request(
        "DELETE",
        "/api/v1/users/me",
        json={"current_password": "correct-password", "confirmation": "delete"},
    )

    assert response.status_code == 422


def test_account_deletion_reconfirms_password_and_returns_no_content(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = create_app()
    current_user = User(
        id=uuid.uuid4(),
        email="user@example.com",
        password_hash="unused",
        is_active=True,
        is_verified=False,
        created_at=datetime(2026, 6, 5, 12, 0, tzinfo=UTC),
        updated_at=datetime(2026, 6, 5, 12, 0, tzinfo=UTC),
    )
    deleted_users: list[uuid.UUID] = []

    async def override_current_user() -> User:
        return current_user

    async def override_delete(
        session: object,
        *,
        user: User,
        current_password: str,
    ) -> None:
        assert session is not None
        assert current_password == "correct-password"
        deleted_users.append(user.id)

    app.dependency_overrides[get_current_user] = override_current_user
    app.dependency_overrides[get_db_session] = _dummy_db_session
    monkeypatch.setattr(user_routes, "delete_user_data", override_delete)

    response = TestClient(app).request(
        "DELETE",
        "/api/v1/users/me",
        json={"current_password": "correct-password", "confirmation": "DELETE"},
    )

    assert response.status_code == 204
    assert deleted_users == [current_user.id]


def test_account_deletion_rejects_incorrect_current_password(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = create_app()
    current_user = User(
        id=uuid.uuid4(),
        email="user@example.com",
        password_hash="unused",
        is_active=True,
        is_verified=False,
        created_at=datetime(2026, 6, 5, 12, 0, tzinfo=UTC),
        updated_at=datetime(2026, 6, 5, 12, 0, tzinfo=UTC),
    )

    async def override_current_user() -> User:
        return current_user

    async def reject_delete(*args: object, **kwargs: object) -> None:
        _ = args, kwargs
        raise InvalidCurrentPasswordError("Current password is incorrect")

    app.dependency_overrides[get_current_user] = override_current_user
    app.dependency_overrides[get_db_session] = _dummy_db_session
    monkeypatch.setattr(user_routes, "delete_user_data", reject_delete)

    response = TestClient(app).request(
        "DELETE",
        "/api/v1/users/me",
        json={"current_password": "wrong-password", "confirmation": "DELETE"},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Current password is incorrect"}


@pytest.mark.parametrize(
    ("method", "path", "payload"),
    [
        (
            "POST",
            "/api/v1/users/me/data-export",
            {"current_password": "correct-password"},
        ),
        (
            "DELETE",
            "/api/v1/users/me",
            {"current_password": "correct-password", "confirmation": "DELETE"},
        ),
    ],
)
def test_privacy_controls_require_authentication(
    method: str,
    path: str,
    payload: dict[str, str],
) -> None:
    response = TestClient(create_app()).request(method, path, json=payload)

    assert response.status_code == 401
