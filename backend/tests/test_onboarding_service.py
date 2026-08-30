import uuid
from datetime import UTC, datetime
from typing import cast

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User, UserAllergen, UserDietaryRule, UserProfile, UserProteinPreference
from app.schemas.onboarding import CURRENT_TERMS_VERSION, PrivacyAcknowledge
from app.users import onboarding as onboarding_service


@pytest.mark.asyncio
async def test_privacy_acknowledgement_records_terms_acceptance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        email="user@example.com",
        password_hash="unused",
    )
    profile = UserProfile(
        user_id=user_id,
        onboarding_status="not_started",
        allergy_status="not_provided",
        cuisine_preference_status="not_provided",
    )

    class SessionStub:
        committed: bool = False

        async def commit(self) -> None:
            self.committed = True

    async def return_profile(
        session: AsyncSession,
        requested_user_id: uuid.UUID,
    ) -> UserProfile:
        _ = session
        assert requested_user_id == user_id
        return profile

    monkeypatch.setattr(onboarding_service, "_ensure_profile", return_profile)
    session = SessionStub()

    _ = await onboarding_service.acknowledge_privacy(
        cast(AsyncSession, cast(object, session)),
        user,
        PrivacyAcknowledge(
            acknowledged=True,
            terms_accepted=True,
            terms_version=CURRENT_TERMS_VERSION,
        ),
    )

    assert session.committed is True
    assert user.terms_version == CURRENT_TERMS_VERSION
    assert user.terms_accepted_at is not None
    assert profile.privacy_notice_acknowledged_at == user.terms_accepted_at


def test_completion_allows_explicit_allergy_skip() -> None:
    now = datetime(2026, 6, 26, tzinfo=UTC)
    profile = UserProfile(
        user_id=uuid.uuid4(),
        country_code="GB",
        location_source="manual",
        privacy_notice_acknowledged_at=now,
        diet_pattern="vegetarian",
        allergy_status="not_provided",
        allergy_updated_at=now,
        dietary_rules_updated_at=now,
        cuisine_preference_status="no_preference",
    )

    assert onboarding_service._completion_errors(profile) == []  # pyright: ignore[reportPrivateUsage]


def test_protein_errors_detect_cross_field_conflicts() -> None:
    user_id = uuid.uuid4()
    profile = UserProfile(user_id=user_id, diet_pattern="omnivore")
    profile.dietary_rules = [UserDietaryRule(user_id=user_id, dietary_rule="avoid_pork")]
    profile.allergens = [UserAllergen(user_id=user_id, allergen="fish")]
    profile.protein_preferences = [
        UserProteinPreference(user_id=user_id, protein="pork"),
        UserProteinPreference(user_id=user_id, protein="fish"),
    ]

    assert onboarding_service._protein_errors(profile) == [  # pyright: ignore[reportPrivateUsage]
        "Pork protein conflicts with avoid_pork.",
        "Fish protein conflicts with fish allergy.",
    ]


def test_remove_incompatible_proteins_when_diet_changes() -> None:
    user_id = uuid.uuid4()
    profile = UserProfile(user_id=user_id, diet_pattern="pescatarian")
    profile.protein_preferences = [
        UserProteinPreference(user_id=user_id, protein="pork", preference_rank=1),
        UserProteinPreference(user_id=user_id, protein="beef", preference_rank=2),
        UserProteinPreference(user_id=user_id, protein="lamb", preference_rank=3),
        UserProteinPreference(user_id=user_id, protein="fish", preference_rank=4),
    ]

    onboarding_service._remove_incompatible_proteins(profile)  # pyright: ignore[reportPrivateUsage]

    assert [(item.protein, item.preference_rank) for item in profile.protein_preferences] == [
        ("fish", 1)
    ]


def test_remove_incompatible_proteins_when_rules_change() -> None:
    user_id = uuid.uuid4()
    profile = UserProfile(user_id=user_id, diet_pattern="omnivore")
    profile.dietary_rules = [UserDietaryRule(user_id=user_id, dietary_rule="avoid_beef")]
    profile.protein_preferences = [
        UserProteinPreference(user_id=user_id, protein="beef", preference_rank=1),
        UserProteinPreference(user_id=user_id, protein="chicken", preference_rank=2),
    ]

    onboarding_service._remove_incompatible_proteins(profile)  # pyright: ignore[reportPrivateUsage]

    assert [(item.protein, item.preference_rank) for item in profile.protein_preferences] == [
        ("chicken", 1)
    ]
