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
    }


def test_unknown_data_key_raises_value_error() -> None:
    with pytest.raises(ValueError, match="Unknown data key"):
        _ = get_data_registration(cast(DataKey, cast(object, "unknown")))
