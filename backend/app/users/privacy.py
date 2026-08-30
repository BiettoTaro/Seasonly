import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    Recipe,
    RecommendationEvent,
    User,
    UserPasswordResetToken,
    UserPlannedMeal,
    UserProfile,
    UserRecipeFavourite,
    UserRecipeHistory,
    UserRefreshToken,
)
from app.schemas.privacy import (
    ConsentExport,
    FavouriteExport,
    PasswordResetRequestExport,
    PlannedMealExport,
    RankedPreferenceExport,
    RecipeHistoryExport,
    RecommendationEventExport,
    RefreshSessionExport,
    UserDataExport,
    UserDataExportAccount,
    UserDataExportProfile,
    UserDataExportRecipeActivity,
    UserDataExportSecurityRecords,
)
from app.users.security import verify_password


class InvalidCurrentPasswordError(ValueError):
    pass


@dataclass(frozen=True)
class UserPrivacyRecords:
    profile: UserProfile | None
    favourites: list[tuple[UserRecipeFavourite, Recipe]]
    history: list[tuple[UserRecipeHistory, Recipe]]
    planned_meals: list[tuple[UserPlannedMeal, Recipe]]
    recommendation_events: list[RecommendationEvent]
    refresh_tokens: list[UserRefreshToken]
    password_reset_tokens: list[UserPasswordResetToken]


async def export_user_data(
    session: AsyncSession,
    *,
    user: User,
    current_password: str,
    exported_at: datetime | None = None,
) -> UserDataExport:
    _require_current_password(user, current_password)
    records = await _load_user_privacy_records(session, user_id=user.id)
    return _build_user_data_export(
        user=user,
        records=records,
        exported_at=exported_at or datetime.now(UTC),
    )


async def delete_user_data(
    session: AsyncSession,
    *,
    user: User,
    current_password: str,
) -> None:
    _require_current_password(user, current_password)
    await session.delete(user)
    await session.commit()


def _require_current_password(user: User, current_password: str) -> None:
    if not verify_password(current_password, user.password_hash):
        raise InvalidCurrentPasswordError("Current password is incorrect")


async def _load_user_privacy_records(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
) -> UserPrivacyRecords:
    profile_result = await session.execute(_user_profile_export_statement(user_id))
    favourites_result = await session.execute(
        select(UserRecipeFavourite, Recipe)
        .join(Recipe, Recipe.id == UserRecipeFavourite.recipe_id)
        .where(UserRecipeFavourite.user_id == user_id)
        .order_by(UserRecipeFavourite.created_at, UserRecipeFavourite.recipe_id)
    )
    history_result = await session.execute(
        select(UserRecipeHistory, Recipe)
        .join(Recipe, Recipe.id == UserRecipeHistory.recipe_id)
        .where(UserRecipeHistory.user_id == user_id)
        .order_by(UserRecipeHistory.viewed_at, UserRecipeHistory.recipe_id)
    )
    planned_meals_result = await session.execute(
        select(UserPlannedMeal, Recipe)
        .join(Recipe, Recipe.id == UserPlannedMeal.recipe_id)
        .where(UserPlannedMeal.user_id == user_id)
        .order_by(UserPlannedMeal.created_at, UserPlannedMeal.id)
    )
    recommendation_events_result = await session.execute(
        select(RecommendationEvent)
        .where(RecommendationEvent.user_id == user_id)
        .order_by(RecommendationEvent.occurred_at, RecommendationEvent.id)
    )
    refresh_tokens_result = await session.execute(
        select(UserRefreshToken)
        .where(UserRefreshToken.user_id == user_id)
        .order_by(UserRefreshToken.created_at, UserRefreshToken.id)
    )
    password_reset_tokens_result = await session.execute(
        select(UserPasswordResetToken)
        .where(UserPasswordResetToken.user_id == user_id)
        .order_by(UserPasswordResetToken.created_at, UserPasswordResetToken.id)
    )
    return UserPrivacyRecords(
        profile=profile_result.scalar_one_or_none(),
        favourites=list(favourites_result.tuples()),
        history=list(history_result.tuples()),
        planned_meals=list(planned_meals_result.tuples()),
        recommendation_events=list(recommendation_events_result.scalars()),
        refresh_tokens=list(refresh_tokens_result.scalars()),
        password_reset_tokens=list(password_reset_tokens_result.scalars()),
    )


def _user_profile_export_statement(user_id: uuid.UUID) -> Select[tuple[UserProfile]]:
    return (
        select(UserProfile)
        .options(
            selectinload(UserProfile.allergens),
            selectinload(UserProfile.dietary_rules),
            selectinload(UserProfile.cuisine_preferences),
            selectinload(UserProfile.protein_preferences),
            selectinload(UserProfile.consents),
        )
        .where(UserProfile.user_id == user_id)
        .execution_options(populate_existing=True)
    )


def _build_user_data_export(
    *,
    user: User,
    records: UserPrivacyRecords,
    exported_at: datetime,
) -> UserDataExport:
    profile = records.profile
    consents = (
        [
            ConsentExport(
                id=consent.id,
                consent_type=consent.consent_type,
                notice_version=consent.notice_version,
                granted_at=consent.granted_at,
                withdrawn_at=consent.withdrawn_at,
            )
            for consent in sorted(
                profile.consents, key=lambda item: (item.granted_at, str(item.id))
            )
        ]
        if profile is not None
        else []
    )
    return UserDataExport(
        format_version="seasonly-user-data-v1",
        exported_at=exported_at,
        account=UserDataExportAccount(
            id=user.id,
            email=user.email,
            is_active=user.is_active,
            is_verified=user.is_verified,
            created_at=user.created_at,
            updated_at=user.updated_at,
            terms_version=user.terms_version,
            terms_accepted_at=user.terms_accepted_at,
        ),
        profile=_profile_export(profile) if profile is not None else None,
        consents=consents,
        recipe_activity=UserDataExportRecipeActivity(
            favourites=[
                FavouriteExport(
                    recipe_id=favourite.recipe_id,
                    recipe_name=recipe.name,
                    created_at=favourite.created_at,
                )
                for favourite, recipe in records.favourites
            ],
            history=[
                RecipeHistoryExport(
                    recipe_id=history.recipe_id,
                    recipe_name=recipe.name,
                    viewed_at=history.viewed_at,
                )
                for history, recipe in records.history
            ],
            planned_meals=[
                PlannedMealExport(
                    id=meal.id,
                    recipe_id=meal.recipe_id,
                    recipe_name=recipe.name,
                    day_of_week=meal.day_of_week,
                    meal_slot=meal.meal_slot,
                    created_at=meal.created_at,
                )
                for meal, recipe in records.planned_meals
            ],
        ),
        recommendation_events=[
            RecommendationEventExport(
                id=event.id,
                recipe_id=event.recipe_id,
                consent_id=event.consent_id,
                event_type=event.event_type,
                source=event.source,
                slate_id=event.slate_id,
                position=event.position,
                occurred_at=event.occurred_at,
                expires_at=event.expires_at,
            )
            for event in records.recommendation_events
        ],
        security_records=UserDataExportSecurityRecords(
            refresh_sessions=[
                RefreshSessionExport(
                    id=token.id,
                    family_id=token.family_id,
                    parent_token_id=token.parent_token_id,
                    created_at=token.created_at,
                    expires_at=token.expires_at,
                    revoked_at=token.revoked_at,
                )
                for token in records.refresh_tokens
            ],
            password_reset_requests=[
                PasswordResetRequestExport(
                    id=token.id,
                    created_at=token.created_at,
                    expires_at=token.expires_at,
                    used_at=token.used_at,
                )
                for token in records.password_reset_tokens
            ],
        ),
    )


def _profile_export(profile: UserProfile) -> UserDataExportProfile:
    return UserDataExportProfile(
        display_name=profile.display_name,
        country_code=profile.country_code,
        region_code=profile.region_code,
        location_source=profile.location_source,
        onboarding_status=profile.onboarding_status,
        privacy_notice_version=profile.privacy_notice_version,
        privacy_notice_acknowledged_at=profile.privacy_notice_acknowledged_at,
        diet_pattern=profile.diet_pattern,
        allergy_status=profile.allergy_status,
        allergens=sorted(item.allergen for item in profile.allergens),
        allergy_updated_at=profile.allergy_updated_at,
        dietary_rules=sorted(item.dietary_rule for item in profile.dietary_rules),
        dietary_rules_updated_at=profile.dietary_rules_updated_at,
        cuisine_preference_status=profile.cuisine_preference_status,
        cuisine_preferences=[
            RankedPreferenceExport(
                value=item.area,
                preference_rank=item.preference_rank,
            )
            for item in sorted(
                profile.cuisine_preferences,
                key=lambda item: (
                    item.preference_rank is None,
                    item.preference_rank or 0,
                    item.area.casefold(),
                ),
            )
        ],
        protein_preferences=[
            RankedPreferenceExport(
                value=item.protein,
                preference_rank=item.preference_rank,
            )
            for item in sorted(
                profile.protein_preferences,
                key=lambda item: (
                    item.preference_rank is None,
                    item.preference_rank or 0,
                    item.protein.casefold(),
                ),
            )
        ],
        completed_at=profile.completed_at,
        updated_at=profile.updated_at,
    )
