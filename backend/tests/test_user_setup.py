import uuid
from datetime import UTC, datetime, timedelta
from typing import cast

import pytest
from sqlalchemy import Table

from app.auth import TokenDecodeError, create_access_token, decode_access_token
from app.auth.password_reset import generate_password_reset_token, hash_password_reset_token
from app.auth.refresh_tokens import generate_refresh_token, hash_refresh_token
from app.data.data_key import UserDataKey
from app.data.data_target import USER_ONBOARDING_PROFILE_TARGET, USER_PROFILE_TARGET
from app.data.enums import StorageBackendType
from app.models import (
    User,
    UserAllergen,
    UserConsent,
    UserCuisinePreference,
    UserDietaryRule,
    UserPasswordResetToken,
    UserProfile,
    UserProteinPreference,
    UserRefreshToken,
)


def test_user_tables_are_configured() -> None:
    users_table = cast(Table, User.__table__)
    user_profiles_table = cast(Table, UserProfile.__table__)
    user_allergens_table = cast(Table, UserAllergen.__table__)
    user_dietary_rules_table = cast(Table, UserDietaryRule.__table__)
    user_cuisine_preferences_table = cast(Table, UserCuisinePreference.__table__)
    user_protein_preferences_table = cast(Table, UserProteinPreference.__table__)
    user_consents_table = cast(Table, UserConsent.__table__)
    refresh_tokens_table = cast(Table, UserRefreshToken.__table__)
    password_reset_tokens_table = cast(Table, UserPasswordResetToken.__table__)

    assert User.__tablename__ == "users"
    assert UserProfile.__tablename__ == "user_profiles"
    assert UserAllergen.__tablename__ == "user_allergens"
    assert UserDietaryRule.__tablename__ == "user_dietary_rules"
    assert UserCuisinePreference.__tablename__ == "user_cuisine_preferences"
    assert UserProteinPreference.__tablename__ == "user_protein_preferences"
    assert UserConsent.__tablename__ == "user_consents"
    assert UserRefreshToken.__tablename__ == "user_refresh_tokens"
    assert UserPasswordResetToken.__tablename__ == "user_password_reset_tokens"
    assert users_table.c.id.primary_key is True
    assert cast(object, users_table.c.email.unique) is True
    assert user_profiles_table.c.user_id.primary_key is True
    assert next(iter(user_profiles_table.c.user_id.foreign_keys)).ondelete == "CASCADE"
    assert {
        "onboarding_status",
        "allergy_status",
        "allergy_updated_at",
        "dietary_rules_updated_at",
        "cuisine_preference_status",
    } <= set(user_profiles_table.c.keys())
    assert {constraint.name for constraint in user_profiles_table.constraints} >= {
        "ck_user_profiles_onboarding_status",
        "ck_user_profiles_diet_pattern",
        "ck_user_profiles_allergy_status",
    }
    assert user_allergens_table.c.user_id.primary_key is True
    assert user_allergens_table.c.allergen.primary_key is True
    assert next(iter(user_allergens_table.c.user_id.foreign_keys)).ondelete == "CASCADE"
    assert user_dietary_rules_table.c.user_id.primary_key is True
    assert user_dietary_rules_table.c.dietary_rule.primary_key is True
    assert user_cuisine_preferences_table.c.user_id.primary_key is True
    assert user_cuisine_preferences_table.c.area.primary_key is True
    assert user_protein_preferences_table.c.user_id.primary_key is True
    assert user_protein_preferences_table.c.protein.primary_key is True
    assert cast(object, user_consents_table.c.user_id.index) is True
    assert next(iter(user_consents_table.c.user_id.foreign_keys)).ondelete == "CASCADE"
    assert cast(object, refresh_tokens_table.c.token_hash.unique) is True
    assert next(iter(refresh_tokens_table.c.user_id.foreign_keys)).ondelete == "CASCADE"
    assert cast(object, password_reset_tokens_table.c.token_hash.unique) is True
    assert next(iter(password_reset_tokens_table.c.user_id.foreign_keys)).ondelete == "CASCADE"


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


def test_user_onboarding_profile_data_target_uses_postgres_with_cache() -> None:
    assert USER_ONBOARDING_PROFILE_TARGET.key == UserDataKey.ONBOARDING_PROFILE
    assert USER_ONBOARDING_PROFILE_TARGET.spec is not None
    assert USER_ONBOARDING_PROFILE_TARGET.spec.backend == StorageBackendType.POSTGRES
    assert USER_ONBOARDING_PROFILE_TARGET.spec.enable_memory_cache is True
    assert USER_ONBOARDING_PROFILE_TARGET.model_dump(mode="json") == {
        "key": "user_onboarding_profile",
        "spec": {
            "type": "OnboardingProfileResponse",
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


def test_refresh_token_generation_returns_hashed_opaque_token() -> None:
    token = generate_refresh_token()
    token_hash = hash_refresh_token(token)

    assert len(token) >= 32
    assert token not in token_hash
    assert len(token_hash) == 64
    assert hash_refresh_token(token) == token_hash


def test_password_reset_token_generation_returns_hashed_opaque_token() -> None:
    token = generate_password_reset_token()
    token_hash = hash_password_reset_token(token)

    assert len(token) >= 32
    assert token not in token_hash
    assert len(token_hash) == 64
    assert hash_password_reset_token(token) == token_hash
