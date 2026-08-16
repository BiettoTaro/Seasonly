# pyright: reportMissingTypeStubs=false

import math
import uuid
from collections import Counter, defaultdict
from collections.abc import Iterable, Sequence
from typing import ClassVar, Protocol

from app.recommendations.content_ranker import (
    CONTENT_WEIGHT,
    CUISINE_WEIGHT,
    SEASONAL_WEIGHT,
    RecipeProfile,
    RecipeSignal,
    TfidfRecipeIndex,
    content_ranking_score,
)
from app.recommendations.preprocessing import DatasetSplit
from app.recommendations.ranking_types import (
    BaselineMetrics,
    RankingExample,
    RecipeContent,
    SlateRankingMetrics,
)


class RankingBaseline(Protocol):
    name: ClassVar[str]

    def score(self, example: RankingExample) -> float: ...


class PopularityBaseline:
    name: ClassVar[str] = "weighted_popularity"

    def __init__(self, training_examples: Iterable[RankingExample]) -> None:
        self._weighted_positive_actions: Counter[uuid.UUID] = Counter()
        for example in training_examples:
            if example.split != DatasetSplit.TRAIN:
                raise ValueError("Popularity baseline must be fitted with training examples only")
            self._weighted_positive_actions[example.recipe_id] += example.relevance

    def score(self, example: RankingExample) -> float:
        return float(self._weighted_positive_actions[example.recipe_id])


class PrecomputedLightGBMBaseline:
    name: ClassVar[str] = "lightgbm_lambdarank"

    def __init__(
        self,
        scores: dict[tuple[uuid.UUID, uuid.UUID], float],
    ) -> None:
        self._scores: dict[tuple[uuid.UUID, uuid.UUID], float] = scores

    def score(self, example: RankingExample) -> float:
        key = (example.slate_id, example.recipe_id)
        score = self._scores.get(key)
        if score is None:
            raise ValueError(
                " ".join(
                    (
                        f"Missing LightGBM score for slate {example.slate_id}",
                        f"and recipe {example.recipe_id}",
                    )
                )
            )
        return score


class SeasonalContentBaseline:
    name: ClassVar[str] = "seasonal_tfidf_content"
    content_weight: ClassVar[float] = CONTENT_WEIGHT
    seasonal_weight: ClassVar[float] = SEASONAL_WEIGHT
    cuisine_weight: ClassVar[float] = CUISINE_WEIGHT

    def __init__(
        self,
        *,
        recipes: Sequence[RecipeContent],
        training_examples: Iterable[RankingExample],
    ) -> None:
        self._index: TfidfRecipeIndex = TfidfRecipeIndex(recipes)
        self._user_profiles: dict[uuid.UUID, RecipeProfile] = self._build_user_profiles(
            training_examples
        )

    def score(self, example: RankingExample) -> float:
        profile = self._user_profiles.get(example.user_id)
        return content_ranking_score(
            content_similarity=self._index.similarity(
                recipe_id=example.recipe_id,
                profile=profile,
            ),
            seasonal_match_count=example.seasonal_match_count,
            cuisine_match=example.cuisine_match,
        )

    def _build_user_profiles(
        self,
        training_examples: Iterable[RankingExample],
    ) -> dict[uuid.UUID, RecipeProfile]:
        signals_by_user: defaultdict[uuid.UUID, list[RecipeSignal]] = defaultdict(list)
        for example in training_examples:
            if example.split != DatasetSplit.TRAIN:
                raise ValueError("Content baseline must be fitted with training examples only")
            if example.relevance < 1:
                continue
            signals_by_user[example.user_id].append(
                RecipeSignal(
                    recipe_id=example.recipe_id,
                    weight=float(example.relevance),
                )
            )
        return {
            user_id: profile
            for user_id, signals in signals_by_user.items()
            if (profile := self._index.build_profile(signals)) is not None
        }


def evaluate_baseline(
    *,
    baseline: RankingBaseline,
    examples: Iterable[RankingExample],
    recipes: Sequence[RecipeContent],
    split: DatasetSplit,
    k: int,
) -> BaselineMetrics:
    if k < 1:
        raise ValueError("k must be at least 1")
    recipes_by_id = {recipe.recipe_id: recipe for recipe in recipes}
    if len(recipes_by_id) != len(recipes):
        raise ValueError("Recipe content records must have unique identifiers")

    slates: defaultdict[uuid.UUID, list[RankingExample]] = defaultdict(list)
    for example in examples:
        if example.split == split:
            slates[example.slate_id].append(example)
    if not slates:
        raise ValueError(f"No examples found for the {split.value} split")
    if any(len(slate) <= k for slate in slates.values()):
        raise ValueError("Every evaluation slate must contain more candidates than k")

    ndcg_values: list[float] = []
    recall_values: list[float] = []
    zero_history_ndcg_values: list[float] = []
    zero_history_recall_values: list[float] = []
    diversity_values: list[float] = []
    recommended_recipe_ids: set[uuid.UUID] = set()
    candidate_recipe_ids: set[uuid.UUID] = set()

    for slate in slates.values():
        _validate_slate(slate)
        candidate_recipe_ids.update(example.recipe_id for example in slate)
        ranked = sorted(
            slate,
            key=lambda example: (-baseline.score(example), str(example.recipe_id)),
        )
        top_k = ranked[:k]
        recommended_recipe_ids.update(example.recipe_id for example in top_k)
        diversity_values.append(
            _ingredient_diversity(
                [recipes_by_id[example.recipe_id] for example in top_k],
            )
        )

        relevant_count = sum(example.relevance > 0 for example in slate)
        if relevant_count == 0:
            continue
        ndcg = _ndcg_at_k(ranked, k=k)
        recall = sum(example.relevance > 0 for example in top_k) / relevant_count
        ndcg_values.append(ndcg)
        recall_values.append(recall)
        if slate[0].user_prior_impressions == 0:
            zero_history_ndcg_values.append(ndcg)
            zero_history_recall_values.append(recall)

    if not ndcg_values:
        raise ValueError(f"No relevant slates found for the {split.value} split")

    return BaselineMetrics(
        k=k,
        candidate_slates=len(slates),
        relevant_slates=len(ndcg_values),
        zero_history_relevant_slates=len(zero_history_ndcg_values),
        ndcg_at_k=_mean(ndcg_values),
        recall_at_k=_mean(recall_values),
        catalog_coverage_at_k=len(recommended_recipe_ids) / len(recipes),
        candidate_coverage_at_k=len(recommended_recipe_ids) / len(candidate_recipe_ids),
        mean_ingredient_diversity_at_k=_mean(diversity_values),
        zero_history_ndcg_at_k=_mean(zero_history_ndcg_values),
        zero_history_recall_at_k=_mean(zero_history_recall_values),
    )


def evaluate_relevant_slates(
    *,
    baseline: RankingBaseline,
    examples: Iterable[RankingExample],
    split: DatasetSplit,
    k: int,
) -> dict[uuid.UUID, SlateRankingMetrics]:
    if k < 1:
        raise ValueError("k must be at least 1")
    slates: defaultdict[uuid.UUID, list[RankingExample]] = defaultdict(list)
    for example in examples:
        if example.split == split:
            slates[example.slate_id].append(example)
    if not slates:
        raise ValueError(f"No examples found for the {split.value} split")
    if any(len(slate) <= k for slate in slates.values()):
        raise ValueError("Every evaluation slate must contain more candidates than k")

    metrics: dict[uuid.UUID, SlateRankingMetrics] = {}
    for slate_id, slate in slates.items():
        _validate_slate(slate)
        relevant_count = sum(example.relevance > 0 for example in slate)
        if relevant_count == 0:
            continue
        ranked = sorted(
            slate,
            key=lambda example: (-baseline.score(example), str(example.recipe_id)),
        )
        metrics[slate_id] = SlateRankingMetrics(
            slate_id=slate_id,
            user_id=slate[0].user_id,
            ndcg_at_k=_ndcg_at_k(ranked, k=k),
            recall_at_k=(sum(example.relevance > 0 for example in ranked[:k]) / relevant_count),
        )
    if not metrics:
        raise ValueError(f"No relevant slates found for the {split.value} split")
    return metrics


def _validate_slate(slate: Sequence[RankingExample]) -> None:
    if len({example.user_id for example in slate}) != 1:
        raise ValueError("A slate cannot contain multiple users")
    if len({example.split for example in slate}) != 1:
        raise ValueError("A slate cannot cross dataset splits")
    if len({example.recipe_id for example in slate}) != len(slate):
        raise ValueError("A slate cannot contain duplicate recipes")
    if len({example.user_prior_impressions for example in slate}) != 1:
        raise ValueError("User history must be snapshotted before the slate")


def _ndcg_at_k(ranked: Sequence[RankingExample], *, k: int) -> float:
    observed = _discounted_cumulative_gain(
        [example.relevance for example in ranked[:k]],
    )
    ideal = _discounted_cumulative_gain(
        sorted((example.relevance for example in ranked), reverse=True)[:k],
    )
    return observed / ideal if ideal > 0 else 0.0


def _discounted_cumulative_gain(relevances: Sequence[int]) -> float:
    return sum(
        ((2**relevance) - 1) / math.log2(index + 2) for index, relevance in enumerate(relevances)
    )


def _ingredient_diversity(recipes: Sequence[RecipeContent]) -> float:
    if len(recipes) < 2:
        return 0.0
    distances: list[float] = []
    for left_index, left in enumerate(recipes):
        left_ingredients = {ingredient.casefold() for ingredient in left.ingredient_names}
        for right in recipes[left_index + 1 :]:
            right_ingredients = {ingredient.casefold() for ingredient in right.ingredient_names}
            union = left_ingredients | right_ingredients
            intersection = left_ingredients & right_ingredients
            distances.append(1.0 - (len(intersection) / len(union)) if union else 0.0)
    return _mean(distances)


def _mean(values: Sequence[float]) -> float:
    return sum(values) / len(values) if values else 0.0
