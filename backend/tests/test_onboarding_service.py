import uuid
from datetime import UTC, datetime

from app.models import UserAllergen, UserDietaryRule, UserProfile, UserProteinPreference
from app.users import onboarding as onboarding_service


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

    assert onboarding_service._completion_errors(profile) == []


def test_protein_errors_detect_cross_field_conflicts() -> None:
    user_id = uuid.uuid4()
    profile = UserProfile(user_id=user_id, diet_pattern="omnivore")
    profile.dietary_rules = [UserDietaryRule(user_id=user_id, dietary_rule="avoid_pork")]
    profile.allergens = [UserAllergen(user_id=user_id, allergen="fish")]
    profile.protein_preferences = [
        UserProteinPreference(user_id=user_id, protein="pork"),
        UserProteinPreference(user_id=user_id, protein="fish"),
    ]

    assert onboarding_service._protein_errors(profile) == [
        "Pork protein conflicts with avoid_pork.",
        "Fish protein conflicts with fish allergy.",
    ]
