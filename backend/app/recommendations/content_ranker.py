# pyright: reportMissingTypeStubs=false

import re
import uuid
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Protocol, cast

import numpy as np
from numpy.typing import NDArray
from sklearn.feature_extraction.text import TfidfVectorizer

from app.recommendations.ranking_types import RecipeContent

CONTENT_WEIGHT = 0.60
SEASONAL_WEIGHT = 0.30
CUISINE_WEIGHT = 0.10

type RecipeProfile = NDArray[np.float64]


class _SparseMatrix(Protocol):
    def toarray(self) -> NDArray[np.float64]: ...


@dataclass(frozen=True)
class RecipeSignal:
    recipe_id: uuid.UUID
    weight: float


@dataclass(frozen=True)
class ContentRankingCandidate:
    recipe_id: uuid.UUID
    seasonal_match_count: int
    cuisine_match: int


@dataclass(frozen=True)
class ContentRankingScore:
    recipe_id: uuid.UUID
    score: float


class TfidfRecipeIndex:
    def __init__(self, recipes: Sequence[RecipeContent]) -> None:
        if not recipes:
            raise ValueError("At least one recipe is required for the TF-IDF index")
        recipe_ids = [recipe.recipe_id for recipe in recipes]
        if len(set(recipe_ids)) != len(recipe_ids):
            raise ValueError("Recipe content records must have unique identifiers")

        self._recipe_index: dict[uuid.UUID, int] = {
            recipe_id: index for index, recipe_id in enumerate(recipe_ids)
        }
        vectorizer = TfidfVectorizer(
            lowercase=True,
            norm="l2",
            token_pattern=r"(?u)\b[\w-]+\b",
        )
        sparse_matrix = cast(
            _SparseMatrix,
            vectorizer.fit_transform(  # pyright: ignore[reportUnknownMemberType]
                [_recipe_document(recipe) for recipe in recipes]
            ),
        )
        self._recipe_vectors: NDArray[np.float64] = np.asarray(
            sparse_matrix.toarray(),
            dtype=np.float64,
        )

    def build_profile(
        self,
        signals: Iterable[RecipeSignal],
    ) -> RecipeProfile | None:
        feature_count = cast(int, self._recipe_vectors.shape[1])
        profile = cast(
            NDArray[np.float64],
            np.zeros(feature_count, dtype=np.float64),
        )
        has_signal = False
        for signal in signals:
            if signal.weight <= 0:
                raise ValueError("TF-IDF profile signals must have a positive weight")
            recipe_index = self._recipe_index.get(signal.recipe_id)
            if recipe_index is None:
                raise ValueError(f"Missing content record for recipe {signal.recipe_id}")
            recipe_vector = cast(
                NDArray[np.float64],
                self._recipe_vectors[recipe_index],
            )
            profile += recipe_vector * signal.weight
            has_signal = True
        if not has_signal:
            return None
        norm = float(np.linalg.norm(profile))
        return profile / norm if norm > 0 else None

    def similarity(
        self,
        *,
        recipe_id: uuid.UUID,
        profile: RecipeProfile | None,
    ) -> float:
        recipe_index = self._recipe_index.get(recipe_id)
        if recipe_index is None:
            raise ValueError(f"Missing content record for recipe {recipe_id}")
        if profile is None:
            return 0.0
        recipe_vector = cast(
            NDArray[np.float64],
            self._recipe_vectors[recipe_index],
        )
        return float(
            np.dot(  # pyright: ignore[reportAny]
                profile,
                recipe_vector,
            )
        )


def rank_content_candidates(
    *,
    recipes: Sequence[RecipeContent],
    candidates: Sequence[ContentRankingCandidate],
    signals: Iterable[RecipeSignal],
) -> list[ContentRankingScore]:
    if not candidates:
        return []
    if len({candidate.recipe_id for candidate in candidates}) != len(candidates):
        raise ValueError("Recommendation candidates must have unique recipe identifiers")
    index = TfidfRecipeIndex(recipes)
    profile = index.build_profile(signals)
    scores = [
        ContentRankingScore(
            recipe_id=candidate.recipe_id,
            score=content_ranking_score(
                content_similarity=index.similarity(
                    recipe_id=candidate.recipe_id,
                    profile=profile,
                ),
                seasonal_match_count=candidate.seasonal_match_count,
                cuisine_match=candidate.cuisine_match,
            ),
        )
        for candidate in candidates
    ]
    return sorted(scores, key=lambda item: (-item.score, str(item.recipe_id)))


def content_ranking_score(
    *,
    content_similarity: float,
    seasonal_match_count: int,
    cuisine_match: int,
) -> float:
    if seasonal_match_count < 0:
        raise ValueError("Seasonal match count cannot be negative")
    if cuisine_match not in {0, 1}:
        raise ValueError("Cuisine match must be 0 or 1")
    seasonal_score = seasonal_match_count / (seasonal_match_count + 1.0)
    return (
        CONTENT_WEIGHT * content_similarity
        + SEASONAL_WEIGHT * seasonal_score
        + CUISINE_WEIGHT * cuisine_match
    )


def _recipe_document(recipe: RecipeContent) -> str:
    tokens = [
        f"name_{_token(recipe.name)}",
        f"area_{_token(recipe.area)}",
        f"category_{_token(recipe.category)}",
    ]
    tokens.extend(f"ingredient_{_token(ingredient)}" for ingredient in recipe.ingredient_names)
    return " ".join(tokens)


def _token(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "_", value.casefold()).strip("_")
    return normalized or "unknown"
