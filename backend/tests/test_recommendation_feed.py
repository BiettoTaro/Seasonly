import uuid
from datetime import UTC, datetime
from typing import cast

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.data.enums import (
    Allergen,
    AllergyProfileStatus,
    CountryCode,
    CuisinePreferenceStatus,
    DietaryRule,
    DietPattern,
    Month,
    RecommendationEventType,
    RecommendationRankingStrategy,
)
from app.models import (
    User,
    UserAllergen,
    UserCuisinePreference,
    UserDietaryRule,
    UserProfile,
)
from app.recipes.service import SeasonalRecipeCandidate
from app.recommendations import feed as recommendation_feed
from app.recommendations.content_ranker import RecipeSignal
from app.recommendations.ranking_types import RecipeContent
from app.schemas.recipe import SeasonalRecipeResponse


def recipe_id(sequence: int) -> uuid.UUID:
    return uuid.UUID(f"00000000-0000-0000-0000-{sequence:012d}")


def user_with_profile() -> User:
    user_id = uuid.UUID("10000000-0000-0000-0000-000000000001")
    user = User(
        id=user_id,
        email="user@example.com",
        password_hash="unused",
        is_active=True,
        is_verified=False,
        created_at=datetime(2026, 7, 24, tzinfo=UTC),
        updated_at=datetime(2026, 7, 24, tzinfo=UTC),
    )
    user.profile = UserProfile(
        user_id=user_id,
        country_code=CountryCode.UNITED_KINGDOM.value,
        diet_pattern=DietPattern.PESCATARIAN.value,
        allergy_status=AllergyProfileStatus.PROVIDED.value,
        cuisine_preference_status=CuisinePreferenceStatus.PROVIDED.value,
    )
    profile = user.profile
    assert profile is not None
    profile.allergens = [UserAllergen(user_id=user_id, allergen=Allergen.PEANUTS.value)]
    profile.dietary_rules = [
        UserDietaryRule(
            user_id=user_id,
            dietary_rule=DietaryRule.AVOID_BEEF.value,
        )
    ]
    profile.cuisine_preferences = [
        UserCuisinePreference(
            user_id=user_id,
            area="Italian",
            preference_rank=1,
        )
    ]
    return user


def candidate(
    sequence: int,
    *,
    area: str,
    ingredients: tuple[str, ...],
    seasonal_matches: int = 1,
) -> tuple[SeasonalRecipeCandidate, RecipeContent]:
    identifier = recipe_id(sequence)
    return (
        SeasonalRecipeCandidate(
            recipe=SeasonalRecipeResponse(
                id=identifier,
                name=f"Recipe {sequence}",
                category="Main",
                area=area,
                country_of_origin=None,
                thumbnail_url=None,
                instructions="Cook it.",
                matched_seasonal_produce=["tomato"],
                matched_seasonal_produce_count=seasonal_matches,
            )
        ),
        RecipeContent(
            recipe_id=identifier,
            name=f"Recipe {sequence}",
            area=area,
            category="Main",
            ingredient_names=ingredients,
        ),
    )


@pytest.mark.asyncio
async def test_feed_without_consent_uses_no_history_or_cuisine(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    weak_candidate, weak_content = candidate(
        10,
        area="Italian",
        ingredients=("tomato",),
        seasonal_matches=1,
    )
    strong_candidate, strong_content = candidate(
        11,
        area="British",
        ingredients=("potato",),
        seasonal_matches=3,
    )

    async def load_candidates(
        session: AsyncSession,
        **kwargs: object,
    ) -> list[SeasonalRecipeCandidate]:
        _ = session
        assert kwargs["excluded_allergens"] == {Allergen.PEANUTS}
        assert kwargs["diet_pattern"] == DietPattern.PESCATARIAN
        assert kwargs["dietary_rules"] == {DietaryRule.AVOID_BEEF}
        return [weak_candidate, strong_candidate]

    async def no_consent(session: AsyncSession, *, user_id: uuid.UUID) -> bool:
        _ = session, user_id
        return False

    async def load_content(session: AsyncSession) -> list[RecipeContent]:
        _ = session
        return [weak_content, strong_content]

    async def reject_history(
        session: AsyncSession,
        *,
        user_id: uuid.UUID,
        now: datetime,
    ) -> list[RecipeSignal]:
        _ = session, user_id, now
        raise AssertionError("History must not be read without active consent")

    monkeypatch.setattr(
        recommendation_feed,
        "load_eligible_seasonal_recipe_candidates",
        load_candidates,
    )
    monkeypatch.setattr(
        recommendation_feed,
        "personalization_consent_is_active",
        no_consent,
    )
    monkeypatch.setattr(recommendation_feed, "load_active_recipe_content", load_content)
    monkeypatch.setattr(recommendation_feed, "_load_user_recipe_signals", reject_history)

    result = await recommendation_feed.build_recommendation_feed(
        cast(AsyncSession, object()),
        user=user_with_profile(),
        month=Month.JULY,
        limit=2,
        ranking_mode=RecommendationRankingStrategy.SEASONAL_TFIDF_V1,
    )

    assert result.personalized is False
    assert [item.id for item in result.items] == [
        strong_candidate.recipe.id,
        weak_candidate.recipe.id,
    ]


@pytest.mark.asyncio
async def test_consented_history_and_cuisine_personalize_safe_candidates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    liked_candidate, liked_content = candidate(
        10,
        area="Italian",
        ingredients=("tomato", "basil", "pasta"),
    )
    similar_candidate, similar_content = candidate(
        11,
        area="Italian",
        ingredients=("tomato", "basil"),
    )
    different_candidate, different_content = candidate(
        12,
        area="Japanese",
        ingredients=("salmon", "miso"),
    )

    async def load_candidates(
        session: AsyncSession,
        **kwargs: object,
    ) -> list[SeasonalRecipeCandidate]:
        _ = session, kwargs
        return [similar_candidate, different_candidate]

    async def active_consent(session: AsyncSession, *, user_id: uuid.UUID) -> bool:
        _ = session, user_id
        return True

    async def load_content(session: AsyncSession) -> list[RecipeContent]:
        _ = session
        return [liked_content, similar_content, different_content]

    async def load_history(
        session: AsyncSession,
        *,
        user_id: uuid.UUID,
        now: datetime,
    ) -> list[RecipeSignal]:
        _ = session, user_id, now
        return [RecipeSignal(recipe_id=liked_candidate.recipe.id, weight=3.0)]

    monkeypatch.setattr(
        recommendation_feed,
        "load_eligible_seasonal_recipe_candidates",
        load_candidates,
    )
    monkeypatch.setattr(
        recommendation_feed,
        "personalization_consent_is_active",
        active_consent,
    )
    monkeypatch.setattr(recommendation_feed, "load_active_recipe_content", load_content)
    monkeypatch.setattr(recommendation_feed, "_load_user_recipe_signals", load_history)

    result = await recommendation_feed.build_recommendation_feed(
        cast(AsyncSession, object()),
        user=user_with_profile(),
        month=Month.JULY,
        limit=2,
        ranking_mode=RecommendationRankingStrategy.SEASONAL_TFIDF_V1,
    )

    assert result.personalized is True
    assert [item.id for item in result.items] == [
        similar_candidate.recipe.id,
        different_candidate.recipe.id,
    ]


def test_event_signals_apply_removal_events_and_drop_non_positive_weights() -> None:
    kept_recipe = recipe_id(10)
    removed_recipe = recipe_id(11)

    signals = recommendation_feed.recipe_signals_from_event_counts(
        [
            (kept_recipe, RecommendationEventType.OPEN.value, 2),
            (kept_recipe, RecommendationEventType.FAVOURITE.value, 1),
            (removed_recipe, RecommendationEventType.FAVOURITE.value, 1),
            (removed_recipe, RecommendationEventType.UNFAVOURITE.value, 1),
        ]
    )

    assert signals == [RecipeSignal(recipe_id=kept_recipe, weight=4.0)]


@pytest.mark.asyncio
async def test_feed_requires_supported_profile_country() -> None:
    user = user_with_profile()
    assert user.profile is not None
    user.profile.country_code = None

    with pytest.raises(
        recommendation_feed.RecommendationProfileError,
        match="supported profile country",
    ):
        _ = await recommendation_feed.build_recommendation_feed(
            cast(AsyncSession, object()),
            user=user,
            month=Month.JULY,
            limit=24,
            ranking_mode=RecommendationRankingStrategy.SEASONAL_TFIDF_V1,
        )


@pytest.mark.asyncio
async def test_seasonal_rollback_keeps_safety_filter_and_skips_personalization(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    weak_candidate, _ = candidate(
        10,
        area="Italian",
        ingredients=("tomato",),
        seasonal_matches=1,
    )
    strong_candidate, _ = candidate(
        11,
        area="British",
        ingredients=("potato",),
        seasonal_matches=3,
    )

    async def load_candidates(
        session: AsyncSession,
        **kwargs: object,
    ) -> list[SeasonalRecipeCandidate]:
        _ = session
        assert kwargs["excluded_allergens"] == {Allergen.PEANUTS}
        assert kwargs["diet_pattern"] == DietPattern.PESCATARIAN
        assert kwargs["dietary_rules"] == {DietaryRule.AVOID_BEEF}
        return [weak_candidate, strong_candidate]

    async def reject_query(*args: object, **kwargs: object) -> None:
        _ = args, kwargs
        raise AssertionError("Rollback mode must not read personalization data")

    monkeypatch.setattr(
        recommendation_feed,
        "load_eligible_seasonal_recipe_candidates",
        load_candidates,
    )
    monkeypatch.setattr(
        recommendation_feed,
        "personalization_consent_is_active",
        reject_query,
    )
    monkeypatch.setattr(recommendation_feed, "load_active_recipe_content", reject_query)
    monkeypatch.setattr(recommendation_feed, "_load_user_recipe_signals", reject_query)

    result = await recommendation_feed.build_recommendation_feed(
        cast(AsyncSession, object()),
        user=user_with_profile(),
        month=Month.JULY,
        limit=2,
        ranking_mode=RecommendationRankingStrategy.SEASONAL_ONLY_V1,
    )

    assert result.ranking_strategy is RecommendationRankingStrategy.SEASONAL_ONLY_V1
    assert result.personalized is False
    assert [item.id for item in result.items] == [
        strong_candidate.recipe.id,
        weak_candidate.recipe.id,
    ]
