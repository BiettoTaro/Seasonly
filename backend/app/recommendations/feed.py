import uuid
from collections import defaultdict
from collections.abc import Iterable, Sequence
from datetime import UTC, datetime

from sqlalchemy import func, select
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
from app.models import Recipe, RecommendationEvent, User
from app.recipes.service import (
    SeasonalRecipeCandidate,
    load_active_recipe_content,
    load_eligible_seasonal_recipe_candidates,
)
from app.recommendations.content_ranker import (
    ContentRankingCandidate,
    RecipeSignal,
    rank_content_candidates,
)
from app.recommendations.events import personalization_consent_is_active
from app.schemas.recipe import SeasonalRecipeResponse
from app.schemas.recommendation import RecommendationFeedResponse

EVENT_SIGNAL_WEIGHTS: dict[RecommendationEventType, float] = {
    RecommendationEventType.OPEN: 1.0,
    RecommendationEventType.FAVOURITE: 2.0,
    RecommendationEventType.UNFAVOURITE: -2.0,
    RecommendationEventType.PLAN: 3.0,
    RecommendationEventType.UNPLAN: -3.0,
}


class RecommendationProfileError(ValueError):
    pass


async def build_recommendation_feed(
    session: AsyncSession,
    *,
    user: User,
    month: Month,
    limit: int,
    ranking_mode: RecommendationRankingStrategy,
    now: datetime | None = None,
) -> RecommendationFeedResponse:
    if not 1 <= limit <= 100:
        raise ValueError("Recommendation feed limit must be between 1 and 100")
    country_code = _profile_country_code(user)
    candidates = await load_eligible_seasonal_recipe_candidates(
        session,
        country_code=country_code,
        month=month,
        excluded_allergens=_profile_allergens(user),
        diet_pattern=_profile_diet(user),
        dietary_rules=_profile_dietary_rules(user),
    )
    if not candidates:
        return _feed_response(
            country_code=country_code,
            month=month,
            ranking_strategy=ranking_mode,
            personalized=False,
            total=0,
            items=[],
        )
    if ranking_mode is RecommendationRankingStrategy.SEASONAL_ONLY_V1:
        ranked_candidates = _rank_seasonal_candidates(candidates)
        return _feed_response(
            country_code=country_code,
            month=month,
            ranking_strategy=ranking_mode,
            personalized=False,
            total=len(candidates),
            items=[candidate.recipe for candidate in ranked_candidates[:limit]],
        )
    personalization_active = await personalization_consent_is_active(
        session,
        user_id=user.id,
    )
    recipes = await load_active_recipe_content(session)
    signals = (
        await _load_user_recipe_signals(
            session,
            user_id=user.id,
            now=now or datetime.now(UTC),
        )
        if personalization_active
        else []
    )
    preferred_areas = _profile_preferred_areas(user) if personalization_active else frozenset[str]()
    ranked = rank_content_candidates(
        recipes=recipes,
        candidates=[
            ContentRankingCandidate(
                recipe_id=candidate.recipe.id,
                seasonal_match_count=candidate.recipe.matched_seasonal_produce_count,
                cuisine_match=int(
                    candidate.recipe.area is not None
                    and candidate.recipe.area.casefold() in preferred_areas
                ),
            )
            for candidate in candidates
        ],
        signals=signals,
    )
    candidates_by_id = {candidate.recipe.id: candidate.recipe for candidate in candidates}
    return _feed_response(
        country_code=country_code,
        month=month,
        ranking_strategy=ranking_mode,
        personalized=bool(signals or preferred_areas),
        total=len(candidates),
        items=[candidates_by_id[item.recipe_id] for item in ranked[:limit]],
    )


def _rank_seasonal_candidates(
    candidates: Sequence[SeasonalRecipeCandidate],
) -> list[SeasonalRecipeCandidate]:
    return sorted(
        candidates,
        key=lambda candidate: (
            -candidate.recipe.matched_seasonal_produce_count,
            str(candidate.recipe.id),
        ),
    )


def _feed_response(
    *,
    country_code: CountryCode,
    month: Month,
    ranking_strategy: RecommendationRankingStrategy,
    personalized: bool,
    total: int,
    items: list[SeasonalRecipeResponse],
) -> RecommendationFeedResponse:
    return RecommendationFeedResponse(
        slate_id=uuid.uuid4(),
        country_code=country_code,
        month=month,
        ranking_strategy=ranking_strategy,
        personalized=personalized,
        total=total,
        items=items,
    )


async def _load_user_recipe_signals(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    now: datetime,
) -> list[RecipeSignal]:
    result = await session.execute(
        select(
            RecommendationEvent.recipe_id,
            RecommendationEvent.event_type,
            func.count(RecommendationEvent.id),
        )
        .join(Recipe, Recipe.id == RecommendationEvent.recipe_id)
        .where(
            RecommendationEvent.user_id == user_id,
            RecommendationEvent.expires_at > now,
            RecommendationEvent.event_type.in_(
                [event_type.value for event_type in EVENT_SIGNAL_WEIGHTS]
            ),
            Recipe.is_active.is_(True),
        )
        .group_by(
            RecommendationEvent.recipe_id,
            RecommendationEvent.event_type,
        )
    )
    event_counts = result.tuples().all()
    return recipe_signals_from_event_counts(event_counts)


def recipe_signals_from_event_counts(
    event_counts: Iterable[tuple[uuid.UUID, str, int]],
) -> list[RecipeSignal]:
    weights: defaultdict[uuid.UUID, float] = defaultdict(float)
    for recipe_id, raw_event_type, count in event_counts:
        if count < 1:
            raise ValueError("Recommendation event count must be positive")
        try:
            event_type = RecommendationEventType(raw_event_type)
        except ValueError as e:
            raise ValueError(f"Unsupported recommendation event type {raw_event_type}") from e
        event_weight = EVENT_SIGNAL_WEIGHTS.get(event_type)
        if event_weight is None:
            raise ValueError(
                f"Recommendation event type {event_type.value} is not a profile signal"
            )
        weights[recipe_id] += event_weight * count
    return [
        RecipeSignal(recipe_id=recipe_id, weight=weight)
        for recipe_id, weight in sorted(weights.items(), key=lambda item: str(item[0]))
        if weight > 0
    ]


def _profile_country_code(user: User) -> CountryCode:
    if user.profile is None or user.profile.country_code is None:
        raise RecommendationProfileError(
            "A supported profile country is required for recommendations"
        )
    try:
        return CountryCode(user.profile.country_code)
    except ValueError as e:
        raise RecommendationProfileError(
            "A supported profile country is required for recommendations"
        ) from e


def _profile_allergens(user: User) -> set[Allergen]:
    if user.profile is None or user.profile.allergy_status != AllergyProfileStatus.PROVIDED.value:
        return set()
    return {Allergen(item.allergen) for item in user.profile.allergens}


def _profile_diet(user: User) -> DietPattern | None:
    if user.profile is None or user.profile.diet_pattern is None:
        return None
    return DietPattern(user.profile.diet_pattern)


def _profile_dietary_rules(user: User) -> set[DietaryRule]:
    if user.profile is None:
        return set()
    return {DietaryRule(item.dietary_rule) for item in user.profile.dietary_rules}


def _profile_preferred_areas(user: User) -> frozenset[str]:
    if (
        user.profile is None
        or user.profile.cuisine_preference_status != CuisinePreferenceStatus.PROVIDED.value
    ):
        return frozenset()
    return frozenset(item.area.casefold() for item in user.profile.cuisine_preferences)
