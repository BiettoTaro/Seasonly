import uuid
from datetime import UTC, datetime, timedelta
from typing import cast

import pytest
from sqlalchemy import Table

from app.auth import TokenDecodeError, create_access_token, decode_access_token
from app.data.data_key import UserDataKey
from app.data.data_target import USER_PROFILE_TARGET
from app.data.enums import StorageBackendType
from app.models import User, UserProfile


def test_user_tables_are_configured() -> None:
    users_table = cast(Table, User.__table__)
    user_profiles_table = cast(Table, UserProfile.__table__)

    assert User.__tablename__ == "users"
    assert UserProfile.__tablename__ == "user_profiles"
    assert users_table.c.id.primary_key is True
    assert cast(object, users_table.c.email.unique) is True
    assert user_profiles_table.c.user_id.primary_key is True
    assert next(iter(user_profiles_table.c.user_id.foreign_keys)).ondelete == "CASCADE"


def test_user_profile_data_target_uses_postgres_with_cache() -> None:
    assert USER_PROFILE_TARGET.key == UserDataKey.PROFILE
    assert USER_PROFILE_TARGET.spec is not None
    assert USER_PROFILE_TARGET.spec.backend == StorageBackendType.POSTGRES
    assert USER_PROFILE_TARGET.spec.enable_memory_cache is True
    assert USER_PROFILE_TARGET.model_dump(mode="json") == {
        "key": "user_profile",
        "spec": {
            "type": "UserProfileResponse",
            "backend": "postgres",
            "enable_memory_cache": True,
        },
        "target_type": None,
        "name": None,
        "description": None,
    }


def test_access_token_round_trip_returns_user_uuid() -> None:
    user_id = uuid.uuid4()
    token = create_access_token(
        user_id,
        now=datetime(2026, 1, 1, tzinfo=UTC),
        expires_delta=timedelta(minutes=5),
    )

    assert decode_access_token(token, now=datetime(2026, 1, 1, 0, 1, tzinfo=UTC)) == user_id


def test_expired_access_token_is_rejected() -> None:
    token = create_access_token(
        uuid.uuid4(),
        now=datetime(2026, 1, 1, tzinfo=UTC),
        expires_delta=timedelta(minutes=5),
    )

    with pytest.raises(TokenDecodeError, match="expired"):
        _ = decode_access_token(token, now=datetime(2026, 1, 1, 0, 6, tzinfo=UTC))
