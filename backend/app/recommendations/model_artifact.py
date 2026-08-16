# pyright: reportMissingTypeStubs=false

import json
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import cast

import numpy as np
from lightgbm import Booster

from app.recommendations.offline_data import (
    ModelTrainingExample,
    read_manifest,
    sha256,
)
from app.recommendations.preprocessing import DatasetSplit
from app.recommendations.ranker import FeatureEncoder, encode_split

EXPECTED_MODEL_CLASSIFICATION = "synthetic_prototype_model"
EXPECTED_ARTIFACT_VERSION = "lightgbm-lambdarank-v1"


@dataclass(frozen=True)
class LoadedRankerArtifact:
    artifact_dir: Path
    encoder: FeatureEncoder
    booster: Booster
    best_iteration: int
    manifest: dict[str, object]

    def score_map(
        self,
        examples: list[ModelTrainingExample],
        *,
        split: DatasetSplit,
    ) -> dict[tuple[uuid.UUID, uuid.UUID], float]:
        encoded = encode_split(
            examples=examples,
            split=split,
            encoder=self.encoder,
        )
        raw_predictions = cast(
            object,
            self.booster.predict(
                encoded.features,
                num_iteration=self.best_iteration,
            ),
        )
        predictions = np.asarray(raw_predictions, dtype=np.float64)
        if predictions.ndim != 1 or len(predictions) != len(encoded.examples):
            raise ValueError("LightGBM returned an unexpected prediction shape")
        prediction_values = cast(list[float], predictions.tolist())
        return {
            (example.slate_id, example.recipe_id): score
            for example, score in zip(
                encoded.examples,
                prediction_values,
                strict=True,
            )
        }


def load_ranker_artifact(artifact_dir: Path) -> LoadedRankerArtifact:
    manifest = read_manifest(artifact_dir / "manifest.json")
    if manifest.get("classification") != EXPECTED_MODEL_CLASSIFICATION:
        raise ValueError("Unexpected recommendation model classification")
    if manifest.get("artifact_version") != EXPECTED_ARTIFACT_VERSION:
        raise ValueError("Unexpected recommendation model artifact version")
    _validate_artifact_file(artifact_dir, manifest, "model.txt")
    _validate_artifact_file(artifact_dir, manifest, "feature_schema.json")

    schema_payload = _read_json_object(artifact_dir / "feature_schema.json")
    encoder = FeatureEncoder.from_json(schema_payload)
    best_iteration = manifest.get("best_iteration")
    if not isinstance(best_iteration, int) or best_iteration < 1:
        raise ValueError("Model manifest has an invalid best iteration")

    booster = Booster(model_file=str(artifact_dir / "model.txt"))
    if booster.current_iteration() != best_iteration:
        raise ValueError("Saved model iteration count does not match its manifest")
    return LoadedRankerArtifact(
        artifact_dir=artifact_dir,
        encoder=encoder,
        booster=booster,
        best_iteration=best_iteration,
        manifest=manifest,
    )


def _validate_artifact_file(
    artifact_dir: Path,
    manifest: dict[str, object],
    filename: str,
) -> None:
    raw_files = manifest.get("files")
    if not isinstance(raw_files, dict):
        raise ValueError("Model manifest is missing file metadata")
    raw_metadata = cast(dict[object, object], raw_files).get(filename)
    if not isinstance(raw_metadata, dict):
        raise ValueError(f"Model manifest is missing metadata for {filename}")
    expected_hash = cast(dict[object, object], raw_metadata).get("sha256")
    if not isinstance(expected_hash, str):
        raise ValueError(f"Model manifest is missing the SHA-256 for {filename}")
    if sha256(artifact_dir / filename) != expected_hash:
        raise ValueError(f"Model artifact checksum mismatch for {filename}")


def _read_json_object(path: Path) -> dict[str, object]:
    try:
        raw_payload = cast(object, json.loads(path.read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError) as e:
        raise ValueError(f"Could not read model artifact JSON: {path}") from e
    if not isinstance(raw_payload, dict):
        raise ValueError(f"Model artifact JSON must contain an object: {path}")
    payload: dict[str, object] = {}
    for key, value in cast(dict[object, object], raw_payload).items():
        if not isinstance(key, str):
            raise ValueError(f"Model artifact JSON contains a non-string key: {path}")
        payload[key] = value
    return payload
