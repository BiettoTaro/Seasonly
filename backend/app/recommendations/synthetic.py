import random
import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta

from app.data.enums import (
    Allergen,
    AllergenAssessmentStatus,
    CountryCode,
    DietPattern,
    RecommendationEventSource,
    RecommendationEventType,
)
from app.data.synthetic import SYNTHETIC_PERSONAS, PersonaDefinition
from app.recipes.dietary import (
    diet_excluded_terms,
    dietary_rule_excluded_terms,
    ingredient_names_contain_terms,
)

SYNTHETIC_GENERATOR_VERSION = "persona-simulation-v2"
SYNTHETIC_UUID_NAMESPACE = uuid.UUID("f71248e7-4434-4bf3-bbed-4896621a644b")
COLD_START_PERSONA_KEY = "cold_start_newcomer"


@dataclass(frozen=True)
class RecipeFeature:
    recipe_id: uuid.UUID
    name: str
    area: str | None
    category: str | None
    ingredient_names: tuple[str, ...]
    seasonal_match_counts: dict[tuple[str, int], int]
    allergen_statuses: dict[str, str]


@dataclass(frozen=True)
class SyntheticUser:
    user_id: uuid.UUID
    persona_key: str
    country_code: CountryCode
    diet_pattern: DietPattern
    preferred_areas: tuple[str, ...]
    allergens: tuple[Allergen, ...]
    joined_on: date


@dataclass(frozen=True)
class InteractionEvent:
    event_id: uuid.UUID
    slate_id: uuid.UUID | None
    user_id: uuid.UUID
    recipe_id: uuid.UUID
    event_type: RecommendationEventType
    source: RecommendationEventSource
    position: int | None
    occurred_at: datetime
    is_synthetic: bool
    generator_version: str


def generate_synthetic_users(
    *,
    user_count: int,
    start_date: date,
    days: int,
    seed: int,
) -> list[SyntheticUser]:
    if user_count < len(SYNTHETIC_PERSONAS):
        raise ValueError(
            f"user_count must be at least {len(SYNTHETIC_PERSONAS)} so every persona is represented"
        )
    if days < 3:
        raise ValueError("days must be at least 3")

    rng = random.Random(seed)
    persona_assignments = [
        SYNTHETIC_PERSONAS[index % len(SYNTHETIC_PERSONAS)] for index in range(user_count)
    ]
    rng.shuffle(persona_assignments)

    users: list[SyntheticUser] = []
    for index, persona in enumerate(persona_assignments):
        joined_on = (
            start_date + timedelta(days=rng.randrange(max(days - 14, 1), days))
            if persona.key == COLD_START_PERSONA_KEY
            else start_date - timedelta(days=rng.randrange(0, 181))
        )
        users.append(
            SyntheticUser(
                user_id=uuid.uuid5(
                    SYNTHETIC_UUID_NAMESPACE,
                    f"{seed}:user:{index}",
                ),
                persona_key=persona.key,
                country_code=rng.choice(persona.countries),
                diet_pattern=persona.diet_pattern,
                preferred_areas=persona.preferred_areas,
                allergens=persona.allergens,
                joined_on=joined_on,
            )
        )
    return users


def generate_cold_start_users(
    *,
    user_count: int,
    start_date: date,
    days: int,
    seed: int,
) -> list[SyntheticUser]:
    if user_count < days:
        raise ValueError("user_count must be at least days so every evaluation date is covered")
    if days < 3:
        raise ValueError("days must be at least 3")

    persona = next(
        (item for item in SYNTHETIC_PERSONAS if item.key == COLD_START_PERSONA_KEY),
        None,
    )
    if persona is None:
        raise ValueError(f"Synthetic persona {COLD_START_PERSONA_KEY} is not configured")

    rng = random.Random(seed)
    joined_day_offsets = [index % days for index in range(user_count)]
    rng.shuffle(joined_day_offsets)
    return [
        SyntheticUser(
            user_id=uuid.uuid5(
                SYNTHETIC_UUID_NAMESPACE,
                f"{seed}:cold-start-user:{index}",
            ),
            persona_key=persona.key,
            country_code=rng.choice(persona.countries),
            diet_pattern=persona.diet_pattern,
            preferred_areas=persona.preferred_areas,
            allergens=persona.allergens,
            joined_on=start_date + timedelta(days=joined_day_offsets[index]),
        )
        for index in range(user_count)
    ]


def simulate_interactions(
    *,
    users: list[SyntheticUser],
    recipes: list[RecipeFeature],
    start_date: date,
    days: int,
    seed: int,
    feed_size: int = 10,
    initial_session_only: bool = False,
) -> list[InteractionEvent]:
    if not recipes:
        raise ValueError("At least one actual Seasonly recipe is required")
    if days < 3:
        raise ValueError("days must be at least 3")
    if not 1 <= feed_size <= 100:
        raise ValueError("feed_size must be between 1 and 100")

    rng = random.Random(seed)
    personas_by_key = {persona.key: persona for persona in SYNTHETIC_PERSONAS}
    seen_recipes: dict[uuid.UUID, set[uuid.UUID]] = {user.user_id: set() for user in users}
    factory = _EventFactory(seed=seed)
    events: list[InteractionEvent] = []
    simulation_end = start_date + timedelta(days=days)

    for day_offset in range(days):
        current_date = start_date + timedelta(days=day_offset)
        for user in users:
            if current_date < user.joined_on:
                continue
            persona = personas_by_key[user.persona_key]
            if initial_session_only and current_date != user.joined_on:
                continue
            if not initial_session_only and rng.random() > persona.activity_probability:
                continue

            eligible = [
                recipe
                for recipe in recipes
                if recipe_is_eligible(
                    recipe=recipe,
                    user=user,
                    persona=persona,
                    month=current_date.month,
                )
            ]
            if not eligible:
                continue

            selected = _weighted_sample_without_replacement(
                rng,
                eligible,
                weights=[
                    _recipe_affinity(
                        recipe=recipe,
                        user=user,
                        persona=persona,
                        month=current_date.month,
                        seen_recipe_ids=seen_recipes[user.user_id],
                    )
                    for recipe in eligible
                ],
                count=min(feed_size, len(eligible)),
            )
            slate_id = uuid.uuid5(
                SYNTHETIC_UUID_NAMESPACE,
                f"{seed}:slate:{user.user_id}:{current_date.isoformat()}",
            )
            feed_time = datetime.combine(
                current_date,
                time(hour=18),
                tzinfo=UTC,
            ) + timedelta(minutes=rng.randrange(0, 90))
            for position, recipe in enumerate(selected, start=1):
                affinity = _normalized_affinity(
                    recipe=recipe,
                    user=user,
                    persona=persona,
                    month=current_date.month,
                )
                events.append(
                    factory.create(
                        slate_id=slate_id,
                        user_id=user.user_id,
                        recipe_id=recipe.recipe_id,
                        event_type=RecommendationEventType.IMPRESSION,
                        source=RecommendationEventSource.SEASONAL_FEED,
                        position=position,
                        occurred_at=feed_time + timedelta(seconds=position),
                    )
                )
                seen_recipes[user.user_id].add(recipe.recipe_id)

                position_factor = max(0.45, 1.0 - ((position - 1) * 0.06))
                open_probability = _clamp_probability(
                    (persona.open_probability * position_factor) + (0.18 * affinity)
                )
                if rng.random() > open_probability:
                    continue

                open_time = feed_time + timedelta(minutes=rng.randrange(2, 46))
                events.append(
                    factory.create(
                        slate_id=slate_id,
                        user_id=user.user_id,
                        recipe_id=recipe.recipe_id,
                        event_type=RecommendationEventType.OPEN,
                        source=RecommendationEventSource.RECIPE_DETAIL,
                        position=None,
                        occurred_at=open_time,
                    )
                )
                favourite_probability = _clamp_probability(
                    persona.favourite_probability + (0.20 * affinity)
                )
                if rng.random() > favourite_probability:
                    continue

                favourite_time = open_time + timedelta(minutes=rng.randrange(1, 16))
                events.append(
                    factory.create(
                        slate_id=slate_id,
                        user_id=user.user_id,
                        recipe_id=recipe.recipe_id,
                        event_type=RecommendationEventType.FAVOURITE,
                        source=RecommendationEventSource.RECIPE_DETAIL,
                        position=None,
                        occurred_at=favourite_time,
                    )
                )
                if rng.random() < 0.05:
                    _append_future_event(
                        events=events,
                        factory=factory,
                        slate_id=slate_id,
                        user=user,
                        recipe=recipe,
                        event_type=RecommendationEventType.UNFAVOURITE,
                        source=RecommendationEventSource.RECIPE_DETAIL,
                        after=favourite_time,
                        simulation_end=simulation_end,
                        rng=rng,
                    )

                plan_probability = _clamp_probability(persona.plan_probability + (0.12 * affinity))
                if rng.random() > plan_probability:
                    continue
                plan_time = favourite_time + timedelta(minutes=rng.randrange(1, 31))
                events.append(
                    factory.create(
                        slate_id=slate_id,
                        user_id=user.user_id,
                        recipe_id=recipe.recipe_id,
                        event_type=RecommendationEventType.PLAN,
                        source=RecommendationEventSource.RECIPE_DETAIL,
                        position=None,
                        occurred_at=plan_time,
                    )
                )
                if rng.random() < 0.08:
                    _append_future_event(
                        events=events,
                        factory=factory,
                        slate_id=slate_id,
                        user=user,
                        recipe=recipe,
                        event_type=RecommendationEventType.UNPLAN,
                        source=RecommendationEventSource.PLANNER,
                        after=plan_time,
                        simulation_end=simulation_end,
                        rng=rng,
                    )

    return sorted(events, key=lambda event: (event.occurred_at, str(event.event_id)))


def recipe_is_eligible(
    *,
    recipe: RecipeFeature,
    user: SyntheticUser,
    persona: PersonaDefinition,
    month: int,
) -> bool:
    if recipe.seasonal_match_counts.get((user.country_code.value, month), 0) < 1:
        return False
    excluded_terms = diet_excluded_terms(user.diet_pattern)
    excluded_terms.update(dietary_rule_excluded_terms(persona.dietary_rules))
    if ingredient_names_contain_terms(recipe.ingredient_names, excluded_terms):
        return False
    return all(
        recipe.allergen_statuses.get(allergen.value)
        == AllergenAssessmentStatus.DOES_NOT_CONTAIN.value
        for allergen in user.allergens
    )


def _recipe_affinity(
    *,
    recipe: RecipeFeature,
    user: SyntheticUser,
    persona: PersonaDefinition,
    month: int,
    seen_recipe_ids: set[uuid.UUID],
) -> float:
    affinity = 1.0 + (0.30 * recipe.seasonal_match_counts[(user.country_code.value, month)])
    if _cuisine_matches(recipe, user):
        affinity += 1.8
    affinity += (
        persona.variety_preference
        if recipe.recipe_id not in seen_recipe_ids
        else (1.0 - persona.variety_preference) * 0.7
    )
    return max(affinity, 0.01)


def _normalized_affinity(
    *,
    recipe: RecipeFeature,
    user: SyntheticUser,
    persona: PersonaDefinition,
    month: int,
) -> float:
    seasonal = min(
        recipe.seasonal_match_counts[(user.country_code.value, month)] / 4.0,
        1.0,
    )
    cuisine = 1.0 if _cuisine_matches(recipe, user) else 0.0
    return min((seasonal * 0.45) + (cuisine * 0.45) + (persona.variety_preference * 0.10), 1.0)


def _cuisine_matches(recipe: RecipeFeature, user: SyntheticUser) -> bool:
    if recipe.area is None:
        return False
    preferred = {area.casefold() for area in user.preferred_areas}
    return recipe.area.casefold() in preferred


def _weighted_sample_without_replacement[T](
    rng: random.Random,
    values: list[T],
    *,
    weights: list[float],
    count: int,
) -> list[T]:
    if len(values) != len(weights):
        raise ValueError("values and weights must have matching lengths")
    remaining = list(zip(values, weights, strict=True))
    selected: list[T] = []
    for _ in range(count):
        index = rng.choices(
            range(len(remaining)),
            weights=[weight for _, weight in remaining],
            k=1,
        )[0]
        value, _ = remaining.pop(index)
        selected.append(value)
    return selected


def _append_future_event(
    *,
    events: list[InteractionEvent],
    factory: "_EventFactory",
    slate_id: uuid.UUID,
    user: SyntheticUser,
    recipe: RecipeFeature,
    event_type: RecommendationEventType,
    source: RecommendationEventSource,
    after: datetime,
    simulation_end: date,
    rng: random.Random,
) -> None:
    occurred_at = after + timedelta(days=rng.randrange(1, 15))
    if occurred_at.date() >= simulation_end:
        return
    events.append(
        factory.create(
            slate_id=slate_id,
            user_id=user.user_id,
            recipe_id=recipe.recipe_id,
            event_type=event_type,
            source=source,
            position=None,
            occurred_at=occurred_at,
        )
    )


def _clamp_probability(value: float) -> float:
    return min(max(value, 0.0), 1.0)


class _EventFactory:
    def __init__(self, *, seed: int) -> None:
        self._seed: int = seed
        self._sequence: int = 0

    def create(
        self,
        *,
        slate_id: uuid.UUID | None,
        user_id: uuid.UUID,
        recipe_id: uuid.UUID,
        event_type: RecommendationEventType,
        source: RecommendationEventSource,
        position: int | None,
        occurred_at: datetime,
    ) -> InteractionEvent:
        event = InteractionEvent(
            event_id=uuid.uuid5(
                SYNTHETIC_UUID_NAMESPACE,
                f"{self._seed}:event:{self._sequence}",
            ),
            slate_id=slate_id,
            user_id=user_id,
            recipe_id=recipe_id,
            event_type=event_type,
            source=source,
            position=position,
            occurred_at=occurred_at,
            is_synthetic=True,
            generator_version=SYNTHETIC_GENERATOR_VERSION,
        )
        self._sequence += 1
        return event
