from typing import cast

import pytest

from app.data.data_key import DataKey
from app.data.data_target.recipes import RECIPE_CATEGORIES_TARGET, RECIPES_TARGET
from app.data.enums import DataTargetType
from app.data.registry import get_data_registration, get_data_targets


def test_data_key_targets_are_registered() -> None:
    targets = get_data_targets(DataKey.EU_SEASONAL_PRODUCE)

    assert {target.target_type for target in targets} == {
        DataTargetType.RAW_FILE,
        DataTargetType.NORMALIZED_TABLE,
    }


def test_themealdb_recipe_targets_match_persisted_tables() -> None:
    targets = get_data_targets(DataKey.THEMEALDB_RECIPES)

    assert {target.target_type for target in targets} == {DataTargetType.NORMALIZED_TABLE}
    assert RECIPE_CATEGORIES_TARGET in targets
    assert RECIPES_TARGET in targets
    assert {target.name for target in targets} == {
        "recipe_categories",
        "recipes",
        "ingredients",
        "recipe_ingredients",
        "tags",
        "recipe_tags",
        "recipe_allergen_assessments",
    }


def test_recommendation_catalog_keeps_pilot_events_out_of_ml_evidence() -> None:
    registration = get_data_registration(DataKey.RECOMMENDATION_EVENTS)
    targets_by_name = {target.name: target for target in registration.targets}

    assert registration.metadata.notes is not None
    assert "brief private-pilot activity" in registration.metadata.notes
    assert targets_by_name["recommendation_events"].description is not None
    assert (
        "excluded from current ML training" in targets_by_name["recommendation_events"].description
    )
    assert targets_by_name["recommendation_features"].description is not None
    assert (
        "only from explicitly synthetic" in targets_by_name["recommendation_features"].description
    )


def test_unknown_data_key_raises_value_error() -> None:
    with pytest.raises(ValueError, match="Unknown data key"):
        _ = get_data_registration(cast(DataKey, cast(object, "unknown")))
