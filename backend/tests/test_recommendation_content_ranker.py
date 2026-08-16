import uuid

import pytest

from app.recommendations.content_ranker import (
    ContentRankingCandidate,
    RecipeSignal,
    rank_content_candidates,
)
from app.recommendations.ranking_types import RecipeContent


def recipe(
    sequence: int,
    *,
    area: str,
    ingredients: tuple[str, ...],
) -> RecipeContent:
    return RecipeContent(
        recipe_id=uuid.UUID(f"00000000-0000-0000-0000-{sequence:012d}"),
        name=f"Recipe {sequence}",
        area=area,
        category="Main",
        ingredient_names=ingredients,
    )


def candidate(
    recipe_id: uuid.UUID,
    *,
    seasonal_matches: int = 1,
    cuisine_match: int = 0,
) -> ContentRankingCandidate:
    return ContentRankingCandidate(
        recipe_id=recipe_id,
        seasonal_match_count=seasonal_matches,
        cuisine_match=cuisine_match,
    )


def test_history_profile_prefers_similar_recipe() -> None:
    liked = recipe(10, area="Italian", ingredients=("tomato", "basil", "pasta"))
    similar = recipe(11, area="Italian", ingredients=("tomato", "basil"))
    different = recipe(12, area="Japanese", ingredients=("salmon", "miso"))

    ranked = rank_content_candidates(
        recipes=[liked, similar, different],
        candidates=[
            candidate(similar.recipe_id),
            candidate(different.recipe_id),
        ],
        signals=[RecipeSignal(recipe_id=liked.recipe_id, weight=3.0)],
    )

    assert [item.recipe_id for item in ranked] == [
        similar.recipe_id,
        different.recipe_id,
    ]


def test_cold_start_uses_seasonal_strength_and_cuisine_match() -> None:
    weak = recipe(10, area="British", ingredients=("potato",))
    strong = recipe(11, area="Italian", ingredients=("tomato",))

    ranked = rank_content_candidates(
        recipes=[weak, strong],
        candidates=[
            candidate(weak.recipe_id, seasonal_matches=1),
            candidate(strong.recipe_id, seasonal_matches=3, cuisine_match=1),
        ],
        signals=[],
    )

    assert [item.recipe_id for item in ranked] == [
        strong.recipe_id,
        weak.recipe_id,
    ]


def test_equal_scores_use_recipe_identifier_order() -> None:
    first = recipe(10, area="British", ingredients=("potato",))
    second = recipe(11, area="British", ingredients=("leek",))

    ranked = rank_content_candidates(
        recipes=[second, first],
        candidates=[
            candidate(second.recipe_id),
            candidate(first.recipe_id),
        ],
        signals=[],
    )

    assert [item.recipe_id for item in ranked] == [
        first.recipe_id,
        second.recipe_id,
    ]


def test_profile_rejects_non_positive_signal_weight() -> None:
    item = recipe(10, area="British", ingredients=("potato",))

    with pytest.raises(ValueError, match="positive weight"):
        _ = rank_content_candidates(
            recipes=[item],
            candidates=[candidate(item.recipe_id)],
            signals=[RecipeSignal(recipe_id=item.recipe_id, weight=0)],
        )
