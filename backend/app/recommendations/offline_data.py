import csv
import hashlib
import json
import uuid
from dataclasses import dataclass, fields
from datetime import date
from pathlib import Path
from typing import cast

from app.data.enums import Allergen, CountryCode, DietPattern
from app.recommendations.preprocessing import DatasetSplit
from app.recommendations.ranking_types import RankingExample, RecipeContent
from app.recommendations.synthetic import (
    SYNTHETIC_GENERATOR_VERSION,
    RecipeFeature,
    SyntheticUser,
)


@dataclass(frozen=True)
class ModelTrainingExample:
    slate_id: uuid.UUID
    user_id: uuid.UUID
    recipe_id: uuid.UUID
    split: DatasetSplit
    persona_key: str
    relevance: int
    month: int
    seasonal_match_count: int
    cuisine_match: int
    user_country: str
    user_diet: str
    recipe_area: str
    recipe_category: str
    user_prior_impressions: int
    user_prior_opens: int
    user_prior_favourites: int
    user_prior_plans: int
    user_recipe_prior_impressions: int
    recipe_prior_impressions: int
    recipe_prior_positive_actions: int

    def ranking_example(self) -> RankingExample:
        return RankingExample(
            slate_id=self.slate_id,
            user_id=self.user_id,
            recipe_id=self.recipe_id,
            split=self.split,
            persona_key=self.persona_key,
            relevance=self.relevance,
            user_prior_impressions=self.user_prior_impressions,
            seasonal_match_count=self.seasonal_match_count,
            cuisine_match=self.cuisine_match,
        )


def validate_synthetic_dataset(
    dataset_dir: Path,
    *,
    required_files: tuple[str, ...],
    minimum_feed_size: int,
) -> dict[str, object]:
    manifest_path = dataset_dir / "manifest.json"
    manifest = read_manifest(manifest_path)
    if manifest.get("classification") != "synthetic":
        raise ValueError("Offline ML accepts only explicitly synthetic datasets")
    if manifest.get("generator_version") != SYNTHETIC_GENERATOR_VERSION:
        raise ValueError(
            " ".join(
                (
                    f"Expected generator version {SYNTHETIC_GENERATOR_VERSION},",
                    f"received {manifest.get('generator_version')}",
                )
            )
        )
    feed_size = manifest.get("feed_size")
    if not isinstance(feed_size, int) or feed_size < minimum_feed_size:
        raise ValueError(f"Dataset feed_size must be at least {minimum_feed_size}")

    files = manifest.get("files")
    if not isinstance(files, dict):
        raise ValueError("Dataset manifest is missing file checksums")
    files_by_name = cast(dict[str, object], files)
    for filename in required_files:
        file_metadata = files_by_name.get(filename)
        if not isinstance(file_metadata, dict):
            raise ValueError(f"Dataset manifest is missing metadata for {filename}")
        metadata = cast(dict[str, object], file_metadata)
        expected_hash = metadata.get("sha256")
        if not isinstance(expected_hash, str):
            raise ValueError(f"Dataset manifest is missing the SHA-256 for {filename}")
        if sha256(dataset_dir / filename) != expected_hash:
            raise ValueError(f"Dataset checksum mismatch for {filename}")
    return manifest


def read_manifest(path: Path) -> dict[str, object]:
    try:
        payload = cast(object, json.loads(path.read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError) as e:
        raise ValueError(f"Could not read dataset manifest: {path}") from e
    if not isinstance(payload, dict):
        raise ValueError("Dataset manifest must contain a JSON object")
    return cast(dict[str, object], payload)


def read_recipe_content(path: Path) -> list[RecipeContent]:
    recipes: list[RecipeContent] = []
    with path.open(newline="", encoding="utf-8") as input_file:
        for row in csv.DictReader(input_file):
            recipes.append(
                RecipeContent(
                    recipe_id=uuid.UUID(_value(row, "recipe_id")),
                    name=_value(row, "name"),
                    area=_value(row, "area") or "unknown",
                    category=_value(row, "category") or "unknown",
                    ingredient_names=tuple(
                        ingredient
                        for ingredient in _value(row, "ingredient_names").split("|")
                        if ingredient
                    ),
                )
            )
    if not recipes:
        raise ValueError("Dataset contains no recipe content records")
    return recipes


def read_recipe_features(path: Path) -> list[RecipeFeature]:
    recipes: list[RecipeFeature] = []
    with path.open(newline="", encoding="utf-8") as input_file:
        for row in csv.DictReader(input_file):
            seasonal_payload = _json_object(
                _value(row, "seasonal_match_counts"),
                field_name="seasonal_match_counts",
            )
            allergen_payload = _json_object(
                _value(row, "allergen_statuses"),
                field_name="allergen_statuses",
            )
            seasonal_match_counts: dict[tuple[str, int], int] = {}
            for raw_key, raw_count in seasonal_payload.items():
                country_code, separator, raw_month = raw_key.partition(":")
                if not separator or not isinstance(raw_count, int):
                    raise ValueError("Invalid seasonal_match_counts record")
                seasonal_match_counts[(country_code, int(raw_month))] = raw_count
            if not all(isinstance(value, str) for value in allergen_payload.values()):
                raise ValueError("Invalid allergen_statuses record")
            recipes.append(
                RecipeFeature(
                    recipe_id=uuid.UUID(_value(row, "recipe_id")),
                    name=_value(row, "name"),
                    area=_value(row, "area") or None,
                    category=_value(row, "category") or None,
                    ingredient_names=tuple(
                        ingredient
                        for ingredient in _value(row, "ingredient_names").split("|")
                        if ingredient
                    ),
                    seasonal_match_counts=seasonal_match_counts,
                    allergen_statuses=cast(dict[str, str], allergen_payload),
                )
            )
    if not recipes:
        raise ValueError("Dataset contains no recipe feature records")
    return recipes


def read_synthetic_users(path: Path) -> list[SyntheticUser]:
    users: list[SyntheticUser] = []
    with path.open(newline="", encoding="utf-8") as input_file:
        for row in csv.DictReader(input_file):
            users.append(
                SyntheticUser(
                    user_id=uuid.UUID(_value(row, "user_id")),
                    persona_key=_value(row, "persona_key"),
                    country_code=CountryCode(_value(row, "country_code")),
                    diet_pattern=DietPattern(_value(row, "diet_pattern")),
                    preferred_areas=tuple(
                        area for area in _value(row, "preferred_areas").split("|") if area
                    ),
                    allergens=tuple(
                        Allergen(allergen)
                        for allergen in _value(row, "allergens").split("|")
                        if allergen
                    ),
                    joined_on=date.fromisoformat(_value(row, "joined_on")),
                )
            )
    if not users:
        raise ValueError("Dataset contains no synthetic user records")
    return users


def read_training_examples(path: Path) -> list[ModelTrainingExample]:
    examples: list[ModelTrainingExample] = []
    with path.open(newline="", encoding="utf-8") as input_file:
        for row in csv.DictReader(input_file):
            examples.append(
                ModelTrainingExample(
                    slate_id=uuid.UUID(_value(row, "slate_id")),
                    user_id=uuid.UUID(_value(row, "user_id")),
                    recipe_id=uuid.UUID(_value(row, "recipe_id")),
                    split=DatasetSplit(_value(row, "split")),
                    persona_key=_value(row, "persona_key"),
                    relevance=int(_value(row, "relevance")),
                    month=int(_value(row, "month")),
                    seasonal_match_count=int(_value(row, "seasonal_match_count")),
                    cuisine_match=int(_value(row, "cuisine_match")),
                    user_country=_value(row, "user_country"),
                    user_diet=_value(row, "user_diet"),
                    recipe_area=_value(row, "recipe_area"),
                    recipe_category=_value(row, "recipe_category"),
                    user_prior_impressions=int(_value(row, "user_prior_impressions")),
                    user_prior_opens=int(_value(row, "user_prior_opens")),
                    user_prior_favourites=int(_value(row, "user_prior_favourites")),
                    user_prior_plans=int(_value(row, "user_prior_plans")),
                    user_recipe_prior_impressions=int(_value(row, "user_recipe_prior_impressions")),
                    recipe_prior_impressions=int(_value(row, "recipe_prior_impressions")),
                    recipe_prior_positive_actions=int(_value(row, "recipe_prior_positive_actions")),
                )
            )
    if not examples:
        raise ValueError("Dataset contains no training examples")
    return examples


def write_training_examples(
    path: Path,
    examples: list[ModelTrainingExample],
) -> None:
    if not examples:
        raise ValueError("Cannot write an empty training example file")
    rows: list[dict[str, object]] = []
    for example in examples:
        rows.append(
            {
                "slate_id": str(example.slate_id),
                "user_id": str(example.user_id),
                "recipe_id": str(example.recipe_id),
                "split": example.split.value,
                "persona_key": example.persona_key,
                "relevance": example.relevance,
                "month": example.month,
                "seasonal_match_count": example.seasonal_match_count,
                "cuisine_match": example.cuisine_match,
                "user_country": example.user_country,
                "user_diet": example.user_diet,
                "recipe_area": example.recipe_area,
                "recipe_category": example.recipe_category,
                "user_prior_impressions": example.user_prior_impressions,
                "user_prior_opens": example.user_prior_opens,
                "user_prior_favourites": example.user_prior_favourites,
                "user_prior_plans": example.user_prior_plans,
                "user_recipe_prior_impressions": example.user_recipe_prior_impressions,
                "recipe_prior_impressions": example.recipe_prior_impressions,
                "recipe_prior_positive_actions": example.recipe_prior_positive_actions,
            }
        )
    with path.open("w", newline="", encoding="utf-8") as output_file:
        writer = csv.DictWriter(
            output_file,
            fieldnames=[field.name for field in fields(ModelTrainingExample)],
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as input_file:
        for chunk in iter(lambda: input_file.read(65_536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _value(row: dict[str, str | None], key: str) -> str:
    value = row.get(key)
    if value is None:
        raise ValueError(f"Dataset row is missing required column {key}")
    return value


def _json_object(value: str, *, field_name: str) -> dict[str, object]:
    try:
        payload = cast(object, json.loads(value))
    except json.JSONDecodeError as e:
        raise ValueError(f"Dataset row contains invalid {field_name} JSON") from e
    if not isinstance(payload, dict):
        raise ValueError(f"Dataset row contains invalid {field_name}")
    result: dict[str, object] = {}
    for key, item in cast(dict[object, object], payload).items():
        if not isinstance(key, str):
            raise ValueError(f"Dataset row contains invalid {field_name}")
        result[key] = item
    return result
