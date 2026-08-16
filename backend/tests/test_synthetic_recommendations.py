import uuid
from datetime import UTC, date, datetime, timedelta

from app.data.enums import (
    Allergen,
    AllergenAssessmentStatus,
    CountryCode,
    DietPattern,
    RecommendationEventSource,
    RecommendationEventType,
)
from app.data.synthetic import SYNTHETIC_PERSONAS
from app.recommendations.preprocessing import (
    MODEL_FEATURE_COLUMNS,
    DatasetSplit,
    build_training_examples,
    split_for_timestamp,
)
from app.recommendations.synthetic import (
    COLD_START_PERSONA_KEY,
    SYNTHETIC_GENERATOR_VERSION,
    InteractionEvent,
    RecipeFeature,
    SyntheticUser,
    generate_cold_start_users,
    generate_synthetic_users,
    recipe_is_eligible,
    simulate_interactions,
)

START_DATE = date(2026, 4, 26)
TEST_SLATE_ID = uuid.UUID("00000000-0000-0000-0000-000000000030")
SECOND_TEST_SLATE_ID = uuid.UUID("00000000-0000-0000-0000-000000000031")


def recipe_feature(
    *,
    allergen_status: str = AllergenAssessmentStatus.DOES_NOT_CONTAIN.value,
    recipe_id: uuid.UUID | None = None,
) -> RecipeFeature:
    return RecipeFeature(
        recipe_id=recipe_id or uuid.UUID("00000000-0000-0000-0000-000000000010"),
        name="Seasonal Test Bowl",
        area="Italian",
        category="Vegetarian",
        ingredient_names=("tomato", "rice"),
        seasonal_match_counts={
            (country.value, month): 2 for country in CountryCode for month in range(1, 13)
        },
        allergen_statuses={Allergen.PEANUTS.value: allergen_status},
    )


def synthetic_user(*, allergens: tuple[Allergen, ...] = ()) -> SyntheticUser:
    return SyntheticUser(
        user_id=uuid.UUID("00000000-0000-0000-0000-000000000020"),
        persona_key="seasonal_explorer",
        country_code=CountryCode.UNITED_KINGDOM,
        diet_pattern=DietPattern.OMNIVORE,
        preferred_areas=("Italian",),
        allergens=allergens,
        joined_on=START_DATE,
    )


def interaction_event(
    *,
    sequence: int,
    event_type: RecommendationEventType,
    occurred_at: datetime,
    position: int | None = None,
    recipe_id: uuid.UUID | None = None,
    slate_id: uuid.UUID | None = TEST_SLATE_ID,
) -> InteractionEvent:
    return InteractionEvent(
        event_id=uuid.UUID(f"00000000-0000-0000-0000-{sequence:012d}"),
        slate_id=slate_id,
        user_id=synthetic_user().user_id,
        recipe_id=recipe_id or recipe_feature().recipe_id,
        event_type=event_type,
        source=(
            RecommendationEventSource.SEASONAL_FEED
            if event_type == RecommendationEventType.IMPRESSION
            else RecommendationEventSource.RECIPE_DETAIL
        ),
        position=position,
        occurred_at=occurred_at,
        is_synthetic=True,
        generator_version=SYNTHETIC_GENERATOR_VERSION,
    )


def test_persona_catalog_contains_twelve_adult_archetypes() -> None:
    assert len(SYNTHETIC_PERSONAS) == 12
    assert len({persona.key for persona in SYNTHETIC_PERSONAS}) == 12
    assert any("Adult" in persona.label for persona in SYNTHETIC_PERSONAS)


def test_five_hundred_users_are_deterministic_and_cover_every_persona() -> None:
    first = generate_synthetic_users(
        user_count=500,
        start_date=START_DATE,
        days=90,
        seed=20_260_724,
    )
    second = generate_synthetic_users(
        user_count=500,
        start_date=START_DATE,
        days=90,
        seed=20_260_724,
    )

    assert first == second
    assert len(first) == 500
    assert {user.persona_key for user in first} == {persona.key for persona in SYNTHETIC_PERSONAS}


def test_cold_start_evaluation_users_are_deterministic_and_cover_every_date() -> None:
    first = generate_cold_start_users(
        user_count=60,
        start_date=START_DATE,
        days=30,
        seed=20_260_725,
    )
    second = generate_cold_start_users(
        user_count=60,
        start_date=START_DATE,
        days=30,
        seed=20_260_725,
    )

    assert first == second
    assert {user.persona_key for user in first} == {COLD_START_PERSONA_KEY}
    assert {user.joined_on for user in first} == {
        START_DATE + timedelta(days=offset) for offset in range(30)
    }


def test_allergy_persona_requires_verified_safe_recipe() -> None:
    user = synthetic_user(allergens=(Allergen.PEANUTS,))
    persona = next(persona for persona in SYNTHETIC_PERSONAS if persona.key == user.persona_key)

    assert (
        recipe_is_eligible(
            recipe=recipe_feature(allergen_status=AllergenAssessmentStatus.UNKNOWN.value),
            user=user,
            persona=persona,
            month=4,
        )
        is False
    )
    assert (
        recipe_is_eligible(
            recipe=recipe_feature(),
            user=user,
            persona=persona,
            month=4,
        )
        is True
    )


def test_interaction_simulation_is_reproducible() -> None:
    users = generate_synthetic_users(
        user_count=12,
        start_date=START_DATE,
        days=20,
        seed=42,
    )
    recipes = [recipe_feature()]

    first = simulate_interactions(
        users=users,
        recipes=recipes,
        start_date=START_DATE,
        days=20,
        seed=42,
        feed_size=1,
    )
    second = simulate_interactions(
        users=users,
        recipes=recipes,
        start_date=START_DATE,
        days=20,
        seed=42,
        feed_size=1,
    )

    assert first == second
    assert first
    assert all(event.is_synthetic for event in first)
    impression_slate_ids = {
        event.slate_id for event in first if event.event_type == RecommendationEventType.IMPRESSION
    }
    assert None not in impression_slate_ids


def test_initial_session_simulation_forces_one_history_free_slate_per_user() -> None:
    users = generate_cold_start_users(
        user_count=12,
        start_date=START_DATE,
        days=3,
        seed=42,
    )
    events = simulate_interactions(
        users=users,
        recipes=[recipe_feature()],
        start_date=START_DATE,
        days=3,
        seed=42,
        feed_size=1,
        initial_session_only=True,
    )
    examples = build_training_examples(
        users=users,
        recipes=[recipe_feature()],
        events=events,
        start_date=START_DATE,
        days=3,
    )

    impressions = [
        event for event in events if event.event_type == RecommendationEventType.IMPRESSION
    ]
    assert len(impressions) == len(users)
    assert len({event.slate_id for event in impressions}) == len(users)
    assert {example.user_prior_impressions for example in examples} == {0}
    assert {example.user_recipe_prior_impressions for example in examples} == {0}


def test_preprocessing_uses_only_prior_history_as_features() -> None:
    first_impression = datetime(2026, 4, 26, 18, tzinfo=UTC)
    events = [
        interaction_event(
            sequence=1,
            event_type=RecommendationEventType.IMPRESSION,
            occurred_at=first_impression,
            position=1,
        ),
        interaction_event(
            sequence=2,
            event_type=RecommendationEventType.OPEN,
            occurred_at=first_impression + timedelta(minutes=5),
        ),
        interaction_event(
            sequence=3,
            event_type=RecommendationEventType.IMPRESSION,
            occurred_at=first_impression + timedelta(days=1),
            position=2,
            slate_id=SECOND_TEST_SLATE_ID,
        ),
    ]

    examples = build_training_examples(
        users=[synthetic_user()],
        recipes=[recipe_feature()],
        events=events,
        start_date=START_DATE,
        days=90,
    )

    assert examples[0].user_prior_impressions == 0
    assert examples[0].user_prior_opens == 0
    assert examples[0].engagement_label == 1
    assert examples[0].relevance == 1
    assert examples[1].user_prior_impressions == 1
    assert examples[1].user_prior_opens == 1
    assert examples[1].user_recipe_prior_impressions == 1


def test_labels_do_not_cross_chronological_split_boundary() -> None:
    final_train_impression = datetime(2026, 6, 27, 23, 55, tzinfo=UTC)
    validation_open = datetime(2026, 6, 28, 0, 5, tzinfo=UTC)
    events = [
        interaction_event(
            sequence=1,
            event_type=RecommendationEventType.IMPRESSION,
            occurred_at=final_train_impression,
            position=1,
        ),
        interaction_event(
            sequence=2,
            event_type=RecommendationEventType.OPEN,
            occurred_at=validation_open,
        ),
    ]

    examples = build_training_examples(
        users=[synthetic_user()],
        recipes=[recipe_feature()],
        events=events,
        start_date=START_DATE,
        days=90,
    )

    assert examples[0].split == DatasetSplit.TRAIN
    assert examples[0].engagement_label == 0


def test_history_snapshot_does_not_change_within_a_slate() -> None:
    first_recipe = recipe_feature()
    second_recipe = recipe_feature(recipe_id=uuid.UUID("00000000-0000-0000-0000-000000000011"))
    impression_time = datetime(2026, 4, 26, 18, tzinfo=UTC)
    events = [
        interaction_event(
            sequence=1,
            event_type=RecommendationEventType.IMPRESSION,
            occurred_at=impression_time,
            position=1,
            recipe_id=first_recipe.recipe_id,
        ),
        interaction_event(
            sequence=2,
            event_type=RecommendationEventType.IMPRESSION,
            occurred_at=impression_time + timedelta(seconds=1),
            position=2,
            recipe_id=second_recipe.recipe_id,
        ),
    ]

    examples = build_training_examples(
        users=[synthetic_user()],
        recipes=[first_recipe, second_recipe],
        events=events,
        start_date=START_DATE,
        days=90,
    )

    assert {example.slate_id for example in examples} == {TEST_SLATE_ID}
    assert [example.user_prior_impressions for example in examples] == [0, 0]


def test_ninety_day_split_is_70_15_15_without_persona_feature() -> None:
    assert (
        split_for_timestamp(
            occurred_at=datetime(2026, 6, 27, tzinfo=UTC),
            start_date=START_DATE,
            days=90,
        )
        == DatasetSplit.TRAIN
    )
    assert (
        split_for_timestamp(
            occurred_at=datetime(2026, 6, 28, tzinfo=UTC),
            start_date=START_DATE,
            days=90,
        )
        == DatasetSplit.VALIDATION
    )
    assert (
        split_for_timestamp(
            occurred_at=datetime(2026, 7, 11, tzinfo=UTC),
            start_date=START_DATE,
            days=90,
        )
        == DatasetSplit.TEST
    )
    assert "persona_key" not in MODEL_FEATURE_COLUMNS
    assert "is_synthetic" not in MODEL_FEATURE_COLUMNS
    assert "position" not in MODEL_FEATURE_COLUMNS
