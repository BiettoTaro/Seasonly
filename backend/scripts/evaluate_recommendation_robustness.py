# pyright: reportMissingTypeStubs=false

import argparse
import json
import uuid
from collections import Counter, defaultdict
from dataclasses import asdict
from pathlib import Path
from typing import cast

from app.data.synthetic import SYNTHETIC_PERSONAS
from app.recommendations.baselines import (
    PopularityBaseline,
    PrecomputedLightGBMBaseline,
    RankingBaseline,
    SeasonalContentBaseline,
    evaluate_baseline,
    evaluate_relevant_slates,
)
from app.recommendations.evaluation import (
    BootstrapInterval,
    paired_bootstrap_interval,
)
from app.recommendations.model_artifact import (
    LoadedRankerArtifact,
    load_ranker_artifact,
)
from app.recommendations.offline_data import (
    ModelTrainingExample,
    read_manifest,
    read_recipe_content,
    read_recipe_features,
    read_synthetic_users,
    read_training_examples,
    sha256,
    validate_synthetic_dataset,
)
from app.recommendations.preprocessing import MODEL_FEATURE_COLUMNS, DatasetSplit
from app.recommendations.ranking_types import (
    RankingExample,
    RecipeContent,
    SlateRankingMetrics,
)
from app.recommendations.synthetic import (
    SYNTHETIC_GENERATOR_VERSION,
    RecipeFeature,
    SyntheticUser,
    recipe_is_eligible,
)

DEFAULT_SOURCE_DATASET_DIR = Path(
    f"datasets/synthetic/runs/{SYNTHETIC_GENERATOR_VERSION}-seed-20260724"
)
DEFAULT_STRESS_DATASET_DIR = Path("datasets/synthetic/stress/cold-start-v1-seed-20260725")
DEFAULT_ARTIFACT_DIR = Path("artifacts/recommendations/lightgbm-lambdarank-v1-seed-20260724")
DEFAULT_OUTPUT_PATH = DEFAULT_STRESS_DATASET_DIR / "section6_evaluation-v2.json"
EVALUATION_K = 10
BOOTSTRAP_ITERATIONS = 10_000
BOOTSTRAP_SEED = 20_260_726
MINIMUM_SLICE_SLATES = 30
FORBIDDEN_MODEL_FEATURES = frozenset(
    {
        "persona_key",
        "position",
        "is_synthetic",
        "generator_version",
        "engagement_label",
        "relevance",
    }
)


def evaluate_and_publish(
    *,
    source_dataset_dir: Path,
    stress_dataset_dir: Path,
    artifact_dir: Path,
    output_path: Path,
) -> Path:
    if output_path.exists():
        raise FileExistsError(
            " ".join(
                (
                    f"Evaluation evidence already exists: {output_path}.",
                    "Choose a new output path to preserve the prior result.",
                )
            )
        )

    _ = validate_synthetic_dataset(
        source_dataset_dir,
        required_files=(
            "recipes.csv",
            "training_examples.csv",
            "users.csv",
        ),
        minimum_feed_size=EVALUATION_K + 1,
    )
    stress_manifest = _validate_stress_dataset(
        stress_dataset_dir=stress_dataset_dir,
        source_dataset_dir=source_dataset_dir,
    )
    artifact = load_ranker_artifact(artifact_dir)
    if artifact.manifest.get("dataset_manifest_sha256") != sha256(
        source_dataset_dir / "manifest.json"
    ):
        raise ValueError("Model artifact was not trained from the frozen source dataset")

    recipes = read_recipe_content(source_dataset_dir / "recipes.csv")
    recipe_features = read_recipe_features(source_dataset_dir / "recipes.csv")
    source_users = read_synthetic_users(source_dataset_dir / "users.csv")
    stress_users = read_synthetic_users(stress_dataset_dir / "users.csv")
    source_examples = read_training_examples(source_dataset_dir / "training_examples.csv")
    stress_examples = read_training_examples(stress_dataset_dir / "stress_examples.csv")
    training_examples = [
        example for example in source_examples if example.split == DatasetSplit.TRAIN
    ]
    _validate_isolation(
        source_examples=source_examples,
        stress_examples=stress_examples,
        training_examples=training_examples,
        stress_manifest=stress_manifest,
    )

    safety_audits = {
        "source_candidates": _audit_candidate_safety(
            examples=source_examples,
            users=source_users,
            recipes=recipe_features,
        ),
        "cold_start_candidates": _audit_candidate_safety(
            examples=stress_examples,
            users=stress_users,
            recipes=recipe_features,
        ),
    }

    training_ranking_examples = [example.ranking_example() for example in training_examples]
    source_test_ranking_examples = [
        example.ranking_example()
        for example in source_examples
        if example.split == DatasetSplit.TEST
    ]
    stress_ranking_examples = [example.ranking_example() for example in stress_examples]
    baselines = _build_baselines(
        recipes=recipes,
        training_examples=training_ranking_examples,
        source_examples=source_examples,
        stress_examples=stress_examples,
        artifact=artifact,
    )

    source_evaluation = _evaluate_cohort(
        baselines=baselines["source"],
        examples=source_test_ranking_examples,
        recipes=recipes,
    )
    stress_evaluation = _evaluate_cohort(
        baselines=baselines["stress"],
        examples=stress_ranking_examples,
        recipes=recipes,
    )
    source_paired = _paired_analysis(
        baselines=baselines["source"],
        examples=source_test_ranking_examples,
    )
    stress_paired = _paired_analysis(
        baselines=baselines["stress"],
        examples=stress_ranking_examples,
    )
    source_slices = _slice_analysis(
        baselines=baselines["source"],
        examples=source_examples,
        dimensions=("persona_key", "user_country", "user_diet"),
    )
    stress_slices = _slice_analysis(
        baselines=baselines["stress"],
        examples=stress_examples,
        dimensions=("user_country", "month"),
    )

    source_ndcg_interval = source_paired["ndcg_at_10"]
    stress_ndcg_interval = stress_paired["ndcg_at_10"]
    learned_model_supported = (
        float(source_ndcg_interval["lower_95"]) > 0 and float(stress_ndcg_interval["lower_95"]) > 0
    )
    selected_for_integration = (
        "lightgbm_lambdarank" if learned_model_supported else "seasonal_tfidf_content"
    )
    payload: dict[str, object] = {
        "protocol": {
            "training_or_tuning_performed": False,
            "evaluation_k": EVALUATION_K,
            "paired_bootstrap_iterations": BOOTSTRAP_ITERATIONS,
            "paired_bootstrap_seed": BOOTSTRAP_SEED,
            "confidence_interval": "paired percentile bootstrap, 95%",
            "slice_minimum_relevant_slates": MINIMUM_SLICE_SLATES,
        },
        "inputs": {
            "source_dataset": str(source_dataset_dir),
            "source_dataset_manifest_sha256": sha256(source_dataset_dir / "manifest.json"),
            "stress_dataset": str(stress_dataset_dir),
            "stress_dataset_manifest_sha256": sha256(stress_dataset_dir / "manifest.json"),
            "model_artifact": str(artifact_dir),
            "model_artifact_manifest_sha256": sha256(artifact_dir / "manifest.json"),
        },
        "locked_test": {
            "metrics": source_evaluation,
            "lightgbm_minus_seasonal_tfidf": source_paired,
            "slices": source_slices,
        },
        "cold_start_stress": {
            "metrics": stress_evaluation,
            "lightgbm_minus_seasonal_tfidf": stress_paired,
            "slices": stress_slices,
        },
        "controls": {
            "feature_columns": list(MODEL_FEATURE_COLUMNS),
            "forbidden_feature_overlap": sorted(
                FORBIDDEN_MODEL_FEATURES.intersection(MODEL_FEATURE_COLUMNS)
            ),
            "artifact_checksums_verified": True,
            "source_and_stress_user_ids_disjoint": True,
            "source_and_stress_slate_ids_disjoint": True,
            "stress_training_prohibited": True,
            "stress_user_history_all_zero": True,
            "stress_global_history_matches_frozen_training_counts": True,
            "safety_audits": safety_audits,
        },
        "decision_gate": {
            "learned_model_supported_on_both_cohorts": learned_model_supported,
            "selected_for_section_7": selected_for_integration,
            "rule": (
                "Select LightGBM only if the lower 95% paired-bootstrap NDCG@10 "
                "difference versus seasonal TF-IDF is above zero on both the "
                "locked test and isolated cold-start cohort."
            ),
            "synthetic_effectiveness_limitation": (
                "The result validates only synthetic offline behaviour and cannot "
                "establish real-user effectiveness."
            ),
        },
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    _ = output_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return output_path


def _validate_stress_dataset(
    *,
    stress_dataset_dir: Path,
    source_dataset_dir: Path,
) -> dict[str, object]:
    manifest = read_manifest(stress_dataset_dir / "manifest.json")
    if manifest.get("classification") != "synthetic_evaluation_only":
        raise ValueError("Cold-start dataset is not marked evaluation-only")
    if manifest.get("training_prohibited") is not True:
        raise ValueError("Cold-start dataset must prohibit training")
    if manifest.get("tuning_prohibited") is not True:
        raise ValueError("Cold-start dataset must prohibit tuning")
    if manifest.get("source_dataset_manifest_sha256") != sha256(
        source_dataset_dir / "manifest.json"
    ):
        raise ValueError("Cold-start dataset does not reference the frozen source dataset")
    if manifest.get("source_training_examples_sha256") != sha256(
        source_dataset_dir / "training_examples.csv"
    ):
        raise ValueError("Cold-start dataset source training checksum has changed")
    raw_files = manifest.get("files")
    if not isinstance(raw_files, dict):
        raise ValueError("Cold-start manifest is missing file metadata")
    files = cast(dict[object, object], raw_files)
    for filename in ("users.csv", "stress_examples.csv"):
        raw_metadata = files.get(filename)
        if not isinstance(raw_metadata, dict):
            raise ValueError(f"Cold-start manifest is missing metadata for {filename}")
        expected_hash = cast(dict[object, object], raw_metadata).get("sha256")
        if not isinstance(expected_hash, str):
            raise ValueError(f"Cold-start manifest is missing SHA-256 for {filename}")
        if sha256(stress_dataset_dir / filename) != expected_hash:
            raise ValueError(f"Cold-start checksum mismatch for {filename}")
    return manifest


def _validate_isolation(
    *,
    source_examples: list[ModelTrainingExample],
    stress_examples: list[ModelTrainingExample],
    training_examples: list[ModelTrainingExample],
    stress_manifest: dict[str, object],
) -> None:
    source_user_ids = {example.user_id for example in source_examples}
    source_slate_ids = {example.slate_id for example in source_examples}
    if source_user_ids.intersection(example.user_id for example in stress_examples):
        raise ValueError("Cold-start users overlap with the source dataset")
    if source_slate_ids.intersection(example.slate_id for example in stress_examples):
        raise ValueError("Cold-start slates overlap with the source dataset")
    if {example.split for example in stress_examples} != {DatasetSplit.TEST}:
        raise ValueError("Cold-start examples must be evaluation rows")
    if any(
        (
            example.user_prior_impressions
            or example.user_prior_opens
            or example.user_prior_favourites
            or example.user_prior_plans
            or example.user_recipe_prior_impressions
        )
        for example in stress_examples
    ):
        raise ValueError("Cold-start examples contain personal history")

    frozen_impressions: Counter[uuid.UUID] = Counter(
        example.recipe_id for example in training_examples
    )
    frozen_positive_actions: Counter[uuid.UUID] = Counter()
    for example in training_examples:
        frozen_positive_actions[example.recipe_id] += example.relevance
    if any(
        example.recipe_prior_impressions != frozen_impressions[example.recipe_id]
        or example.recipe_prior_positive_actions != frozen_positive_actions[example.recipe_id]
        for example in stress_examples
    ):
        raise ValueError("Cold-start global history is not frozen at the training cutoff")

    expected_rows = stress_manifest.get("candidate_rows")
    if not isinstance(expected_rows, int) or expected_rows != len(stress_examples):
        raise ValueError("Cold-start manifest candidate count does not match its data")


def _audit_candidate_safety(
    *,
    examples: list[ModelTrainingExample],
    users: list[SyntheticUser],
    recipes: list[RecipeFeature],
) -> dict[str, object]:
    users_by_id = {user.user_id: user for user in users}
    recipes_by_id = {recipe.recipe_id: recipe for recipe in recipes}
    personas_by_key = {persona.key: persona for persona in SYNTHETIC_PERSONAS}
    violations = 0
    allergy_constrained_candidates = 0
    users_with_candidates: set[uuid.UUID] = set()
    for example in examples:
        user = users_by_id.get(example.user_id)
        recipe = recipes_by_id.get(example.recipe_id)
        if user is None or recipe is None:
            raise ValueError("Safety audit found an unknown user or recipe")
        persona = personas_by_key.get(user.persona_key)
        if persona is None:
            raise ValueError(f"Safety audit found unknown persona {user.persona_key}")
        if user.allergens:
            allergy_constrained_candidates += 1
        users_with_candidates.add(user.user_id)
        if not recipe_is_eligible(
            recipe=recipe,
            user=user,
            persona=persona,
            month=example.month,
        ):
            violations += 1
    if violations:
        raise ValueError(f"Safety audit found {violations} ineligible candidates")
    allergy_user_ids = {user.user_id for user in users if user.allergens}
    persona_totals = Counter(user.persona_key for user in users)
    persona_served = Counter(users_by_id[user_id].persona_key for user_id in users_with_candidates)
    return {
        "candidates_checked": len(examples),
        "allergy_constrained_candidates": allergy_constrained_candidates,
        "violations": violations,
        "users": len(users),
        "users_with_candidates": len(users_with_candidates),
        "users_without_candidates": len(users) - len(users_with_candidates),
        "allergy_users": len(allergy_user_ids),
        "allergy_users_with_candidates": len(allergy_user_ids.intersection(users_with_candidates)),
        "coverage_by_persona": {
            persona_key: {
                "users": total,
                "users_with_candidates": persona_served[persona_key],
                "users_without_candidates": total - persona_served[persona_key],
            }
            for persona_key, total in sorted(persona_totals.items())
        },
    }


def _build_baselines(
    *,
    recipes: list[RecipeContent],
    training_examples: list[RankingExample],
    source_examples: list[ModelTrainingExample],
    stress_examples: list[ModelTrainingExample],
    artifact: LoadedRankerArtifact,
) -> dict[str, dict[str, RankingBaseline]]:
    source_score_map = artifact.score_map(
        source_examples,
        split=DatasetSplit.TEST,
    )
    stress_score_map = artifact.score_map(
        stress_examples,
        split=DatasetSplit.TEST,
    )
    return {
        "source": {
            "weighted_popularity": PopularityBaseline(training_examples),
            "seasonal_tfidf_content": SeasonalContentBaseline(
                recipes=recipes,
                training_examples=training_examples,
            ),
            "lightgbm_lambdarank": PrecomputedLightGBMBaseline(source_score_map),
        },
        "stress": {
            "weighted_popularity": PopularityBaseline(training_examples),
            "seasonal_tfidf_content": SeasonalContentBaseline(
                recipes=recipes,
                training_examples=training_examples,
            ),
            "lightgbm_lambdarank": PrecomputedLightGBMBaseline(stress_score_map),
        },
    }


def _evaluate_cohort(
    *,
    baselines: dict[str, RankingBaseline],
    examples: list[RankingExample],
    recipes: list[RecipeContent],
) -> dict[str, object]:
    return {
        name: asdict(
            evaluate_baseline(
                baseline=baseline,
                examples=examples,
                recipes=recipes,
                split=DatasetSplit.TEST,
                k=EVALUATION_K,
            )
        )
        for name, baseline in baselines.items()
    }


def _paired_analysis(
    *,
    baselines: dict[str, RankingBaseline],
    examples: list[RankingExample],
) -> dict[str, dict[str, int | float]]:
    learned = evaluate_relevant_slates(
        baseline=baselines["lightgbm_lambdarank"],
        examples=examples,
        split=DatasetSplit.TEST,
        k=EVALUATION_K,
    )
    content = evaluate_relevant_slates(
        baseline=baselines["seasonal_tfidf_content"],
        examples=examples,
        split=DatasetSplit.TEST,
        k=EVALUATION_K,
    )
    if set(learned) != set(content):
        raise ValueError("Paired evaluation models do not share the same relevant slates")
    slate_ids = sorted(learned, key=str)
    return {
        "ndcg_at_10": _bootstrap_payload(
            paired_bootstrap_interval(
                [
                    learned[slate_id].ndcg_at_k - content[slate_id].ndcg_at_k
                    for slate_id in slate_ids
                ],
                iterations=BOOTSTRAP_ITERATIONS,
                seed=BOOTSTRAP_SEED,
            )
        ),
        "recall_at_10": _bootstrap_payload(
            paired_bootstrap_interval(
                [
                    learned[slate_id].recall_at_k - content[slate_id].recall_at_k
                    for slate_id in slate_ids
                ],
                iterations=BOOTSTRAP_ITERATIONS,
                seed=BOOTSTRAP_SEED,
            )
        ),
    }


def _bootstrap_payload(
    interval: BootstrapInterval,
) -> dict[str, int | float]:
    return {
        "samples": interval.samples,
        "iterations": interval.iterations,
        "seed": interval.seed,
        "mean_delta": interval.mean_delta,
        "lower_95": interval.lower_95,
        "upper_95": interval.upper_95,
        "probability_positive": interval.probability_positive,
    }


def _slice_analysis(
    *,
    baselines: dict[str, RankingBaseline],
    examples: list[ModelTrainingExample],
    dimensions: tuple[str, ...],
) -> dict[str, object]:
    ranking_examples = [example.ranking_example() for example in examples]
    per_model = {
        name: evaluate_relevant_slates(
            baseline=baseline,
            examples=ranking_examples,
            split=DatasetSplit.TEST,
            k=EVALUATION_K,
        )
        for name, baseline in baselines.items()
    }
    reference_slates = set(per_model["lightgbm_lambdarank"])
    if any(set(metrics) != reference_slates for metrics in per_model.values()):
        raise ValueError("Slice evaluation models do not share relevant slates")

    metadata = _slate_metadata(examples)
    result: dict[str, object] = {}
    for dimension in dimensions:
        grouped: defaultdict[str, list[uuid.UUID]] = defaultdict(list)
        for slate_id in sorted(reference_slates, key=str):
            grouped[_metadata_value(metadata[slate_id], dimension)].append(slate_id)
        result[dimension] = [
            _slice_record(
                value=value,
                slate_ids=slate_ids,
                per_model=per_model,
            )
            for value, slate_ids in sorted(grouped.items())
        ]
    return result


def _slate_metadata(
    examples: list[ModelTrainingExample],
) -> dict[uuid.UUID, ModelTrainingExample]:
    metadata: dict[uuid.UUID, ModelTrainingExample] = {}
    for example in examples:
        existing = metadata.setdefault(example.slate_id, example)
        if (
            existing.user_id != example.user_id
            or existing.persona_key != example.persona_key
            or existing.user_country != example.user_country
            or existing.user_diet != example.user_diet
            or existing.month != example.month
        ):
            raise ValueError("Slate metadata changes within one candidate set")
    return metadata


def _metadata_value(example: ModelTrainingExample, dimension: str) -> str:
    match dimension:
        case "persona_key":
            return example.persona_key
        case "user_country":
            return example.user_country
        case "user_diet":
            return example.user_diet
        case "month":
            return str(example.month)
        case _:
            raise ValueError(f"Unsupported slice dimension {dimension}")


def _slice_record(
    *,
    value: str,
    slate_ids: list[uuid.UUID],
    per_model: dict[str, dict[uuid.UUID, SlateRankingMetrics]],
) -> dict[str, object]:
    metrics = {
        name: {
            "ndcg_at_10": _mean([slates[slate_id].ndcg_at_k for slate_id in slate_ids]),
            "recall_at_10": _mean([slates[slate_id].recall_at_k for slate_id in slate_ids]),
        }
        for name, slates in per_model.items()
    }
    learned = metrics["lightgbm_lambdarank"]
    content = metrics["seasonal_tfidf_content"]
    return {
        "value": value,
        "relevant_slates": len(slate_ids),
        "eligible_for_interpretation": len(slate_ids) >= MINIMUM_SLICE_SLATES,
        "metrics": metrics,
        "lightgbm_minus_seasonal_tfidf": {
            "ndcg_at_10": learned["ndcg_at_10"] - content["ndcg_at_10"],
            "recall_at_10": learned["recall_at_10"] - content["recall_at_10"],
        },
    }


def _mean(values: list[float]) -> float:
    if not values:
        raise ValueError("Cannot average an empty metric slice")
    return sum(values) / len(values)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate the frozen recommendation model against baselines with paired "
            "uncertainty, cold-start stress, slices, leakage and safety audits."
        )
    )
    _ = parser.add_argument(
        "--source-dataset-dir",
        type=Path,
        default=DEFAULT_SOURCE_DATASET_DIR,
    )
    _ = parser.add_argument(
        "--stress-dataset-dir",
        type=Path,
        default=DEFAULT_STRESS_DATASET_DIR,
    )
    _ = parser.add_argument("--artifact-dir", type=Path, default=DEFAULT_ARTIFACT_DIR)
    _ = parser.add_argument("--output-path", type=Path, default=DEFAULT_OUTPUT_PATH)
    args = parser.parse_args()
    result = evaluate_and_publish(
        source_dataset_dir=cast(Path, args.source_dataset_dir),
        stress_dataset_dir=cast(Path, args.stress_dataset_dir),
        artifact_dir=cast(Path, args.artifact_dir),
        output_path=cast(Path, args.output_path),
    )
    print(f"Recommendation robustness evaluation written to {result}")


if __name__ == "__main__":
    main()
