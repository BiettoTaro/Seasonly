import uuid

import pytest

from app.recommendations.baselines import (
    PopularityBaseline,
    PrecomputedLightGBMBaseline,
    SeasonalContentBaseline,
    evaluate_baseline,
    evaluate_relevant_slates,
)
from app.recommendations.preprocessing import DatasetSplit
from app.recommendations.ranking_types import RankingExample, RecipeContent

USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
SLATE_ID = uuid.UUID("00000000-0000-0000-0000-000000000002")


def _approximately_equal(actual: float, expected: float) -> bool:
    tolerance = max(1e-6 * abs(expected), 1e-12)
    return abs(expected - actual) <= tolerance


def recipe(sequence: int, *, area: str, ingredients: tuple[str, ...]) -> RecipeContent:
    return RecipeContent(
        recipe_id=uuid.UUID(f"00000000-0000-0000-0000-{sequence:012d}"),
        name=f"Recipe {sequence}",
        area=area,
        category="Main",
        ingredient_names=ingredients,
    )


def example(
    recipe_id: uuid.UUID,
    *,
    split: DatasetSplit,
    relevance: int,
    slate_id: uuid.UUID = SLATE_ID,
    prior_impressions: int = 20,
    seasonal_matches: int = 1,
    cuisine_match: int = 0,
) -> RankingExample:
    return RankingExample(
        slate_id=slate_id,
        user_id=USER_ID,
        recipe_id=recipe_id,
        split=split,
        persona_key="test_persona",
        relevance=relevance,
        user_prior_impressions=prior_impressions,
        seasonal_match_count=seasonal_matches,
        cuisine_match=cuisine_match,
    )


def test_popularity_baseline_uses_training_relevance_only() -> None:
    popular = recipe(10, area="British", ingredients=("potato",))
    less_popular = recipe(11, area="French", ingredients=("leek",))
    baseline = PopularityBaseline(
        [
            example(popular.recipe_id, split=DatasetSplit.TRAIN, relevance=3),
            example(less_popular.recipe_id, split=DatasetSplit.TRAIN, relevance=1),
        ]
    )

    assert baseline.score(
        example(popular.recipe_id, split=DatasetSplit.TEST, relevance=0)
    ) > baseline.score(example(less_popular.recipe_id, split=DatasetSplit.TEST, relevance=0))


def test_content_baseline_prefers_recipe_similar_to_positive_history() -> None:
    liked = recipe(10, area="Italian", ingredients=("tomato", "basil", "pasta"))
    similar = recipe(11, area="Italian", ingredients=("tomato", "basil"))
    different = recipe(12, area="Japanese", ingredients=("salmon", "miso"))
    baseline = SeasonalContentBaseline(
        recipes=[liked, similar, different],
        training_examples=[
            example(liked.recipe_id, split=DatasetSplit.TRAIN, relevance=3),
        ],
    )

    similar_score = baseline.score(example(similar.recipe_id, split=DatasetSplit.TEST, relevance=0))
    different_score = baseline.score(
        example(different.recipe_id, split=DatasetSplit.TEST, relevance=0)
    )

    assert similar_score > different_score


def test_evaluation_reports_ranking_coverage_diversity_and_cold_start() -> None:
    recipes = [
        recipe(10, area="Italian", ingredients=("tomato", "basil")),
        recipe(11, area="British", ingredients=("potato",)),
        recipe(12, area="Japanese", ingredients=("miso",)),
    ]
    baseline = PopularityBaseline(
        [
            example(recipes[0].recipe_id, split=DatasetSplit.TRAIN, relevance=3),
            example(recipes[1].recipe_id, split=DatasetSplit.TRAIN, relevance=1),
        ]
    )
    test_examples = [
        example(
            recipes[0].recipe_id,
            split=DatasetSplit.TEST,
            relevance=3,
            prior_impressions=0,
        ),
        example(
            recipes[1].recipe_id,
            split=DatasetSplit.TEST,
            relevance=0,
            prior_impressions=0,
        ),
        example(
            recipes[2].recipe_id,
            split=DatasetSplit.TEST,
            relevance=1,
            prior_impressions=0,
        ),
    ]

    metrics = evaluate_baseline(
        baseline=baseline,
        examples=test_examples,
        recipes=recipes,
        split=DatasetSplit.TEST,
        k=2,
    )

    assert metrics.candidate_slates == 1
    assert metrics.relevant_slates == 1
    assert metrics.zero_history_relevant_slates == 1
    assert _approximately_equal(metrics.recall_at_k, 0.5)
    assert _approximately_equal(metrics.catalog_coverage_at_k, 2 / 3)
    assert _approximately_equal(metrics.candidate_coverage_at_k, 2 / 3)
    assert _approximately_equal(metrics.mean_ingredient_diversity_at_k, 1.0)


def test_evaluation_rejects_slate_without_more_candidates_than_k() -> None:
    recipes = [
        recipe(10, area="Italian", ingredients=("tomato",)),
        recipe(11, area="British", ingredients=("potato",)),
    ]
    baseline = PopularityBaseline(
        [example(recipes[0].recipe_id, split=DatasetSplit.TRAIN, relevance=1)]
    )

    with pytest.raises(ValueError, match="more candidates than k"):
        _ = evaluate_baseline(
            baseline=baseline,
            examples=[
                example(recipes[0].recipe_id, split=DatasetSplit.TEST, relevance=1),
                example(recipes[1].recipe_id, split=DatasetSplit.TEST, relevance=0),
            ],
            recipes=recipes,
            split=DatasetSplit.TEST,
            k=2,
        )


def test_precomputed_lightgbm_scores_are_scoped_to_slate_and_recipe() -> None:
    recipe_id = uuid.UUID("00000000-0000-0000-0000-000000000010")
    baseline = PrecomputedLightGBMBaseline(
        {(SLATE_ID, recipe_id): 0.75},
    )

    assert baseline.score(example(recipe_id, split=DatasetSplit.TEST, relevance=0)) == 0.75


def test_relevant_slate_evaluation_returns_paired_metrics_by_slate() -> None:
    recipes = [
        recipe(10, area="Italian", ingredients=("tomato",)),
        recipe(11, area="British", ingredients=("potato",)),
        recipe(12, area="Japanese", ingredients=("miso",)),
    ]
    baseline = PopularityBaseline(
        [
            example(recipes[0].recipe_id, split=DatasetSplit.TRAIN, relevance=3),
            example(recipes[1].recipe_id, split=DatasetSplit.TRAIN, relevance=1),
        ]
    )

    result = evaluate_relevant_slates(
        baseline=baseline,
        examples=[
            example(recipes[0].recipe_id, split=DatasetSplit.TEST, relevance=3),
            example(recipes[1].recipe_id, split=DatasetSplit.TEST, relevance=0),
            example(recipes[2].recipe_id, split=DatasetSplit.TEST, relevance=1),
        ],
        split=DatasetSplit.TEST,
        k=2,
    )

    assert set(result) == {SLATE_ID}
    assert _approximately_equal(result[SLATE_ID].recall_at_k, 0.5)
