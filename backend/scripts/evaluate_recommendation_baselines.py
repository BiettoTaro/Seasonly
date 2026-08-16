import argparse
import json
import tempfile
from dataclasses import asdict
from pathlib import Path
from typing import cast

from app.recommendations.baselines import (
    PopularityBaseline,
    SeasonalContentBaseline,
    evaluate_baseline,
)
from app.recommendations.offline_data import (
    read_recipe_content,
    read_training_examples,
    sha256,
    validate_synthetic_dataset,
)
from app.recommendations.preprocessing import DatasetSplit
from app.recommendations.synthetic import SYNTHETIC_GENERATOR_VERSION

DEFAULT_DATASET_DIR = Path(f"datasets/synthetic/runs/{SYNTHETIC_GENERATOR_VERSION}-seed-20260724")
DEFAULT_K = 10


def evaluate_dataset(*, dataset_dir: Path, output_path: Path, k: int) -> Path:
    if output_path.exists():
        raise FileExistsError(
            " ".join(
                (
                    f"Evaluation output already exists: {output_path}.",
                    "Choose a new path to preserve prior evidence.",
                )
            )
        )
    manifest_path = dataset_dir / "manifest.json"
    manifest = validate_synthetic_dataset(
        dataset_dir,
        required_files=("recipes.csv", "training_examples.csv"),
        minimum_feed_size=k + 1,
    )

    recipes = read_recipe_content(dataset_dir / "recipes.csv")
    rows = read_training_examples(dataset_dir / "training_examples.csv")
    examples = [row.ranking_example() for row in rows]
    training_examples = [example for example in examples if example.split == DatasetSplit.TRAIN]
    if not training_examples:
        raise ValueError("The dataset contains no training examples")

    baselines = (
        PopularityBaseline(training_examples),
        SeasonalContentBaseline(
            recipes=recipes,
            training_examples=training_examples,
        ),
    )
    results = {
        baseline.name: {
            split.value: asdict(
                evaluate_baseline(
                    baseline=baseline,
                    examples=examples,
                    recipes=recipes,
                    split=split,
                    k=k,
                )
            )
            for split in (DatasetSplit.VALIDATION, DatasetSplit.TEST)
        }
        for baseline in baselines
    }
    split_counts = {
        split.value: sum(example.split == split for example in examples) for split in DatasetSplit
    }
    output = {
        "classification": "synthetic_offline_baseline_evaluation",
        "dataset": str(dataset_dir),
        "dataset_manifest_sha256": sha256(manifest_path),
        "generator_version": manifest["generator_version"],
        "k": k,
        "split_counts": split_counts,
        "fit_scope": "training split only",
        "ranking_scope": (
            "Each baseline reranks the 20 safety-filtered recipes in an observed synthetic slate."
        ),
        "metric_scope": (
            "NDCG and recall average only slates with at least one positive outcome; "
            "coverage and diversity use every slate."
        ),
        "content_weights": {
            "tfidf_history_similarity": SeasonalContentBaseline.content_weight,
            "seasonal_match": SeasonalContentBaseline.seasonal_weight,
            "cuisine_match": SeasonalContentBaseline.cuisine_weight,
        },
        "results": results,
        "limitations": [
            (
                "Synthetic results validate pipeline behaviour but are not evidence of "
                "real-user effectiveness."
            ),
            (
                "Outcomes are observed only for displayed recipes and retain position bias "
                "from the generating policy."
            ),
            (
                "The evaluation measures reranking within logged slates, not retrieval from "
                "the complete catalog."
            ),
        ],
    }
    _write_json_atomically(output_path, output)
    return output_path


def _write_json_atomically(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}-",
            suffix=".tmp",
            delete=False,
        ) as output_file:
            json.dump(payload, output_file, indent=2, sort_keys=True)
            _ = output_file.write("\n")
            temporary_path = Path(output_file.name)
        _ = temporary_path.rename(path)
    except Exception:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        raise


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate deterministic recommendation baselines on a synthetic dataset."
    )
    _ = parser.add_argument("--dataset-dir", type=Path, default=DEFAULT_DATASET_DIR)
    _ = parser.add_argument("--output-path", type=Path)
    _ = parser.add_argument("--k", type=int, default=DEFAULT_K)
    args = parser.parse_args()
    dataset_dir = cast(Path, args.dataset_dir)
    output_path = cast(Path | None, args.output_path)
    k = cast(int, args.k)
    resolved_output = output_path or dataset_dir / "baseline_metrics.json"
    result = evaluate_dataset(
        dataset_dir=dataset_dir,
        output_path=resolved_output,
        k=k,
    )
    print(f"Baseline evaluation written to {result}")


if __name__ == "__main__":
    main()
