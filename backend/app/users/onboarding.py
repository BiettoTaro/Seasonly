import uuid
from collections.abc import Iterable

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.data.enums import (
    Allergen,
    AllergyProfileStatus,
    ConsentType,
    CountryCode,
    CuisinePreferenceStatus,
    DietaryRule,
    DietPattern,
    LocationSource,
    OnboardingStatus,
    OnboardingStep,
    ProteinPreference,
)
from app.models import (
    ProduceSeason,
    Recipe,
    User,
    UserAllergen,
    UserConsent,
    UserCuisinePreference,
    UserDietaryRule,
    UserProfile,
    UserProteinPreference,
)
from app.models.user import utc_now
from app.schemas.onboarding import (
    CURRENT_ALLERGY_CONSENT_VERSION,
    CURRENT_PRIVACY_NOTICE_VERSION,
    AllergyUpdate,
    CuisineUpdate,
    DietaryRulesUpdate,
    DietUpdate,
    LocationUpdate,
    OnboardingProfileResponse,
    PrivacyAcknowledge,
    ProteinUpdate,
)

PROTEIN_REQUIRED_DIETS = {
    DietPattern.OMNIVORE,
    DietPattern.FLEXITARIAN,
    DietPattern.PESCATARIAN,
}
PESCATARIAN_ALLOWED_PROTEINS = {
    ProteinPreference.FISH,
    ProteinPreference.SEAFOOD,
    ProteinPreference.EGGS,
    ProteinPreference.TOFU,
    ProteinPreference.LEGUMES,
}
VEGETARIAN_ALLOWED_PROTEINS = {
    ProteinPreference.EGGS,
    ProteinPreference.TOFU,
    ProteinPreference.LEGUMES,
}
VEGAN_ALLOWED_PROTEINS = {
    ProteinPreference.TOFU,
    ProteinPreference.LEGUMES,
}


class IncompleteOnboardingError(ValueError):
    def __init__(self, errors: list[str]) -> None:
        super().__init__("Onboarding profile is incomplete")
        self.errors: list[str] = errors


class InvalidOnboardingUpdateError(ValueError):
    pass


async def get_onboarding_profile(
    session: AsyncSession,
    user: User,
) -> OnboardingProfileResponse:
    profile = await _ensure_profile(session, user.id)
    return _build_response(profile)


async def acknowledge_privacy(
    session: AsyncSession,
    user: User,
    payload: PrivacyAcknowledge,
) -> OnboardingProfileResponse:
    profile = await _ensure_profile(session, user.id)
    acknowledged_at = utc_now()
    profile.privacy_notice_version = CURRENT_PRIVACY_NOTICE_VERSION
    profile.privacy_notice_acknowledged_at = acknowledged_at
    user.terms_version = payload.terms_version
    user.terms_accepted_at = acknowledged_at
    _touch_in_progress(profile)
    await session.commit()
    return await get_onboarding_profile(session, user)


async def update_location(
    session: AsyncSession,
    user: User,
    payload: LocationUpdate,
) -> OnboardingProfileResponse:
    profile = await _ensure_profile(session, user.id)
    profile.country_code = payload.country_code.value
    profile.region_code = payload.region_code
    profile.location_source = payload.source.value
    _touch_in_progress(profile)
    await session.commit()
    return await get_onboarding_profile(session, user)


async def update_diet(
    session: AsyncSession,
    user: User,
    payload: DietUpdate,
) -> OnboardingProfileResponse:
    profile = await _ensure_profile(session, user.id)
    profile.diet_pattern = payload.diet_pattern.value
    _remove_incompatible_proteins(profile)
    _touch_in_progress(profile)
    await session.commit()
    return await get_onboarding_profile(session, user)


async def update_allergies(
    session: AsyncSession,
    user: User,
    payload: AllergyUpdate,
) -> OnboardingProfileResponse:
    profile = await _ensure_profile(session, user.id)
    profile.allergy_status = payload.status.value
    profile.allergens = [
        UserAllergen(user_id=user.id, allergen=allergen.value)
        for allergen in sorted(payload.allergens, key=lambda value: value.value)
    ]
    profile.allergy_updated_at = utc_now()
    if payload.status == AllergyProfileStatus.PROVIDED:
        _ensure_allergy_consent(profile, user.id)
    else:
        _withdraw_allergy_consents(profile)
    _remove_incompatible_proteins(profile)
    _touch_in_progress(profile)
    await session.commit()
    return await get_onboarding_profile(session, user)


async def update_dietary_rules(
    session: AsyncSession,
    user: User,
    payload: DietaryRulesUpdate,
) -> OnboardingProfileResponse:
    profile = await _ensure_profile(session, user.id)
    profile.dietary_rules = [
        UserDietaryRule(user_id=user.id, dietary_rule=rule.value)
        for rule in sorted(payload.dietary_rules, key=lambda value: value.value)
    ]
    profile.dietary_rules_updated_at = utc_now()
    _remove_incompatible_proteins(profile)
    _touch_in_progress(profile)
    await session.commit()
    return await get_onboarding_profile(session, user)


async def update_cuisines(
    session: AsyncSession,
    user: User,
    payload: CuisineUpdate,
) -> OnboardingProfileResponse:
    await _validate_recipe_areas(session, payload.areas)
    profile = await _ensure_profile(session, user.id)
    profile.cuisine_preference_status = payload.status.value
    profile.cuisine_preferences = [
        UserCuisinePreference(user_id=user.id, area=area, preference_rank=index + 1)
        for index, area in enumerate(payload.areas)
    ]
    _touch_in_progress(profile)
    await session.commit()
    return await get_onboarding_profile(session, user)


async def update_proteins(
    session: AsyncSession,
    user: User,
    payload: ProteinUpdate,
) -> OnboardingProfileResponse:
    profile = await _ensure_profile(session, user.id)
    profile.protein_preferences = [
        UserProteinPreference(user_id=user.id, protein=protein.value, preference_rank=index + 1)
        for index, protein in enumerate(payload.proteins)
    ]
    _touch_in_progress(profile)
    _validate_current_proteins(profile)
    await session.commit()
    return await get_onboarding_profile(session, user)


async def complete_onboarding(
    session: AsyncSession,
    user: User,
) -> OnboardingProfileResponse:
    profile = await _ensure_profile(session, user.id)
    errors = _completion_errors(profile)
    if errors:
        raise IncompleteOnboardingError(errors)
    profile.onboarding_status = OnboardingStatus.COMPLETED.value
    profile.completed_at = utc_now()
    profile.updated_at = utc_now()
    await session.commit()
    return await get_onboarding_profile(session, user)


async def list_cuisine_areas(session: AsyncSession) -> list[str]:
    result = await session.execute(
        select(Recipe.area)
        .where(Recipe.is_active.is_(True), Recipe.area.is_not(None), Recipe.area != "")
        .distinct()
        .order_by(Recipe.area)
    )
    return [area for area in result.scalars().all() if area]


async def list_countries_with_seasonal_data(
    session: AsyncSession,
) -> set[CountryCode]:
    result = await session.execute(select(ProduceSeason.country_code).distinct())
    return {CountryCode(country_code) for country_code in result.scalars().all()}


def _touch_in_progress(profile: UserProfile) -> None:
    if profile.onboarding_status != OnboardingStatus.COMPLETED.value:
        profile.onboarding_status = OnboardingStatus.IN_PROGRESS.value
    profile.updated_at = utc_now()


def _ensure_allergy_consent(profile: UserProfile, user_id: uuid.UUID) -> None:
    has_active_consent = any(
        consent.consent_type == ConsentType.ALLERGY_STORAGE.value and consent.withdrawn_at is None
        for consent in profile.consents
    )
    if has_active_consent:
        return

    profile.consents.append(
        UserConsent(
            user_id=user_id,
            consent_type=ConsentType.ALLERGY_STORAGE.value,
            notice_version=CURRENT_ALLERGY_CONSENT_VERSION,
            granted_at=utc_now(),
        )
    )


def _withdraw_allergy_consents(profile: UserProfile) -> None:
    withdrawn_at = utc_now()
    for consent in profile.consents:
        if (
            consent.consent_type == ConsentType.ALLERGY_STORAGE.value
            and consent.withdrawn_at is None
        ):
            consent.withdrawn_at = withdrawn_at


async def _ensure_profile(session: AsyncSession, user_id: uuid.UUID) -> UserProfile:
    profile = await _load_profile(session, user_id)
    if profile is not None:
        return profile

    profile = UserProfile(user_id=user_id)
    session.add(profile)
    await session.flush()
    return await _load_profile(session, user_id) or profile


async def _load_profile(session: AsyncSession, user_id: uuid.UUID) -> UserProfile | None:
    result = await session.execute(
        select(UserProfile)
        .options(
            selectinload(UserProfile.allergens),
            selectinload(UserProfile.dietary_rules),
            selectinload(UserProfile.cuisine_preferences),
            selectinload(UserProfile.protein_preferences),
            selectinload(UserProfile.consents),
        )
        .where(UserProfile.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def _validate_recipe_areas(session: AsyncSession, areas: Iterable[str]) -> None:
    requested = {area.casefold(): area for area in areas}
    if not requested:
        return

    result = await session.execute(
        select(func.lower(Recipe.area))
        .where(
            Recipe.is_active.is_(True),
            Recipe.area.is_not(None),
            func.lower(Recipe.area).in_(requested),
        )
        .distinct()
    )
    existing = set(result.scalars().all())
    missing = [area for key, area in requested.items() if key not in existing]
    if missing:
        raise InvalidOnboardingUpdateError(
            f"Unknown or inactive cuisine area: {', '.join(sorted(missing))}"
        )


def _validate_current_proteins(profile: UserProfile) -> None:
    errors = _protein_errors(profile)
    if errors:
        raise InvalidOnboardingUpdateError("; ".join(errors))


def _protein_errors(profile: UserProfile) -> list[str]:
    if profile.diet_pattern is None:
        return []

    diet = DietPattern(profile.diet_pattern)
    proteins = {ProteinPreference(item.protein) for item in profile.protein_preferences}
    allergens = {Allergen(item.allergen) for item in profile.allergens}
    rules = {DietaryRule(item.dietary_rule) for item in profile.dietary_rules}
    errors: list[str] = []

    if diet == DietPattern.PESCATARIAN:
        disallowed = proteins - PESCATARIAN_ALLOWED_PROTEINS
        if disallowed:
            errors.append(
                "Pescatarian profiles can only select fish, seafood, eggs, or plant proteins."
            )
    if diet == DietPattern.VEGETARIAN:
        disallowed = proteins - VEGETARIAN_ALLOWED_PROTEINS
        if disallowed:
            errors.append("Vegetarian profiles can only select eggs or plant proteins.")
    if diet == DietPattern.VEGAN:
        disallowed = proteins - VEGAN_ALLOWED_PROTEINS
        if disallowed:
            errors.append("Vegan profiles can only select plant proteins.")
    if DietaryRule.AVOID_PORK in rules and ProteinPreference.PORK in proteins:
        errors.append("Pork protein conflicts with avoid_pork.")
    if DietaryRule.AVOID_BEEF in rules and ProteinPreference.BEEF in proteins:
        errors.append("Beef protein conflicts with avoid_beef.")
    if DietaryRule.AVOID_SHELLFISH in rules and ProteinPreference.SEAFOOD in proteins:
        errors.append("Seafood protein conflicts with avoid_shellfish.")
    if Allergen.FISH in allergens and ProteinPreference.FISH in proteins:
        errors.append("Fish protein conflicts with fish allergy.")
    if Allergen.CRUSTACEANS in allergens and ProteinPreference.SEAFOOD in proteins:
        errors.append("Seafood protein conflicts with crustaceans allergy.")
    if Allergen.MOLLUSCS in allergens and ProteinPreference.SEAFOOD in proteins:
        errors.append("Seafood protein conflicts with molluscs allergy.")
    if Allergen.EGGS in allergens and ProteinPreference.EGGS in proteins:
        errors.append("Egg protein conflicts with egg allergy.")
    return errors


def _remove_incompatible_proteins(profile: UserProfile) -> None:
    invalid = _invalid_proteins(profile)
    if not invalid:
        return
    profile.protein_preferences = [
        item
        for item in profile.protein_preferences
        if ProteinPreference(item.protein) not in invalid
    ]
    for index, item in enumerate(profile.protein_preferences):
        item.preference_rank = index + 1


def _invalid_proteins(profile: UserProfile) -> set[ProteinPreference]:
    if profile.diet_pattern is None:
        return set()

    diet = DietPattern(profile.diet_pattern)
    proteins = {ProteinPreference(item.protein) for item in profile.protein_preferences}
    allergens = {Allergen(item.allergen) for item in profile.allergens}
    rules = {DietaryRule(item.dietary_rule) for item in profile.dietary_rules}
    invalid: set[ProteinPreference] = set()

    if diet == DietPattern.PESCATARIAN:
        invalid.update(proteins - PESCATARIAN_ALLOWED_PROTEINS)
    if diet == DietPattern.VEGETARIAN:
        invalid.update(proteins - VEGETARIAN_ALLOWED_PROTEINS)
    if diet == DietPattern.VEGAN:
        invalid.update(proteins - VEGAN_ALLOWED_PROTEINS)
    if DietaryRule.AVOID_PORK in rules:
        invalid.add(ProteinPreference.PORK)
    if DietaryRule.AVOID_BEEF in rules:
        invalid.add(ProteinPreference.BEEF)
    if DietaryRule.AVOID_SHELLFISH in rules:
        invalid.add(ProteinPreference.SEAFOOD)
    if Allergen.FISH in allergens:
        invalid.add(ProteinPreference.FISH)
    if Allergen.CRUSTACEANS in allergens or Allergen.MOLLUSCS in allergens:
        invalid.add(ProteinPreference.SEAFOOD)
    if Allergen.EGGS in allergens:
        invalid.add(ProteinPreference.EGGS)
    return proteins & invalid


def _completion_errors(profile: UserProfile) -> list[str]:
    errors: list[str] = []
    if profile.privacy_notice_acknowledged_at is None:
        errors.append("Privacy information has not been acknowledged.")
    if profile.country_code is None:
        errors.append("Country is required.")
    if profile.diet_pattern is None:
        errors.append("Diet pattern is required.")
    if profile.allergy_updated_at is None:
        errors.append("Allergy question must be answered or skipped explicitly.")
    if profile.dietary_rules_updated_at is None:
        errors.append("Dietary rules question must be answered.")
    if profile.cuisine_preference_status == CuisinePreferenceStatus.NOT_PROVIDED.value:
        errors.append("Cuisine preference must be answered.")
    if (
        profile.cuisine_preference_status == CuisinePreferenceStatus.PROVIDED.value
        and not profile.cuisine_preferences
    ):
        errors.append("At least one cuisine area is required.")
    if profile.diet_pattern is not None:
        diet = DietPattern(profile.diet_pattern)
        if diet in PROTEIN_REQUIRED_DIETS and not profile.protein_preferences:
            errors.append("At least one protein preference is required.")
    errors.extend(_protein_errors(profile))
    return errors


def _build_response(profile: UserProfile) -> OnboardingProfileResponse:
    return OnboardingProfileResponse(
        status=OnboardingStatus(profile.onboarding_status),
        next_step=_next_step(profile),
        user_id=profile.user_id,
        country_code=None if profile.country_code is None else CountryCode(profile.country_code),
        region_code=profile.region_code,
        location_source=(
            None if profile.location_source is None else LocationSource(profile.location_source)
        ),
        privacy_notice_version=profile.privacy_notice_version,
        privacy_notice_acknowledged_at=profile.privacy_notice_acknowledged_at,
        diet_pattern=None if profile.diet_pattern is None else DietPattern(profile.diet_pattern),
        allergy_status=AllergyProfileStatus(profile.allergy_status),
        allergens=[Allergen(item.allergen) for item in profile.allergens],
        dietary_rules=[DietaryRule(item.dietary_rule) for item in profile.dietary_rules],
        cuisine_preference_status=CuisinePreferenceStatus(profile.cuisine_preference_status),
        cuisine_areas=[item.area for item in profile.cuisine_preferences],
        proteins=[ProteinPreference(item.protein) for item in profile.protein_preferences],
        completed_at=profile.completed_at,
        updated_at=profile.updated_at,
    )


def _next_step(profile: UserProfile) -> OnboardingStep:
    if profile.onboarding_status == OnboardingStatus.COMPLETED.value:
        return OnboardingStep.COMPLETE
    if profile.privacy_notice_acknowledged_at is None:
        return OnboardingStep.PRIVACY
    if profile.country_code is None:
        return OnboardingStep.LOCATION
    if profile.diet_pattern is None:
        return OnboardingStep.DIET
    if profile.allergy_updated_at is None:
        return OnboardingStep.ALLERGIES
    if profile.dietary_rules_updated_at is None:
        return OnboardingStep.DIETARY_RULES
    if profile.cuisine_preference_status == CuisinePreferenceStatus.NOT_PROVIDED.value:
        return OnboardingStep.CUISINES
    diet = DietPattern(profile.diet_pattern)
    if diet in PROTEIN_REQUIRED_DIETS and not profile.protein_preferences:
        return OnboardingStep.PROTEINS
    return OnboardingStep.REVIEW
