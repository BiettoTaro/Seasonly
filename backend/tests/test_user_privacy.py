import json
import uuid
from datetime import UTC, datetime, timedelta
from typing import cast

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Recipe,
    RecommendationEvent,
    User,
    UserAllergen,
    UserConsent,
    UserCuisinePreference,
    UserDietaryRule,
    UserPasswordResetToken,
    UserPlannedMeal,
    UserProfile,
    UserProteinPreference,
    UserRecipeFavourite,
    UserRecipeHistory,
    UserRefreshToken,
)
from app.users import privacy as user_privacy
from app.users.security import hash_password

NOW = datetime(2026, 7, 24, 12, 0, tzinfo=UTC)
CURRENT_PASSWORD = "correct-password"


def _user() -> User:
    return User(
        id=uuid.UUID("10000000-0000-0000-0000-000000000001"),
        email="user@example.com",
        password_hash=hash_password(CURRENT_PASSWORD),
        is_active=True,
        is_verified=False,
        created_at=NOW,
        updated_at=NOW,
    )


def _privacy_records(user: User) -> user_privacy.UserPrivacyRecords:
    recipe_id = uuid.UUID("20000000-0000-0000-0000-000000000001")
    consent_id = uuid.UUID("30000000-0000-0000-0000-000000000001")
    profile = UserProfile(
        user_id=user.id,
        display_name="Seasonal Cook",
        country_code="GB",
        region_code="GB-LND",
        location_source="manual",
        onboarding_status="completed",
        privacy_notice_version="2026-07-24",
        privacy_notice_acknowledged_at=NOW,
        diet_pattern="pescatarian",
        allergy_status="provided",
        allergy_updated_at=NOW,
        dietary_rules_updated_at=NOW,
        cuisine_preference_status="provided",
        completed_at=NOW,
        updated_at=NOW,
    )
    profile.allergens = [UserAllergen(user_id=user.id, allergen="peanuts")]
    profile.dietary_rules = [UserDietaryRule(user_id=user.id, dietary_rule="avoid_beef")]
    profile.cuisine_preferences = [
        UserCuisinePreference(
            user_id=user.id,
            area="Italian",
            preference_rank=1,
        )
    ]
    profile.protein_preferences = [
        UserProteinPreference(
            user_id=user.id,
            protein="fish",
            preference_rank=1,
        )
    ]
    profile.consents = [
        UserConsent(
            id=consent_id,
            user_id=user.id,
            consent_type="personalization",
            notice_version="2026-07-24",
            granted_at=NOW,
            withdrawn_at=None,
        )
    ]
    recipe = Recipe(
        id=recipe_id,
        provider="themealdb",
        provider_recipe_id="1",
        name="Seasonal pasta",
        instructions="Cook it.",
        raw_payload={},
        is_active=True,
        first_seen_at=NOW,
        last_seen_at=NOW,
        fetched_at=NOW,
    )
    favourite = UserRecipeFavourite(
        user_id=user.id,
        recipe_id=recipe_id,
        created_at=NOW,
    )
    history = UserRecipeHistory(
        user_id=user.id,
        recipe_id=recipe_id,
        viewed_at=NOW,
    )
    planned_meal = UserPlannedMeal(
        id=uuid.UUID("40000000-0000-0000-0000-000000000001"),
        user_id=user.id,
        recipe_id=recipe_id,
        day_of_week=1,
        meal_slot="dinner",
        created_at=NOW,
    )
    event = RecommendationEvent(
        id=uuid.UUID("50000000-0000-0000-0000-000000000001"),
        user_id=user.id,
        recipe_id=recipe_id,
        consent_id=consent_id,
        event_type="open",
        source="recipe_detail",
        slate_id=None,
        position=None,
        occurred_at=NOW,
        expires_at=NOW + timedelta(days=365),
    )
    refresh_token = UserRefreshToken(
        id=uuid.UUID("60000000-0000-0000-0000-000000000001"),
        user_id=user.id,
        family_id=uuid.UUID("70000000-0000-0000-0000-000000000001"),
        parent_token_id=None,
        token_hash="secret-refresh-token-hash",
        created_at=NOW,
        expires_at=NOW + timedelta(days=30),
        revoked_at=None,
    )
    reset_token = UserPasswordResetToken(
        id=uuid.UUID("80000000-0000-0000-0000-000000000001"),
        user_id=user.id,
        token_hash="secret-reset-token-hash",
        created_at=NOW,
        expires_at=NOW + timedelta(minutes=30),
        used_at=None,
    )
    return user_privacy.UserPrivacyRecords(
        profile=profile,
        favourites=[(favourite, recipe)],
        history=[(history, recipe)],
        planned_meals=[(planned_meal, recipe)],
        recommendation_events=[event],
        refresh_tokens=[refresh_token],
        password_reset_tokens=[reset_token],
    )


@pytest.mark.asyncio
async def test_export_requires_current_password_before_reading_records(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def reject_load(*args: object, **kwargs: object) -> user_privacy.UserPrivacyRecords:
        _ = args, kwargs
        raise AssertionError("Private records must not be read before password verification")

    monkeypatch.setattr(user_privacy, "_load_user_privacy_records", reject_load)

    with pytest.raises(user_privacy.InvalidCurrentPasswordError):
        _ = await user_privacy.export_user_data(
            cast(AsyncSession, object()),
            user=_user(),
            current_password="wrong-password",
        )


@pytest.mark.asyncio
async def test_export_contains_user_owned_records_without_security_secrets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = _user()
    records = _privacy_records(user)

    async def load_records(
        session: AsyncSession,
        *,
        user_id: uuid.UUID,
    ) -> user_privacy.UserPrivacyRecords:
        _ = session
        assert user_id == user.id
        return records

    monkeypatch.setattr(user_privacy, "_load_user_privacy_records", load_records)

    data_export = await user_privacy.export_user_data(
        cast(AsyncSession, object()),
        user=user,
        current_password=CURRENT_PASSWORD,
        exported_at=NOW,
    )
    payload = data_export.model_dump(mode="json")
    serialized = json.dumps(payload)

    assert data_export.format_version == "seasonly-user-data-v1"
    assert data_export.profile is not None
    assert data_export.profile.allergens == ["peanuts"]
    assert data_export.recipe_activity.favourites[0].recipe_name == "Seasonal pasta"
    assert len(data_export.recommendation_events) == 1
    assert len(data_export.security_records.refresh_sessions) == 1
    assert "password_hash" not in serialized
    assert "token_hash" not in serialized
    assert CURRENT_PASSWORD not in serialized
    assert "secret-refresh-token-hash" not in serialized
    assert "secret-reset-token-hash" not in serialized


@pytest.mark.asyncio
async def test_deletion_requires_password_and_commits_hard_delete() -> None:
    user = _user()
    calls: list[str] = []

    class SessionStub:
        async def delete(self, target: User) -> None:
            assert target is user
            calls.append("delete")

        async def commit(self) -> None:
            calls.append("commit")

    with pytest.raises(user_privacy.InvalidCurrentPasswordError):
        await user_privacy.delete_user_data(
            cast(AsyncSession, cast(object, SessionStub())),
            user=user,
            current_password="wrong-password",
        )
    assert calls == []

    await user_privacy.delete_user_data(
        cast(AsyncSession, cast(object, SessionStub())),
        user=user,
        current_password=CURRENT_PASSWORD,
    )

    assert calls == ["delete", "commit"]
