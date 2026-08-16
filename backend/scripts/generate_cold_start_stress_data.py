import argparse
import csv
import json
import shutil
import tempfile
import uuid
from collections import Counter
from datetime import date, timedelta
from pathlib import Path
from typing import cast

from app.data.synthetic import SYNTHETIC_PERSONAS
from app.recommendations.offline_data import (
    ModelTrainingExample,
    read_recipe_features,
    read_training_examples,
    sha256,
    validate_synthetic_dataset,
    write_training_examples,
)
from app.recommendations.preprocessing import DatasetSplit, build_training_examples
from app.recommendations.synthetic import (
    COLD_START_PERSONA_KEY,
    SYNTHETIC_GENERATOR_VERSION,
    RecipeFeature,
    SyntheticUser,
    generate_cold_start_users,
    recipe_is_eligible,
    simulate_interactions,
)

COLD_START_STRESS_VERSION = "cold-start-stress-v1"
DEFAULT_SOURCE_DATASET_DIR = Path(
    f"datasets/synthetic/runs/{SYNTHETIC_GENERATOR_VERSION}-seed-20260724"
)
DEFAULT_OUTPUT_DIR = Path("datasets/synthetic/stress/cold-start-v1-seed-20260725")
DEFAULT_USER_COUNT = 1_000
DEFAULT_DAYS = 30
DEFAULT_SEED = 20_260_725
DEFAULT_START_DATE = date(2026, 7, 25)
DEFAULT_FEED_SIZE = 20


def generate_and_publish(
    *,
    source_dataset_dir: Path,
    output_dir: Path,
    user_count: int,
    days: int,
    seed: int,
    start_date: date,
    feed_size: int,
) -> Path:
    if output_dir.exists():
        raise FileExistsError(
            " ".join(
                (
                    f"Output directory already exists: {output_dir}.",
                    "Choose a new directory to preserve prior evaluation evidence.",
                )
            )
        )
    source_manifest = validate_synthetic_dataset(
        source_dataset_dir,
        required_files=("recipes.csv", "training_examples.csv"),
        minimum_feed_size=feed_size,
    )
    recipes = read_recipe_features(source_dataset_dir / "recipes.csv")
    source_examples = read_training_examples(source_dataset_dir / "training_examples.csv")
    source_training_examples = [
        example for example in source_examples if example.split == DatasetSplit.TRAIN
    ]
    if not source_training_examples:
        raise ValueError("Source dataset contains no training examples")

    frozen_recipe_impressions: Counter[uuid.UUID] = Counter(
        example.recipe_id for example in source_training_examples
    )
    frozen_recipe_positive_actions: Counter[uuid.UUID] = Counter()
    for example in source_training_examples:
        frozen_recipe_positive_actions[example.recipe_id] += example.relevance

    users = generate_cold_start_users(
        user_count=user_count,
        start_date=start_date,
        days=days,
        seed=seed,
    )
    events = simulate_interactions(
        users=users,
        recipes=recipes,
        start_date=start_date,
        days=days,
        seed=seed,
        feed_size=feed_size,
        initial_session_only=True,
    )
    generated_examples = build_training_examples(
        users=users,
        recipes=recipes,
        events=events,
        start_date=start_date,
        days=days,
    )
    expected_rows = user_count * feed_size
    if len(generated_examples) != expected_rows:
        raise ValueError(
            f"Expected {expected_rows} cold-start candidates, received {len(generated_examples)}"
        )

    stress_examples = [
        ModelTrainingExample(
            slate_id=example.slate_id,
            user_id=example.user_id,
            recipe_id=example.recipe_id,
            split=DatasetSplit.TEST,
            persona_key=example.persona_key,
            relevance=example.relevance,
            month=example.month,
            seasonal_match_count=example.seasonal_match_count,
            cuisine_match=example.cuisine_match,
            user_country=example.user_country,
            user_diet=example.user_diet,
            recipe_area=example.recipe_area,
            recipe_category=example.recipe_category,
            user_prior_impressions=0,
            user_prior_opens=0,
            user_prior_favourites=0,
            user_prior_plans=0,
            user_recipe_prior_impressions=0,
            recipe_prior_impressions=frozen_recipe_impressions[example.recipe_id],
            recipe_prior_positive_actions=frozen_recipe_positive_actions[example.recipe_id],
        )
        for example in generated_examples
    ]
    _validate_stress_examples(
        users=users,
        recipes_by_id={recipe.recipe_id: recipe for recipe in recipes},
        examples=stress_examples,
        feed_size=feed_size,
    )
    _publish(
        output_dir=output_dir,
        source_dataset_dir=source_dataset_dir,
        source_manifest=source_manifest,
        users=users,
        examples=stress_examples,
        start_date=start_date,
        days=days,
        seed=seed,
        feed_size=feed_size,
    )
    return output_dir


def _validate_stress_examples(
    *,
    users: list[SyntheticUser],
    recipes_by_id: dict[uuid.UUID, RecipeFeature],
    examples: list[ModelTrainingExample],
    feed_size: int,
) -> None:
    users_by_id = {user.user_id: user for user in users}
    persona = next(
        (item for item in SYNTHETIC_PERSONAS if item.key == COLD_START_PERSONA_KEY),
        None,
    )
    if persona is None:
        raise ValueError(f"Synthetic persona {COLD_START_PERSONA_KEY} is not configured")

    slate_counts: Counter[uuid.UUID] = Counter()
    user_slates: dict[uuid.UUID, set[uuid.UUID]] = {}
    for example in examples:
        user = users_by_id[example.user_id]
        recipe = recipes_by_id.get(example.recipe_id)
        if recipe is None:
            raise ValueError(f"Stress example references unknown recipe {example.recipe_id}")
        if not recipe_is_eligible(
            recipe=recipe,
            user=user,
            persona=persona,
            month=example.month,
        ):
            raise ValueError("Cold-start stress cohort contains an unsafe or ineligible candidate")
        if any(
            (
                example.user_prior_impressions,
                example.user_prior_opens,
                example.user_prior_favourites,
                example.user_prior_plans,
                example.user_recipe_prior_impressions,
            )
        ):
            raise ValueError("Cold-start stress cohort contains non-zero user history")
        slate_counts[example.slate_id] += 1
        user_slates.setdefault(example.user_id, set()).add(example.slate_id)

    if set(users_by_id) != set(user_slates):
        raise ValueError("Every cold-start user must have an evaluation slate")
    if any(len(slates) != 1 for slates in user_slates.values()):
        raise ValueError("Every cold-start user must have exactly one evaluation slate")
    if set(slate_counts.values()) != {feed_size}:
        raise ValueError("Every cold-start slate must have the configured candidate count")


def _publish(
    *,
    output_dir: Path,
    source_dataset_dir: Path,
    source_manifest: dict[str, object],
    users: list[SyntheticUser],
    examples: list[ModelTrainingExample],
    start_date: date,
    days: int,
    seed: int,
    feed_size: int,
) -> None:
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    temporary_dir = Path(
        tempfile.mkdtemp(
            prefix=f".{output_dir.name}-",
            dir=output_dir.parent,
        )
    )
    try:
        users_path = temporary_dir / "users.csv"
        examples_path = temporary_dir / "stress_examples.csv"
        _write_users(users_path, users)
        write_training_examples(examples_path, examples)

        source_start_date = _manifest_date(source_manifest, "start_date")
        source_days = _manifest_int(source_manifest, "days")
        training_days = (source_days * 70) // 100
        training_history_cutoff = source_start_date + timedelta(days=training_days - 1)
        relevant_slates = len({example.slate_id for example in examples if example.relevance > 0})
        manifest: dict[str, object] = {
            "classification": "synthetic_evaluation_only",
            "stress_version": COLD_START_STRESS_VERSION,
            "generator_version": SYNTHETIC_GENERATOR_VERSION,
            "training_prohibited": True,
            "tuning_prohibited": True,
            "seed": seed,
            "start_date": start_date.isoformat(),
            "end_date": (start_date + timedelta(days=days - 1)).isoformat(),
            "days": days,
            "users": len(users),
            "slates": len(users),
            "candidate_rows": len(examples),
            "relevant_slates": relevant_slates,
            "feed_size": feed_size,
            "persona_user_counts": dict(
                sorted(Counter(user.persona_key for user in users).items())
            ),
            "country_user_counts": dict(
                sorted(Counter(user.country_code.value for user in users).items())
            ),
            "source_dataset": str(source_dataset_dir),
            "source_dataset_manifest_sha256": sha256(source_dataset_dir / "manifest.json"),
            "source_training_examples_sha256": sha256(source_dataset_dir / "training_examples.csv"),
            "global_recipe_history_scope": "source training split only",
            "global_recipe_history_cutoff": training_history_cutoff.isoformat(),
            "user_history_policy": "all user and user-recipe history features fixed at zero",
            "session_policy": "one forced first-session slate per user",
            "safety_audit": {
                "candidates_checked": len(examples),
                "violations": 0,
                "policy": "seasonal, dietary and declared-allergen hard filters",
            },
            "evaluation_restriction": (
                "This isolated synthetic cohort is for evaluation only and must not be "
                "used for fitting, early stopping, hyperparameter selection or "
                "real-user effectiveness claims."
            ),
            "files": {
                path.name: {
                    "sha256": sha256(path),
                    "bytes": path.stat().st_size,
                }
                for path in (users_path, examples_path)
            },
        }
        _ = (temporary_dir / "manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        _ = temporary_dir.rename(output_dir)
    except Exception:
        shutil.rmtree(temporary_dir)
        raise


def _write_users(path: Path, users: list[SyntheticUser]) -> None:
    rows: list[dict[str, object]] = [
        {
            "user_id": str(user.user_id),
            "persona_key": user.persona_key,
            "country_code": user.country_code.value,
            "diet_pattern": user.diet_pattern.value,
            "preferred_areas": "|".join(user.preferred_areas),
            "allergens": "|".join(allergen.value for allergen in user.allergens),
            "joined_on": user.joined_on.isoformat(),
            "is_synthetic": True,
        }
        for user in users
    ]
    with path.open("w", newline="", encoding="utf-8") as output_file:
        writer = csv.DictWriter(
            output_file,
            fieldnames=list(rows[0]),
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)


def _manifest_date(manifest: dict[str, object], key: str) -> date:
    value = manifest.get(key)
    if not isinstance(value, str):
        raise ValueError(f"Source manifest field {key} must be a date")
    try:
        return date.fromisoformat(value)
    except ValueError as e:
        raise ValueError(f"Source manifest field {key} must use YYYY-MM-DD") from e


def _manifest_int(manifest: dict[str, object], key: str) -> int:
    value = manifest.get(key)
    if not isinstance(value, int):
        raise ValueError(f"Source manifest field {key} must be an integer")
    return value


def _iso_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as e:
        raise argparse.ArgumentTypeError("date must use YYYY-MM-DD") from e


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Generate an isolated synthetic first-session cohort for cold-start "
            "recommendation evaluation."
        )
    )
    _ = parser.add_argument(
        "--source-dataset-dir",
        type=Path,
        default=DEFAULT_SOURCE_DATASET_DIR,
    )
    _ = parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    _ = parser.add_argument("--users", type=int, default=DEFAULT_USER_COUNT)
    _ = parser.add_argument("--days", type=int, default=DEFAULT_DAYS)
    _ = parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    _ = parser.add_argument("--start-date", type=_iso_date, default=DEFAULT_START_DATE)
    _ = parser.add_argument("--feed-size", type=int, default=DEFAULT_FEED_SIZE)
    args = parser.parse_args()
    result = generate_and_publish(
        source_dataset_dir=cast(Path, args.source_dataset_dir),
        output_dir=cast(Path, args.output_dir),
        user_count=cast(int, args.users),
        days=cast(int, args.days),
        seed=cast(int, args.seed),
        start_date=cast(date, args.start_date),
        feed_size=cast(int, args.feed_size),
    )
    print(f"Cold-start stress dataset written to {result}")


if __name__ == "__main__":
    main()
