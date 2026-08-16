import uuid
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from enum import StrEnum

from app.data.enums import RecommendationEventType
from app.recommendations.synthetic import (
    InteractionEvent,
    RecipeFeature,
    SyntheticUser,
)

MODEL_FEATURE_COLUMNS: tuple[str, ...] = (
    "month",
    "seasonal_match_count",
    "cuisine_match",
    "user_country",
    "user_diet",
    "recipe_area",
    "recipe_category",
    "user_prior_impressions",
    "user_prior_opens",
    "user_prior_favourites",
    "user_prior_plans",
    "user_recipe_prior_impressions",
    "recipe_prior_impressions",
    "recipe_prior_positive_actions",
)


class DatasetSplit(StrEnum):
    TRAIN = "train"
    VALIDATION = "validation"
    TEST = "test"


@dataclass
class TrainingExample:
    impression_event_id: uuid.UUID
    slate_id: uuid.UUID
    user_id: uuid.UUID
    recipe_id: uuid.UUID
    occurred_at: datetime
    split: DatasetSplit
    is_synthetic: bool
    generator_version: str
    persona_key: str
    position: int
    month: int
    seasonal_match_count: int
    cuisine_match: int
    user_country: str
    user_diet: str
    recipe_area: str
    recipe_category: str
    user_prior_impressions: int
    user_prior_opens: int
    user_prior_favourites: int
    user_prior_plans: int
    user_recipe_prior_impressions: int
    recipe_prior_impressions: int
    recipe_prior_positive_actions: int
    engagement_label: int = 0
    relevance: int = 0


def build_training_examples(
    *,
    users: list[SyntheticUser],
    recipes: list[RecipeFeature],
    events: list[InteractionEvent],
    start_date: date,
    days: int,
    attribution_window: timedelta | None = None,
) -> list[TrainingExample]:
    if days < 3:
        raise ValueError("days must be at least 3")
    resolved_attribution_window = attribution_window or timedelta(hours=24)

    users_by_id = {user.user_id: user for user in users}
    recipes_by_id = {recipe.recipe_id: recipe for recipe in recipes}
    user_event_counts: Counter[tuple[uuid.UUID, RecommendationEventType]] = Counter()
    user_recipe_impressions: Counter[tuple[uuid.UUID, uuid.UUID]] = Counter()
    recipe_impressions: Counter[uuid.UUID] = Counter()
    recipe_positive_actions: Counter[uuid.UUID] = Counter()
    latest_impression_by_user_recipe: dict[tuple[uuid.UUID, uuid.UUID], int] = {}
    latest_impression_by_slate_recipe: dict[tuple[uuid.UUID, uuid.UUID], int] = {}
    slate_impressions_before: dict[uuid.UUID, int] = {}
    examples: list[TrainingExample] = []

    for event in sorted(events, key=lambda item: (item.occurred_at, str(item.event_id))):
        user = users_by_id.get(event.user_id)
        recipe = recipes_by_id.get(event.recipe_id)
        if user is None or recipe is None:
            raise ValueError("Every event must reference a known generated user and recipe")

        if event.event_type == RecommendationEventType.IMPRESSION:
            if event.position is None:
                raise ValueError("Impression events require a feed position")
            if event.slate_id is None:
                raise ValueError("Impression events require a slate identifier")
            impressions_before_slate = slate_impressions_before.setdefault(
                event.slate_id,
                user_event_counts[(event.user_id, RecommendationEventType.IMPRESSION)],
            )
            split = split_for_timestamp(
                occurred_at=event.occurred_at,
                start_date=start_date,
                days=days,
            )
            example = TrainingExample(
                impression_event_id=event.event_id,
                slate_id=event.slate_id,
                user_id=event.user_id,
                recipe_id=event.recipe_id,
                occurred_at=event.occurred_at,
                split=split,
                is_synthetic=event.is_synthetic,
                generator_version=event.generator_version,
                persona_key=user.persona_key,
                position=event.position,
                month=event.occurred_at.month,
                seasonal_match_count=recipe.seasonal_match_counts.get(
                    (user.country_code.value, event.occurred_at.month),
                    0,
                ),
                cuisine_match=_cuisine_match(user, recipe),
                user_country=user.country_code.value,
                user_diet=user.diet_pattern.value,
                recipe_area=recipe.area or "unknown",
                recipe_category=recipe.category or "unknown",
                user_prior_impressions=impressions_before_slate,
                user_prior_opens=user_event_counts[(event.user_id, RecommendationEventType.OPEN)],
                user_prior_favourites=user_event_counts[
                    (event.user_id, RecommendationEventType.FAVOURITE)
                ],
                user_prior_plans=user_event_counts[(event.user_id, RecommendationEventType.PLAN)],
                user_recipe_prior_impressions=user_recipe_impressions[
                    (event.user_id, event.recipe_id)
                ],
                recipe_prior_impressions=recipe_impressions[event.recipe_id],
                recipe_prior_positive_actions=recipe_positive_actions[event.recipe_id],
            )
            examples.append(example)
            latest_impression_by_user_recipe[(event.user_id, event.recipe_id)] = len(examples) - 1
            latest_impression_by_slate_recipe[(event.slate_id, event.recipe_id)] = len(examples) - 1
            user_event_counts[(event.user_id, event.event_type)] += 1
            user_recipe_impressions[(event.user_id, event.recipe_id)] += 1
            recipe_impressions[event.recipe_id] += 1
            continue

        _apply_attributed_label(
            event=event,
            examples=examples,
            latest_impression_by_user_recipe=latest_impression_by_user_recipe,
            latest_impression_by_slate_recipe=latest_impression_by_slate_recipe,
            start_date=start_date,
            days=days,
            attribution_window=resolved_attribution_window,
        )
        user_event_counts[(event.user_id, event.event_type)] += 1
        if event.event_type in {
            RecommendationEventType.OPEN,
            RecommendationEventType.FAVOURITE,
            RecommendationEventType.PLAN,
        }:
            recipe_positive_actions[event.recipe_id] += 1

    return examples


def split_for_timestamp(
    *,
    occurred_at: datetime,
    start_date: date,
    days: int,
) -> DatasetSplit:
    day_offset = (occurred_at.date() - start_date).days
    if not 0 <= day_offset < days:
        raise ValueError("Event timestamp falls outside the configured simulation period")
    train_days = (days * 70) // 100
    validation_days = (days * 15) // 100
    if day_offset < train_days:
        return DatasetSplit.TRAIN
    if day_offset < train_days + validation_days:
        return DatasetSplit.VALIDATION
    return DatasetSplit.TEST


def _apply_attributed_label(
    *,
    event: InteractionEvent,
    examples: list[TrainingExample],
    latest_impression_by_user_recipe: dict[tuple[uuid.UUID, uuid.UUID], int],
    latest_impression_by_slate_recipe: dict[tuple[uuid.UUID, uuid.UUID], int],
    start_date: date,
    days: int,
    attribution_window: timedelta,
) -> None:
    relevance_by_event = {
        RecommendationEventType.OPEN: 1,
        RecommendationEventType.FAVOURITE: 2,
        RecommendationEventType.PLAN: 3,
    }
    relevance = relevance_by_event.get(event.event_type)
    if relevance is None:
        return
    example_index = (
        latest_impression_by_slate_recipe.get((event.slate_id, event.recipe_id))
        if event.slate_id is not None
        else latest_impression_by_user_recipe.get((event.user_id, event.recipe_id))
    )
    if example_index is None:
        return
    example = examples[example_index]
    elapsed = event.occurred_at - example.occurred_at
    if not timedelta(0) <= elapsed <= attribution_window:
        return
    event_split = split_for_timestamp(
        occurred_at=event.occurred_at,
        start_date=start_date,
        days=days,
    )
    if event_split != example.split:
        return
    example.engagement_label = 1
    example.relevance = max(example.relevance, relevance)


def _cuisine_match(user: SyntheticUser, recipe: RecipeFeature) -> int:
    if recipe.area is None:
        return 0
    preferred = {area.casefold() for area in user.preferred_areas}
    return int(recipe.area.casefold() in preferred)
