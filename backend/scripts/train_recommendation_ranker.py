# pyright: reportMissingTypeStubs=false

import argparse
import json
import shutil
import tempfile
from dataclasses import asdict, dataclass
from importlib.metadata import version
from pathlib import Path
from typing import cast

from app.recommendations.baselines import (
    PrecomputedLightGBMBaseline,
    evaluate_baseline,
)
from app.recommendations.offline_data import (
    read_recipe_content,
    read_training_examples,
    sha256,
    validate_synthetic_dataset,
)
from app.recommendations.preprocessing import MODEL_FEATURE_COLUMNS, DatasetSplit
from app.recommendations.ranker import (
    RANKER_SEARCH_SPACE,
    EncodedRankingSplit,
    FeatureEncoder,
    RankerConfig,
    TrainedRanker,
    encode_split,
    ranker_parameters,
    train_ranker,
)
from app.recommendations.ranking_types import BaselineMetrics, RankingExample, RecipeContent
from app.recommendations.synthetic import SYNTHETIC_GENERATOR_VERSION

DEFAULT_DATASET_DIR = Path(f"datasets/synthetic/runs/{SYNTHETIC_GENERATOR_VERSION}-seed-20260724")
DEFAULT_ARTIFACT_DIR = Path("artifacts/recommendations/lightgbm-lambdarank-v1-seed-20260724")
EVALUATION_K = 10


@dataclass(frozen=True)
class CandidateValidationResult:
    config: RankerConfig
    best_iteration: int
    validation_metrics: BaselineMetrics


def train_and_publish(*, dataset_dir: Path, artifact_dir: Path) -> Path:
    if artifact_dir.exists():
        raise FileExistsError(
            " ".join(
                (
                    f"Model artifact already exists: {artifact_dir}.",
                    "Choose a new directory to preserve prior evidence.",
                )
            )
        )
    dataset_manifest = validate_synthetic_dataset(
        dataset_dir,
        required_files=("recipes.csv", "training_examples.csv"),
        minimum_feed_size=EVALUATION_K + 1,
    )
    recipes = read_recipe_content(dataset_dir / "recipes.csv")
    examples = read_training_examples(dataset_dir / "training_examples.csv")
    training_rows = [example for example in examples if example.split == DatasetSplit.TRAIN]
    encoder = FeatureEncoder.fit(training_rows)
    encoded_training = encode_split(
        examples=examples,
        split=DatasetSplit.TRAIN,
        encoder=encoder,
    )
    encoded_validation = encode_split(
        examples=examples,
        split=DatasetSplit.VALIDATION,
        encoder=encoder,
    )
    validation_ranking_examples = [
        example.ranking_example()
        for example in examples
        if example.split == DatasetSplit.VALIDATION
    ]

    candidate_results: list[CandidateValidationResult] = []
    selected_ranker: TrainedRanker | None = None
    selected_metrics: BaselineMetrics | None = None
    selected_index = -1
    for index, config in enumerate(RANKER_SEARCH_SPACE):
        ranker = train_ranker(
            training=encoded_training,
            validation=encoded_validation,
            config=config,
        )
        validation_metrics = _evaluate_ranker(
            ranker=ranker,
            encoded_split=encoded_validation,
            ranking_examples=validation_ranking_examples,
            recipes=recipes,
        )
        candidate_results.append(
            CandidateValidationResult(
                config=config,
                best_iteration=ranker.best_iteration,
                validation_metrics=validation_metrics,
            )
        )
        if selected_metrics is None or _selection_key(
            validation_metrics,
            search_index=index,
        ) > _selection_key(
            selected_metrics,
            search_index=selected_index,
        ):
            selected_ranker = ranker
            selected_metrics = validation_metrics
            selected_index = index

    if selected_ranker is None or selected_metrics is None:
        raise ValueError("Hyperparameter search did not produce a selected ranker")

    encoded_test = encode_split(
        examples=examples,
        split=DatasetSplit.TEST,
        encoder=encoder,
    )
    test_ranking_examples = [
        example.ranking_example() for example in examples if example.split == DatasetSplit.TEST
    ]
    test_metrics = _evaluate_ranker(
        ranker=selected_ranker,
        encoded_split=encoded_test,
        ranking_examples=test_ranking_examples,
        recipes=recipes,
    )
    _publish_artifact(
        artifact_dir=artifact_dir,
        dataset_dir=dataset_dir,
        dataset_manifest=dataset_manifest,
        encoder=encoder,
        selected_ranker=selected_ranker,
        selected_validation_metrics=selected_metrics,
        test_metrics=test_metrics,
        candidate_results=candidate_results,
        encoded_training=encoded_training,
        encoded_validation=encoded_validation,
        encoded_test=encoded_test,
    )
    return artifact_dir


def _evaluate_ranker(
    *,
    ranker: TrainedRanker,
    encoded_split: EncodedRankingSplit,
    ranking_examples: list[RankingExample],
    recipes: list[RecipeContent],
) -> BaselineMetrics:
    baseline = PrecomputedLightGBMBaseline(ranker.score_map(encoded_split))
    return evaluate_baseline(
        baseline=baseline,
        examples=ranking_examples,
        recipes=recipes,
        split=encoded_split.split,
        k=EVALUATION_K,
    )


def _selection_key(
    metrics: BaselineMetrics,
    *,
    search_index: int,
) -> tuple[float, float, int]:
    return (
        metrics.ndcg_at_k,
        metrics.recall_at_k,
        -search_index,
    )


def _publish_artifact(
    *,
    artifact_dir: Path,
    dataset_dir: Path,
    dataset_manifest: dict[str, object],
    encoder: FeatureEncoder,
    selected_ranker: TrainedRanker,
    selected_validation_metrics: BaselineMetrics,
    test_metrics: BaselineMetrics,
    candidate_results: list[CandidateValidationResult],
    encoded_training: EncodedRankingSplit,
    encoded_validation: EncodedRankingSplit,
    encoded_test: EncodedRankingSplit,
) -> None:
    artifact_dir.parent.mkdir(parents=True, exist_ok=True)
    temporary_dir = Path(
        tempfile.mkdtemp(
            prefix=f".{artifact_dir.name}-",
            dir=artifact_dir.parent,
        )
    )
    try:
        model_path = temporary_dir / "model.txt"
        _ = selected_ranker.model.booster_.save_model(
            model_path,
            num_iteration=selected_ranker.best_iteration,
        )
        feature_schema_path = temporary_dir / "feature_schema.json"
        _write_json(feature_schema_path, encoder.as_json())
        tuning_path = temporary_dir / "tuning_results.json"
        _write_json(
            tuning_path,
            {
                "selection_metric": "validation_ndcg_at_10",
                "test_split_accessed": False,
                "candidates": [
                    {
                        "config": asdict(result.config),
                        "parameters": ranker_parameters(result.config),
                        "best_iteration": result.best_iteration,
                        "validation_metrics": asdict(result.validation_metrics),
                    }
                    for result in candidate_results
                ],
            },
        )
        importance_values = cast(
            list[float],
            selected_ranker.model.booster_.feature_importance(
                importance_type="gain",
                iteration=selected_ranker.best_iteration,
            ).tolist(),
        )
        manifest = {
            "classification": "synthetic_prototype_model",
            "model_family": "LightGBM LambdaRank",
            "artifact_version": "lightgbm-lambdarank-v1",
            "synthetic_only": True,
            "production_effectiveness_claim_allowed": False,
            "dataset": str(dataset_dir),
            "dataset_generator_version": dataset_manifest["generator_version"],
            "dataset_manifest_sha256": sha256(dataset_dir / "manifest.json"),
            "fit_scope": "training split only",
            "selection_scope": "validation split only",
            "test_evaluated_once_after_selection": True,
            "evaluation_k": EVALUATION_K,
            "selected_config": asdict(selected_ranker.config),
            "selected_parameters": ranker_parameters(selected_ranker.config),
            "best_iteration": selected_ranker.best_iteration,
            "validation_metrics": asdict(selected_validation_metrics),
            "test_metrics": asdict(test_metrics),
            "feature_columns": list(MODEL_FEATURE_COLUMNS),
            "feature_importance_gain": dict(
                zip(MODEL_FEATURE_COLUMNS, importance_values, strict=True)
            ),
            "row_counts": {
                "train": len(encoded_training.examples),
                "validation": len(encoded_validation.examples),
                "test": len(encoded_test.examples),
            },
            "group_counts": {
                "train": len(encoded_training.group_sizes),
                "validation": len(encoded_validation.group_sizes),
                "test": len(encoded_test.group_sizes),
            },
            "library_versions": {
                "lightgbm": version("lightgbm"),
                "numpy": version("numpy"),
                "scikit-learn": version("scikit-learn"),
            },
            "limitations": [
                (
                    "The model is trained on synthetic interactions and cannot establish "
                    "real-user effectiveness."
                ),
                (
                    "Logged outcomes retain position and exposure bias from the synthetic "
                    "generating policy."
                ),
                ("Safety remains a pre-ranking hard filter and is not delegated to this model."),
            ],
            "files": {
                path.name: {
                    "sha256": sha256(path),
                    "bytes": path.stat().st_size,
                }
                for path in (model_path, feature_schema_path, tuning_path)
            },
        }
        _write_json(temporary_dir / "manifest.json", manifest)
        _ = temporary_dir.rename(artifact_dir)
    except Exception:
        shutil.rmtree(temporary_dir)
        raise


def _write_json(path: Path, payload: dict[str, object]) -> None:
    _ = path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Tune and train a deterministic LightGBM LambdaRank prototype on "
            "checksummed synthetic recommendation data."
        )
    )
    _ = parser.add_argument("--dataset-dir", type=Path, default=DEFAULT_DATASET_DIR)
    _ = parser.add_argument("--artifact-dir", type=Path, default=DEFAULT_ARTIFACT_DIR)
    args = parser.parse_args()
    dataset_dir = cast(Path, args.dataset_dir)
    artifact_dir = cast(Path, args.artifact_dir)
    result = train_and_publish(
        dataset_dir=dataset_dir,
        artifact_dir=artifact_dir,
    )
    print(f"Recommendation ranker artifact written to {result}")


if __name__ == "__main__":
    main()
