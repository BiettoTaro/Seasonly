import argparse
import asyncio
import csv
import hashlib
import json
import shutil
import tempfile
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import asdict, fields
from datetime import date
from pathlib import Path
from typing import cast

from app.data.synthetic import SYNTHETIC_PERSONAS
from app.db.session import async_session, engine
from app.recommendations.catalog import load_recommendation_recipe_catalog
from app.recommendations.preprocessing import TrainingExample, build_training_examples
from app.recommendations.synthetic import (
    SYNTHETIC_GENERATOR_VERSION,
    InteractionEvent,
    RecipeFeature,
    SyntheticUser,
    generate_synthetic_users,
    simulate_interactions,
)

DEFAULT_USER_COUNT = 500
DEFAULT_DAYS = 90
DEFAULT_SEED = 20_260_724
DEFAULT_START_DATE = date(2026, 4, 26)
DEFAULT_FEED_SIZE = 20


class SyntheticRecommendationArguments(argparse.Namespace):
    users: int = DEFAULT_USER_COUNT
    days: int = DEFAULT_DAYS
    seed: int = DEFAULT_SEED
    start_date: date = DEFAULT_START_DATE
    feed_size: int = DEFAULT_FEED_SIZE
    output_dir: Path | None = None


async def async_main(args: SyntheticRecommendationArguments) -> Path:
    output_dir = (
        args.output_dir
        if args.output_dir is not None
        else Path(f"datasets/synthetic/runs/{SYNTHETIC_GENERATOR_VERSION}-seed-{args.seed}")
    )
    if output_dir.exists():
        raise FileExistsError(
            f"Output directory already exists: {output_dir}. "
            + "Choose a new directory to preserve prior generated evidence."
        )

    async with async_session() as session:
        recipes = await load_recommendation_recipe_catalog(session)
    if not recipes:
        raise ValueError(
            "No seasonally matchable recipes were found. Apply migrations and import "
            + "seasonal and TheMealDB data before generating personas."
        )

    users = generate_synthetic_users(
        user_count=args.users,
        start_date=args.start_date,
        days=args.days,
        seed=args.seed,
    )
    events = simulate_interactions(
        users=users,
        recipes=recipes,
        start_date=args.start_date,
        days=args.days,
        seed=args.seed,
        feed_size=args.feed_size,
    )
    examples = build_training_examples(
        users=users,
        recipes=recipes,
        events=events,
        start_date=args.start_date,
        days=args.days,
    )
    _publish_dataset(
        output_dir=output_dir,
        users=users,
        recipes=recipes,
        events=events,
        examples=examples,
        start_date=args.start_date,
        days=args.days,
        seed=args.seed,
        feed_size=args.feed_size,
    )
    return output_dir


async def run_and_dispose(args: SyntheticRecommendationArguments) -> Path:
    try:
        return await async_main(args)
    finally:
        await engine.dispose()


def _publish_dataset(
    *,
    output_dir: Path,
    users: list[SyntheticUser],
    recipes: list[RecipeFeature],
    events: list[InteractionEvent],
    examples: list[TrainingExample],
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
        _write_personas(temporary_dir / "personas.csv")
        _write_users(temporary_dir / "users.csv", users)
        _write_recipes(temporary_dir / "recipes.csv", recipes)
        _write_events(temporary_dir / "events.csv", events)
        _write_training_examples(
            temporary_dir / "training_examples.csv",
            examples,
        )
        data_files = sorted(temporary_dir.glob("*.csv"))
        manifest = {
            "classification": "synthetic",
            "generator_version": SYNTHETIC_GENERATOR_VERSION,
            "seed": seed,
            "start_date": start_date.isoformat(),
            "days": days,
            "adult_personas": len(SYNTHETIC_PERSONAS),
            "users": len(users),
            "actual_recipe_records": len(recipes),
            "events": len(events),
            "training_examples": len(examples),
            "feed_size": feed_size,
            "event_counts": dict(
                sorted(Counter(event.event_type.value for event in events).items())
            ),
            "split_counts": dict(
                sorted(Counter(example.split.value for example in examples).items())
            ),
            "persona_user_counts": dict(
                sorted(Counter(user.persona_key for user in users).items())
            ),
            "evaluation_restriction": (
                "Synthetic data may validate pipelines and train prototype models, "
                "but must not be reported as real-user effectiveness evidence."
            ),
            "files": {
                path.name: {"sha256": _sha256(path), "bytes": path.stat().st_size}
                for path in data_files
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


def _write_personas(path: Path) -> None:
    rows = [
        {
            "persona_key": persona.key,
            "label": persona.label,
            "description": persona.description,
            "countries": "|".join(country.value for country in persona.countries),
            "diet_pattern": persona.diet_pattern.value,
            "dietary_rules": "|".join(rule.value for rule in persona.dietary_rules),
            "allergens": "|".join(allergen.value for allergen in persona.allergens),
            "preferred_areas": "|".join(persona.preferred_areas),
            "activity_probability": persona.activity_probability,
            "open_probability": persona.open_probability,
            "favourite_probability": persona.favourite_probability,
            "plan_probability": persona.plan_probability,
            "variety_preference": persona.variety_preference,
        }
        for persona in SYNTHETIC_PERSONAS
    ]
    _write_csv(path, rows)


def _write_users(path: Path, users: list[SyntheticUser]) -> None:
    rows = [
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
    _write_csv(path, rows)


def _write_recipes(path: Path, recipes: list[RecipeFeature]) -> None:
    rows = [
        {
            "recipe_id": str(recipe.recipe_id),
            "name": recipe.name,
            "area": recipe.area or "",
            "category": recipe.category or "",
            "ingredient_names": "|".join(recipe.ingredient_names),
            "seasonal_match_counts": json.dumps(
                {
                    f"{country_code}:{month}": count
                    for (country_code, month), count in sorted(recipe.seasonal_match_counts.items())
                },
                sort_keys=True,
            ),
            "allergen_statuses": json.dumps(
                recipe.allergen_statuses,
                sort_keys=True,
            ),
            "is_synthetic": False,
        }
        for recipe in recipes
    ]
    _write_csv(path, rows)


def _write_events(path: Path, events: list[InteractionEvent]) -> None:
    rows = [
        {
            "event_id": str(event.event_id),
            "slate_id": str(event.slate_id) if event.slate_id is not None else "",
            "user_id": str(event.user_id),
            "recipe_id": str(event.recipe_id),
            "event_type": event.event_type.value,
            "source": event.source.value,
            "position": event.position if event.position is not None else "",
            "occurred_at": event.occurred_at.isoformat(),
            "is_synthetic": event.is_synthetic,
            "generator_version": event.generator_version,
        }
        for event in events
    ]
    _write_csv(path, rows)


def _write_training_examples(
    path: Path,
    examples: list[TrainingExample],
) -> None:
    rows: list[dict[str, object]] = []
    for example in examples:
        row = cast(dict[str, object], asdict(example))
        row["impression_event_id"] = str(example.impression_event_id)
        row["slate_id"] = str(example.slate_id)
        row["user_id"] = str(example.user_id)
        row["recipe_id"] = str(example.recipe_id)
        row["occurred_at"] = example.occurred_at.isoformat()
        row["split"] = example.split.value
        rows.append(row)
    _write_csv(
        path,
        rows,
        fieldnames=[field.name for field in fields(TrainingExample)],
    )


def _write_csv(
    path: Path,
    rows: Sequence[Mapping[str, object]],
    *,
    fieldnames: list[str] | None = None,
) -> None:
    resolved_fieldnames = fieldnames or list(rows[0]) if rows else fieldnames
    if not resolved_fieldnames:
        raise ValueError(f"Cannot write {path.name} without rows or field names")
    with path.open("w", newline="", encoding="utf-8") as output_file:
        writer = csv.DictWriter(
            output_file,
            fieldnames=resolved_fieldnames,
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as input_file:
        for chunk in iter(lambda: input_file.read(65_536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _iso_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as e:
        raise argparse.ArgumentTypeError("date must use YYYY-MM-DD") from e


def parse_args() -> SyntheticRecommendationArguments:
    parser = argparse.ArgumentParser(
        description=(
            "Generate deterministic synthetic recommendation personas and interactions "
            "against the actual imported Seasonly recipe catalog."
        )
    )
    _ = parser.add_argument("--users", type=int, default=DEFAULT_USER_COUNT)
    _ = parser.add_argument("--days", type=int, default=DEFAULT_DAYS)
    _ = parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    _ = parser.add_argument("--start-date", type=_iso_date, default=DEFAULT_START_DATE)
    _ = parser.add_argument("--feed-size", type=int, default=DEFAULT_FEED_SIZE)
    _ = parser.add_argument("--output-dir", type=Path)
    args = SyntheticRecommendationArguments()
    _ = parser.parse_args(namespace=args)
    return args


def main() -> None:
    args = parse_args()

    output_dir = asyncio.run(run_and_dispose(args))
    print(f"Generated synthetic recommendation dataset at {output_dir}")


if __name__ == "__main__":
    main()
