import uuid
from dataclasses import dataclass

from app.recommendations.preprocessing import DatasetSplit


@dataclass(frozen=True)
class RecipeContent:
    recipe_id: uuid.UUID
    name: str
    area: str
    category: str
    ingredient_names: tuple[str, ...]


@dataclass(frozen=True)
class RankingExample:
    slate_id: uuid.UUID
    user_id: uuid.UUID
    recipe_id: uuid.UUID
    split: DatasetSplit
    persona_key: str
    relevance: int
    user_prior_impressions: int
    seasonal_match_count: int
    cuisine_match: int


@dataclass(frozen=True)
class BaselineMetrics:
    k: int
    candidate_slates: int
    relevant_slates: int
    zero_history_relevant_slates: int
    ndcg_at_k: float
    recall_at_k: float
    catalog_coverage_at_k: float
    candidate_coverage_at_k: float
    mean_ingredient_diversity_at_k: float
    zero_history_ndcg_at_k: float
    zero_history_recall_at_k: float


@dataclass(frozen=True)
class SlateRankingMetrics:
    slate_id: uuid.UUID
    user_id: uuid.UUID
    ndcg_at_k: float
    recall_at_k: float
