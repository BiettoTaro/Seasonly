import csv
from pathlib import Path

import pytest

from scripts.import_seasonal_data import CSV_FIELDS, batches, read_seasonal_csv


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as output_file:
        writer = csv.writer(output_file)
        writer.writerow(CSV_FIELDS)
        writer.writerows([row[field] for field in CSV_FIELDS] for row in rows)


def valid_row(**overrides: str) -> dict[str, str]:
    row = {
        "country_code": "GB",
        "country_name": "United Kingdom",
        "month": "6",
        "produce_name": "Strawberry",
        "produce_type": "fruit",
        "source_name": "Seasonly Demo",
        "source_url": "",
        "mealdb_name": "Strawberries",
    }
    row.update(overrides)
    return row


def test_read_seasonal_csv_normalizes_and_validates_rows(tmp_path: Path) -> None:
    input_path = tmp_path / "seasonal.csv"
    write_csv(input_path, [valid_row()])

    assert read_seasonal_csv(input_path) == [
        {
            "country_code": "GB",
            "country_name": "United Kingdom",
            "month": 6,
            "produce_name": "strawberry",
            "produce_type": "fruit",
            "source_name": "Seasonly Demo",
            "source_url": None,
            "mealdb_name": "strawberries",
        }
    ]


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"country_code": "US"}, "Invalid seasonal data"),
        ({"month": "13"}, "Invalid seasonal data"),
        ({"produce_type": "herb"}, "Invalid seasonal data"),
        ({"source_name": ""}, "Missing source_name"),
    ],
)
def test_read_seasonal_csv_rejects_invalid_rows(
    tmp_path: Path,
    overrides: dict[str, str],
    message: str,
) -> None:
    input_path = tmp_path / "seasonal.csv"
    write_csv(input_path, [valid_row(**overrides)])

    with pytest.raises(ValueError, match=message):
        _ = read_seasonal_csv(input_path)


def test_read_seasonal_csv_allows_same_name_with_different_types(tmp_path: Path) -> None:
    input_path = tmp_path / "seasonal.csv"
    write_csv(
        input_path,
        [
            valid_row(),
            valid_row(produce_type="vegetable"),
        ],
    )

    assert len(read_seasonal_csv(input_path)) == 2


def test_read_seasonal_csv_removes_watermelon_from_vegetables(tmp_path: Path) -> None:
    input_path = tmp_path / "seasonal.csv"
    write_csv(
        input_path,
        [
            valid_row(produce_name="Watermelon", produce_type="fruit", mealdb_name="Watermelon"),
            valid_row(
                produce_name="Watermelon",
                produce_type="vegetable",
                mealdb_name="Watermelon",
            ),
        ],
    )

    assert read_seasonal_csv(input_path) == [
        {
            "country_code": "GB",
            "country_name": "United Kingdom",
            "month": 6,
            "produce_name": "watermelon",
            "produce_type": "fruit",
            "source_name": "Seasonly Demo",
            "source_url": None,
            "mealdb_name": "watermelon",
        }
    ]


def test_read_seasonal_csv_deduplicates_identical_seasons(tmp_path: Path) -> None:
    input_path = tmp_path / "seasonal.csv"
    write_csv(input_path, [valid_row(), valid_row()])

    assert len(read_seasonal_csv(input_path)) == 1


def test_import_batches_limit_statement_size() -> None:
    assert batches(list(range(5)), batch_size=2) == [[0, 1], [2, 3], [4]]


def test_committed_synthetic_sample_is_importable() -> None:
    rows = read_seasonal_csv(Path("datasets/samples/seasonal_sample.csv"))

    assert len(rows) == 5
    assert {row["source_name"] for row in rows} == {"Seasonly Demo"}
