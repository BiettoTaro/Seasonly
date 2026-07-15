import csv
import json
from pathlib import Path
from typing import cast

import pytest

from scripts.scrape_eufic_seasonal import (
    CSV_FIELDS,
    EUFIC_URL,
    PlaywrightLoadState,
    clean_name,
    extract_fvlist,
    mealdb_name,
    transform_fvlist,
    validate_fvlist,
    write_processed_csv,
    write_raw_data,
)


class FakeLocator:
    def __init__(self, count: int) -> None:
        self._count: int = count

    def count(self) -> int:
        return self._count


class FakePage:
    def __init__(self, data: object, locator_count: int = 1) -> None:
        self.data: object = data
        self.locator_count: int = locator_count
        self.goto_calls: list[tuple[str, PlaywrightLoadState, float]] = []
        self.wait_calls: list[tuple[str, float]] = []
        self.locator_calls: list[str] = []

    def goto(
        self,
        url: str,
        *,
        wait_until: PlaywrightLoadState | None,
        timeout: float | None,
    ) -> object:
        assert wait_until is not None
        assert timeout is not None
        self.goto_calls.append((url, wait_until, timeout))
        return None

    def wait_for_function(self, expression: str, *, timeout: float | None) -> object:
        assert timeout is not None
        self.wait_calls.append((expression, timeout))
        return None

    def locator(self, selector: str) -> FakeLocator:
        self.locator_calls.append(selector)
        return FakeLocator(self.locator_count)

    def evaluate(self, expression: str) -> object:
        assert expression == "() => window.fvlist"
        return self.data


def sample_fvlist() -> dict[str, dict[str, list[tuple[str, str]]]]:
    return {
        "Fruit": {
            " Strawberry ": [
                ("June", "United Kingdom"),
                ("June", "United Kingdom"),
                ("July", "Switzerland"),
            ],
            "Apple (stored)": [("January", "Italy")],
        },
        "Vegetable": {
            "  Courgette ": [(" June ", " Italy ")],
            "Tomato": [("June", "Italy")],
            "Watermelon": [("August", "Spain")],
        },
    }


def test_clean_name_and_mealdb_aliases() -> None:
    assert clean_name("  Apple   (stored) ") == "apple (stored)"
    assert mealdb_name("Apple (stored)") == "apple"
    assert mealdb_name("Courgette") == "zucchini"
    assert mealdb_name("Strawberry") == "strawberries"
    assert mealdb_name("Tomato") == "tomato"


def test_transform_filters_deduplicates_sorts_and_warns() -> None:
    rows, warnings = transform_fvlist(sample_fvlist())

    assert len(rows) == 4
    assert rows == sorted(
        rows,
        key=lambda row: (
            row["country_code"],
            row["country_name"],
            row["month"],
            row["produce_type"],
            row["produce_name"],
        ),
    )
    assert {
        (
            row["country_code"],
            row["country_name"],
            row["month"],
            row["produce_name"],
            row["produce_type"],
            row["source_name"],
            row["source_url"],
            row["mealdb_name"],
        )
        for row in rows
    } == {
        ("GB", "United Kingdom", 6, "strawberry", "fruit", "EUFIC", EUFIC_URL, "strawberries"),
        ("IT", "Italy", 1, "apple (stored)", "fruit", "EUFIC", EUFIC_URL, "apple"),
        ("IT", "Italy", 6, "courgette", "vegetable", "EUFIC", EUFIC_URL, "zucchini"),
        ("IT", "Italy", 6, "tomato", "vegetable", "EUFIC", EUFIC_URL, "tomato"),
    }
    assert "No EUFIC seasonal records found for Slovenia" in warnings
    assert not any("Italy" in warning or "United Kingdom" in warning for warning in warnings)


def test_transform_removes_watermelon_from_vegetables() -> None:
    rows, _ = transform_fvlist(
        {
            "Fruit": {"Watermelon": [("August", "Spain")]},
            "Vegetable": {"Watermelon": [("August", "Spain")]},
        }
    )

    assert [(row["produce_name"], row["produce_type"]) for row in rows] == [("watermelon", "fruit")]


@pytest.mark.parametrize(
    ("data", "message"),
    [
        ({"Fruit": {}}, "Unexpected EUFIC categories"),
        ({"Fruit": {}, "Vegetable": {"tomato": [["Smarch", "Italy"]]}}, "Unexpected EUFIC month"),
        ({"Fruit": {}, "Vegetable": {"tomato": [["June", "Switzerland"]]}}, "no in-scope rows"),
    ],
)
def test_transform_rejects_broken_source_data(data: object, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        _ = transform_fvlist(validate_fvlist(data))


def test_validate_fvlist_rejects_malformed_occurrence() -> None:
    with pytest.raises(ValueError, match="Malformed EUFIC fvlist data"):
        _ = validate_fvlist({"Fruit": {}, "Vegetable": {"tomato": [["June"]]}})


def test_extract_fvlist_uses_playwright_page_contract() -> None:
    page = FakePage(sample_fvlist())

    result = extract_fvlist(page, timeout_ms=12_345)

    assert result == sample_fvlist()
    assert page.goto_calls == [(EUFIC_URL, "domcontentloaded", 12_345)]
    assert len(page.wait_calls) == 1
    assert page.locator_calls == ["#sc", "#sm"]


def test_extract_fvlist_rejects_missing_filters() -> None:
    page = FakePage(sample_fvlist(), locator_count=0)

    with pytest.raises(ValueError, match="filter is missing"):
        _ = extract_fvlist(page, timeout_ms=1_000)


def test_write_outputs(tmp_path: Path) -> None:
    data = sample_fvlist()
    rows, _ = transform_fvlist(data)
    raw_path = tmp_path / "raw" / "eufic.json"
    csv_path = tmp_path / "processed" / "eufic.csv"

    write_raw_data(data, raw_path)
    write_processed_csv(rows, csv_path)

    reloaded_data = cast(object, json.loads(raw_path.read_text(encoding="utf-8")))
    assert validate_fvlist(reloaded_data) == data
    with csv_path.open(newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        assert tuple(reader.fieldnames or ()) == CSV_FIELDS
        assert len(list(reader)) == 4


def test_committed_sample_is_synthetic() -> None:
    sample_path = Path("datasets/samples/seasonal_sample.csv")

    with sample_path.open(newline="", encoding="utf-8") as sample_file:
        rows = list(csv.DictReader(sample_file))

    assert 5 <= len(rows) <= 10
    assert {row["source_name"] for row in rows} == {"Seasonly Demo"}
    assert {row["source_url"] for row in rows} == {""}
