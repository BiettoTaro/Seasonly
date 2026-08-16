# pyright: reportMissingTypeStubs=false

import uuid
from collections import defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import cast

import numpy as np
from lightgbm import LGBMRanker, early_stopping, log_evaluation
from numpy.typing import NDArray

from app.recommendations.offline_data import ModelTrainingExample
from app.recommendations.preprocessing import MODEL_FEATURE_COLUMNS, DatasetSplit

CATEGORICAL_FEATURE_COLUMNS: tuple[str, ...] = (
    "user_country",
    "user_diet",
    "recipe_area",
    "recipe_category",
)
CATEGORICAL_FEATURE_INDICES: tuple[int, ...] = tuple(
    MODEL_FEATURE_COLUMNS.index(feature_name) for feature_name in CATEGORICAL_FEATURE_COLUMNS
)
UNKNOWN_CATEGORY_CODE = -1
MODEL_RANDOM_SEED = 20_260_724
EARLY_STOPPING_ROUNDS = 30
MAX_BOOSTING_ROUNDS = 500


@dataclass(frozen=True)
class RankerConfig:
    name: str
    num_leaves: int
    min_child_samples: int
    reg_lambda: float


RANKER_SEARCH_SPACE: tuple[RankerConfig, ...] = (
    RankerConfig(
        name="leaves15_child100_l2_1",
        num_leaves=15,
        min_child_samples=100,
        reg_lambda=1.0,
    ),
    RankerConfig(
        name="leaves31_child100_l2_1",
        num_leaves=31,
        min_child_samples=100,
        reg_lambda=1.0,
    ),
    RankerConfig(
        name="leaves31_child250_l2_1",
        num_leaves=31,
        min_child_samples=250,
        reg_lambda=1.0,
    ),
    RankerConfig(
        name="leaves63_child250_l2_2",
        num_leaves=63,
        min_child_samples=250,
        reg_lambda=2.0,
    ),
)


@dataclass(frozen=True)
class FeatureEncoder:
    category_mappings: dict[str, dict[str, int]]

    @classmethod
    def fit(cls, examples: Iterable[ModelTrainingExample]) -> "FeatureEncoder":
        categories: dict[str, set[str]] = {
            feature_name: set() for feature_name in CATEGORICAL_FEATURE_COLUMNS
        }
        found_training_example = False
        for example in examples:
            if example.split != DatasetSplit.TRAIN:
                raise ValueError("Feature encoder must be fitted with training examples only")
            found_training_example = True
            for feature_name in CATEGORICAL_FEATURE_COLUMNS:
                categories[feature_name].add(_categorical_value(example, feature_name))
        if not found_training_example:
            raise ValueError("Feature encoder requires at least one training example")
        return cls(
            category_mappings={
                feature_name: {value: index for index, value in enumerate(sorted(values))}
                for feature_name, values in categories.items()
            }
        )

    @classmethod
    def from_json(cls, payload: dict[str, object]) -> "FeatureEncoder":
        _validate_json_list(
            payload,
            key="feature_columns",
            expected=MODEL_FEATURE_COLUMNS,
        )
        _validate_json_list(
            payload,
            key="categorical_feature_columns",
            expected=CATEGORICAL_FEATURE_COLUMNS,
        )
        _validate_json_int_list(
            payload,
            key="categorical_feature_indices",
            expected=CATEGORICAL_FEATURE_INDICES,
        )
        if payload.get("unknown_category_code") != UNKNOWN_CATEGORY_CODE:
            raise ValueError("Feature schema has an unexpected unknown category code")

        raw_mappings = payload.get("category_mappings")
        if not isinstance(raw_mappings, dict):
            raise ValueError("Feature schema is missing category mappings")
        mappings_by_feature = cast(dict[object, object], raw_mappings)
        if set(mappings_by_feature) != set(CATEGORICAL_FEATURE_COLUMNS):
            raise ValueError("Feature schema has unexpected categorical features")

        category_mappings: dict[str, dict[str, int]] = {}
        for feature_name in CATEGORICAL_FEATURE_COLUMNS:
            raw_mapping = mappings_by_feature.get(feature_name)
            if not isinstance(raw_mapping, dict):
                raise ValueError(f"Feature schema mapping for {feature_name} must be an object")
            mapping: dict[str, int] = {}
            for raw_value, raw_code in cast(dict[object, object], raw_mapping).items():
                if not isinstance(raw_value, str) or not isinstance(raw_code, int) or raw_code < 0:
                    raise ValueError(f"Feature schema mapping for {feature_name} is invalid")
                mapping[raw_value] = raw_code
            if len(set(mapping.values())) != len(mapping):
                raise ValueError(f"Feature schema mapping for {feature_name} has duplicate codes")
            category_mappings[feature_name] = mapping
        return cls(category_mappings=category_mappings)

    def transform(
        self,
        examples: Sequence[ModelTrainingExample],
    ) -> NDArray[np.float64]:
        matrix = np.empty(
            (len(examples), len(MODEL_FEATURE_COLUMNS)),
            dtype=np.float64,
        )
        for row_index, example in enumerate(examples):
            for column_index, feature_name in enumerate(MODEL_FEATURE_COLUMNS):
                if feature_name in CATEGORICAL_FEATURE_COLUMNS:
                    mapping = self.category_mappings[feature_name]
                    matrix[row_index, column_index] = mapping.get(
                        _categorical_value(example, feature_name),
                        UNKNOWN_CATEGORY_CODE,
                    )
                else:
                    matrix[row_index, column_index] = _numeric_value(
                        example,
                        feature_name,
                    )
        return cast(NDArray[np.float64], matrix)

    def as_json(self) -> dict[str, object]:
        return {
            "feature_columns": list(MODEL_FEATURE_COLUMNS),
            "categorical_feature_columns": list(CATEGORICAL_FEATURE_COLUMNS),
            "categorical_feature_indices": list(CATEGORICAL_FEATURE_INDICES),
            "unknown_category_code": UNKNOWN_CATEGORY_CODE,
            "category_mappings": self.category_mappings,
        }


@dataclass(frozen=True)
class EncodedRankingSplit:
    split: DatasetSplit
    examples: tuple[ModelTrainingExample, ...]
    features: NDArray[np.float64]
    labels: NDArray[np.int32]
    group_sizes: NDArray[np.int32]


@dataclass(frozen=True)
class TrainedRanker:
    config: RankerConfig
    model: LGBMRanker
    best_iteration: int

    def predict(self, encoded_split: EncodedRankingSplit) -> NDArray[np.float64]:
        predictions = cast(
            object,
            self.model.booster_.predict(
                encoded_split.features,
                num_iteration=self.best_iteration,
            ),
        )
        return np.asarray(predictions, dtype=np.float64)

    def score_map(
        self,
        encoded_split: EncodedRankingSplit,
    ) -> dict[tuple[uuid.UUID, uuid.UUID], float]:
        predictions = self.predict(encoded_split)
        if len(predictions) != len(encoded_split.examples):
            raise ValueError("LightGBM returned an unexpected number of predictions")
        prediction_values = cast(list[float], predictions.tolist())
        return {
            (example.slate_id, example.recipe_id): score
            for example, score in zip(
                encoded_split.examples,
                prediction_values,
                strict=True,
            )
        }


def encode_split(
    *,
    examples: Iterable[ModelTrainingExample],
    split: DatasetSplit,
    encoder: FeatureEncoder,
) -> EncodedRankingSplit:
    grouped: defaultdict[uuid.UUID, list[ModelTrainingExample]] = defaultdict(list)
    for example in examples:
        if example.split == split:
            grouped[example.slate_id].append(example)
    if not grouped:
        raise ValueError(f"No examples found for the {split.value} split")

    ordered_examples: list[ModelTrainingExample] = []
    group_sizes: list[int] = []
    for slate_id in sorted(grouped, key=str):
        slate = sorted(grouped[slate_id], key=lambda example: str(example.recipe_id))
        _validate_slate(slate, expected_split=split)
        ordered_examples.extend(slate)
        group_sizes.append(len(slate))
    if sum(group_sizes) != len(ordered_examples):
        raise ValueError("Ranking group sizes do not match encoded rows")

    ordered_tuple = tuple(ordered_examples)
    return EncodedRankingSplit(
        split=split,
        examples=ordered_tuple,
        features=encoder.transform(ordered_tuple),
        labels=np.asarray(
            [example.relevance for example in ordered_tuple],
            dtype=np.int32,
        ),
        group_sizes=np.asarray(group_sizes, dtype=np.int32),
    )


def train_ranker(
    *,
    training: EncodedRankingSplit,
    validation: EncodedRankingSplit,
    config: RankerConfig,
) -> TrainedRanker:
    if training.split != DatasetSplit.TRAIN:
        raise ValueError("LightGBM training input must be the training split")
    if validation.split != DatasetSplit.VALIDATION:
        raise ValueError("LightGBM early stopping input must be the validation split")

    model = LGBMRanker(
        objective="lambdarank",
        metric="ndcg",
        n_estimators=MAX_BOOSTING_ROUNDS,
        learning_rate=0.05,
        num_leaves=config.num_leaves,
        min_child_samples=config.min_child_samples,
        reg_lambda=config.reg_lambda,
        importance_type="gain",
        random_state=MODEL_RANDOM_SEED,
        n_jobs=1,
        deterministic=True,
        force_col_wise=True,
        verbosity=-1,
        label_gain=[0, 1, 3, 7],
    )
    _ = model.fit(  # pyright: ignore[reportUnknownMemberType]
        training.features,
        training.labels,
        group=training.group_sizes,
        eval_X=validation.features,
        eval_y=validation.labels,
        eval_group=[validation.group_sizes],
        eval_names=["validation"],
        eval_metric="ndcg",
        eval_at=(10,),
        feature_name=list(MODEL_FEATURE_COLUMNS),
        categorical_feature=list(CATEGORICAL_FEATURE_INDICES),
        callbacks=[
            early_stopping(EARLY_STOPPING_ROUNDS, verbose=False),
            log_evaluation(period=0),
        ],
    )
    best_iteration = model.best_iteration_
    if best_iteration < 1:
        raise ValueError("LightGBM did not produce a valid best iteration")
    return TrainedRanker(
        config=config,
        model=model,
        best_iteration=best_iteration,
    )


def ranker_parameters(config: RankerConfig) -> dict[str, object]:
    return {
        "objective": "lambdarank",
        "metric": "ndcg",
        "eval_at": [10],
        "label_gain": [0, 1, 3, 7],
        "n_estimators": MAX_BOOSTING_ROUNDS,
        "learning_rate": 0.05,
        "num_leaves": config.num_leaves,
        "min_child_samples": config.min_child_samples,
        "reg_lambda": config.reg_lambda,
        "random_state": MODEL_RANDOM_SEED,
        "n_jobs": 1,
        "deterministic": True,
        "force_col_wise": True,
        "early_stopping_rounds": EARLY_STOPPING_ROUNDS,
    }


def _categorical_value(
    example: ModelTrainingExample,
    feature_name: str,
) -> str:
    match feature_name:
        case "user_country":
            return example.user_country
        case "user_diet":
            return example.user_diet
        case "recipe_area":
            return example.recipe_area
        case "recipe_category":
            return example.recipe_category
        case _:
            raise ValueError(f"Unsupported categorical feature {feature_name}")


def _numeric_value(
    example: ModelTrainingExample,
    feature_name: str,
) -> float:
    match feature_name:
        case "month":
            return float(example.month)
        case "seasonal_match_count":
            return float(example.seasonal_match_count)
        case "cuisine_match":
            return float(example.cuisine_match)
        case "user_prior_impressions":
            return float(example.user_prior_impressions)
        case "user_prior_opens":
            return float(example.user_prior_opens)
        case "user_prior_favourites":
            return float(example.user_prior_favourites)
        case "user_prior_plans":
            return float(example.user_prior_plans)
        case "user_recipe_prior_impressions":
            return float(example.user_recipe_prior_impressions)
        case "recipe_prior_impressions":
            return float(example.recipe_prior_impressions)
        case "recipe_prior_positive_actions":
            return float(example.recipe_prior_positive_actions)
        case _:
            raise ValueError(f"Unsupported numeric feature {feature_name}")


def _validate_slate(
    slate: Sequence[ModelTrainingExample],
    *,
    expected_split: DatasetSplit,
) -> None:
    if len({example.user_id for example in slate}) != 1:
        raise ValueError("A ranking group cannot contain multiple users")
    if {example.split for example in slate} != {expected_split}:
        raise ValueError("A ranking group cannot cross dataset splits")
    if len({example.recipe_id for example in slate}) != len(slate):
        raise ValueError("A ranking group cannot contain duplicate recipes")
    if len({example.user_prior_impressions for example in slate}) != 1:
        raise ValueError("User history must be snapshotted before the ranking group")


def _validate_json_list(
    payload: dict[str, object],
    *,
    key: str,
    expected: tuple[str, ...],
) -> None:
    raw_value = payload.get(key)
    if not isinstance(raw_value, list):
        raise ValueError(f"Feature schema field {key} must be a string array")
    items = cast(list[object], raw_value)
    if not all(isinstance(item, str) for item in items):
        raise ValueError(f"Feature schema field {key} must be a string array")
    if tuple(cast(list[str], items)) != expected:
        raise ValueError(f"Feature schema field {key} does not match the model contract")


def _validate_json_int_list(
    payload: dict[str, object],
    *,
    key: str,
    expected: tuple[int, ...],
) -> None:
    raw_value = payload.get(key)
    if not isinstance(raw_value, list):
        raise ValueError(f"Feature schema field {key} must be an integer array")
    items = cast(list[object], raw_value)
    if not all(isinstance(item, int) for item in items):
        raise ValueError(f"Feature schema field {key} must be an integer array")
    if tuple(cast(list[int], items)) != expected:
        raise ValueError(f"Feature schema field {key} does not match the model contract")
