import pytest

from app.data.data_key import DataKey
from app.data.enums import DataTargetType
from app.data.registry import get_data_registration, get_data_targets


def test_data_key_targets_are_registered() -> None:
    targets = get_data_targets(DataKey.EU_SEASONAL_PRODUCE)

    assert {target.target_type for target in targets} == {
        DataTargetType.RAW_FILE,
        DataTargetType.NORMALIZED_TABLE,
    }


def test_unknown_data_key_raises_value_error() -> None:
    with pytest.raises(ValueError, match="Unknown data key"):
        get_data_registration("unknown")  # type: ignore[arg-type]
