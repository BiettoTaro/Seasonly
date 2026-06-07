import argparse
import asyncio
import csv
import uuid
from pathlib import Path
from typing import Final, TypedDict

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from app.data.enums import CountryCode, Month, ProduceType
from app.db.session import async_session, engine
from app.models import Produce, ProduceSeason

DEFAULT_INPUT: Final = Path("datasets/processed/eufic_seasonal.csv")
IMPORT_BATCH_SIZE: Final = 1_000
CSV_FIELDS: Final = (
    "country_code",
    "country_name",
    "month",
    "produce_name",
    "produce_type",
    "source_name",
    "source_url",
    "mealdb_name",
)


class SeasonalCsvRow(TypedDict):
    country_code: str
    country_name: str
    month: int
    produce_name: str
    produce_type: str
    source_name: str
    source_url: str | None
    mealdb_name: str | None


class ImportArguments(argparse.Namespace):
    input: Path = DEFAULT_INPUT


def read_seasonal_csv(input_path: Path) -> list[SeasonalCsvRow]:
    with input_path.open(newline="", encoding="utf-8") as input_file:
        reader = csv.DictReader(input_file)
        if tuple(reader.fieldnames or ()) != CSV_FIELDS:
            raise ValueError(f"Unexpected CSV fields: {reader.fieldnames}")

        rows = [
            _validate_row(row, line_number=line_number)
            for line_number, row in enumerate(reader, start=2)
        ]

    if not rows:
        raise ValueError("Seasonal produce CSV contains no rows")
    _validate_produce_consistency(rows)
    return _deduplicate_rows(rows)


def _validate_row(row: dict[str, str | None], line_number: int) -> SeasonalCsvRow:
    def required(field: str) -> str:
        value = row.get(field)
        if value is None or not value.strip():
            raise ValueError(f"Missing {field} on CSV line {line_number}")
        return value.strip()

    try:
        country_code = CountryCode(required("country_code").upper())
        month = Month(int(required("month")))
        produce_type = ProduceType(required("produce_type").lower())
    except ValueError as error:
        raise ValueError(f"Invalid seasonal data on CSV line {line_number}: {error}") from error

    source_url = (row.get("source_url") or "").strip() or None
    mealdb_name = (row.get("mealdb_name") or "").strip() or None
    return SeasonalCsvRow(
        country_code=country_code.value,
        country_name=required("country_name"),
        month=month.value,
        produce_name=required("produce_name").lower(),
        produce_type=produce_type.value,
        source_name=required("source_name"),
        source_url=source_url,
        mealdb_name=mealdb_name.lower() if mealdb_name is not None else None,
    )


def _validate_produce_consistency(rows: list[SeasonalCsvRow]) -> None:
    mealdb_names: dict[tuple[str, str], str | None] = {}
    for row in rows:
        key = (row["produce_name"], row["produce_type"])
        existing_mealdb_name = mealdb_names.setdefault(key, row["mealdb_name"])
        if existing_mealdb_name != row["mealdb_name"]:
            raise ValueError(f"Produce {row['produce_name']!r} has conflicting MealDB metadata")


def _deduplicate_rows(rows: list[SeasonalCsvRow]) -> list[SeasonalCsvRow]:
    unique_rows: dict[tuple[str, str, str, int, str], SeasonalCsvRow] = {}
    for row in rows:
        key = (
            row["produce_name"],
            row["produce_type"],
            row["country_code"],
            row["month"],
            row["source_name"],
        )
        existing_row = unique_rows.setdefault(key, row)
        if existing_row != row:
            raise ValueError(f"Conflicting seasonal records for {key}")
    return list(unique_rows.values())


def batches[T](values: list[T], batch_size: int = IMPORT_BATCH_SIZE) -> list[list[T]]:
    return [values[index : index + batch_size] for index in range(0, len(values), batch_size)]


async def import_rows(rows: list[SeasonalCsvRow]) -> tuple[int, int]:
    produce_values = {
        (row["produce_name"], row["produce_type"]): {
            "id": uuid.uuid4(),
            "name": row["produce_name"],
            "type": row["produce_type"],
            "mealdb_name": row["mealdb_name"],
        }
        for row in rows
    }

    async with async_session() as session:
        produce_statement = insert(Produce).values(list(produce_values.values()))
        produce_statement = produce_statement.on_conflict_do_update(
            constraint="uq_produce_name_type",
            set_={
                "mealdb_name": produce_statement.excluded.mealdb_name,
            },
        )
        _ = await session.execute(produce_statement)

        produce_result = await session.execute(
            select(Produce.id, Produce.name, Produce.type).where(
                Produce.name.in_({name for name, _ in produce_values})
            )
        )
        produce_ids = {
            (name, produce_type): produce_id
            for produce_id, name, produce_type in (row.tuple() for row in produce_result.all())
        }

        season_values = [
            {
                "id": uuid.uuid4(),
                "produce_id": produce_ids[(row["produce_name"], row["produce_type"])],
                "country_code": row["country_code"],
                "country_name": row["country_name"],
                "month": row["month"],
                "source_name": row["source_name"],
                "source_url": row["source_url"],
            }
            for row in rows
        ]
        for season_batch in batches(season_values):
            season_statement = insert(ProduceSeason).values(season_batch)
            season_statement = season_statement.on_conflict_do_update(
                constraint="uq_produce_seasons_produce_country_month_source",
                set_={
                    "country_name": season_statement.excluded.country_name,
                    "source_url": season_statement.excluded.source_url,
                },
            )
            _ = await session.execute(season_statement)
        await session.commit()

    return len(produce_values), len(season_values)


def parse_args() -> ImportArguments:
    parser = argparse.ArgumentParser(
        description="Import normalized seasonal produce CSV data into PostgreSQL."
    )
    _ = parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    args = ImportArguments()
    _ = parser.parse_args(namespace=args)
    return args


async def async_main(input_path: Path) -> None:
    try:
        rows = read_seasonal_csv(input_path)
        produce_count, season_count = await import_rows(rows)
        print(f"Imported {produce_count} produce records and {season_count} seasonal records")
    finally:
        await engine.dispose()


def main() -> None:
    args = parse_args()
    asyncio.run(async_main(args.input))


if __name__ == "__main__":
    main()
