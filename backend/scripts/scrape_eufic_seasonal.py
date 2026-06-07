import argparse
import csv
import json
import re
import sys
from pathlib import Path
from typing import Final, Literal, Protocol

from playwright.sync_api import sync_playwright
from pydantic import TypeAdapter, ValidationError

from app.data.enums import CountryCode, Month, ProduceType

EUFIC_URL: Final = "https://www.eufic.org/en/explore-seasonal-fruit-and-vegetables-in-europe"
DEFAULT_RAW_OUTPUT: Final = Path("datasets/raw/eufic_seasonal.json")
DEFAULT_PROCESSED_OUTPUT: Final = Path("datasets/processed/eufic_seasonal.csv")
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

COUNTRIES: Final[dict[str, CountryCode]] = {
    "Austria": CountryCode.AUSTRIA,
    "Belgium": CountryCode.BELGIUM,
    "Bulgaria": CountryCode.BULGARIA,
    "Croatia": CountryCode.CROATIA,
    "Cyprus": CountryCode.CYPRUS,
    "Czech Republic": CountryCode.CZECH_REPUBLIC,
    "Denmark": CountryCode.DENMARK,
    "Estonia": CountryCode.ESTONIA,
    "Finland": CountryCode.FINLAND,
    "France": CountryCode.FRANCE,
    "Germany": CountryCode.GERMANY,
    "Greece": CountryCode.GREECE,
    "Hungary": CountryCode.HUNGARY,
    "Ireland": CountryCode.IRELAND,
    "Italy": CountryCode.ITALY,
    "Latvia": CountryCode.LATVIA,
    "Lithuania": CountryCode.LITHUANIA,
    "Luxembourg": CountryCode.LUXEMBOURG,
    "Malta": CountryCode.MALTA,
    "Netherlands": CountryCode.NETHERLANDS,
    "Poland": CountryCode.POLAND,
    "Portugal": CountryCode.PORTUGAL,
    "Romania": CountryCode.ROMANIA,
    "Slovakia": CountryCode.SLOVAKIA,
    "Slovenia": CountryCode.SLOVENIA,
    "Spain": CountryCode.SPAIN,
    "Sweden": CountryCode.SWEDEN,
    "United Kingdom": CountryCode.UNITED_KINGDOM,
}

MONTHS: Final = {month.name.title(): month for month in Month}
PRODUCE_TYPES: Final = {
    "Fruit": ProduceType.FRUIT,
    "Vegetable": ProduceType.VEGETABLE,
}
MEALDB_NAME_MAP: Final = {
    "aubergine": "eggplant",
    "coriander": "cilantro",
    "courgette": "zucchini",
    "rocket": "arugula",
    "spring onion": "green onion",
    "strawberry": "strawberries",
}
STORED_SUFFIX = re.compile(r"\s+\(stored\)$")

type RawData = dict[str, dict[str, list[tuple[str, str]]]]
type SeasonalRow = dict[str, str | int]
type PlaywrightLoadState = Literal["commit", "domcontentloaded", "load", "networkidle"]

FVLIST_ADAPTER: Final[TypeAdapter[RawData]] = TypeAdapter(
    dict[str, dict[str, list[tuple[str, str]]]]
)


class ScrapeArguments(argparse.Namespace):
    headed: bool = False
    timeout_ms: int = 30_000
    raw_output: Path = DEFAULT_RAW_OUTPUT
    processed_output: Path = DEFAULT_PROCESSED_OUTPUT


class LocatorCounter(Protocol):
    def count(self) -> int: ...


class ScrapePage(Protocol):
    def goto(
        self,
        url: str,
        *,
        wait_until: PlaywrightLoadState | None,
        timeout: float | None,
    ) -> object: ...

    def wait_for_function(self, expression: str, *, timeout: float | None) -> object: ...

    def locator(self, selector: str) -> LocatorCounter: ...

    def evaluate(self, expression: str) -> object: ...


def clean_name(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def mealdb_name(produce_name: str) -> str:
    base_name = STORED_SUFFIX.sub("", clean_name(produce_name))
    return MEALDB_NAME_MAP.get(base_name, base_name)


def extract_fvlist(page: ScrapePage, timeout_ms: int) -> RawData:
    _ = page.goto(EUFIC_URL, wait_until="domcontentloaded", timeout=timeout_ms)
    _ = page.wait_for_function(
        "() => typeof window.fvlist === 'object' && window.fvlist !== null",
        timeout=timeout_ms,
    )

    if page.locator("#sc").count() != 1 or page.locator("#sm").count() != 1:
        raise ValueError("EUFIC country or month filter is missing")

    return validate_fvlist(page.evaluate("() => window.fvlist"))


def validate_fvlist(value: object) -> RawData:
    try:
        return FVLIST_ADAPTER.validate_python(value)
    except ValidationError as error:
        raise ValueError("Malformed EUFIC fvlist data") from error


def transform_fvlist(data: RawData) -> tuple[list[SeasonalRow], list[str]]:
    if set(data) != set(PRODUCE_TYPES):
        raise ValueError(f"Unexpected EUFIC categories: {sorted(data)}")

    rows: dict[tuple[str, str, int, str, str], SeasonalRow] = {}
    covered_countries: set[str] = set()

    for source_type, produce_items in data.items():
        produce_type = PRODUCE_TYPES[source_type]

        for raw_name, occurrences in produce_items.items():
            produce_name = clean_name(raw_name)
            if not produce_name:
                raise ValueError(f"Malformed EUFIC produce record: {raw_name!r}")

            for occurrence in occurrences:
                raw_month, raw_country = occurrence
                month_name = raw_month.strip()
                country_name = raw_country.strip()
                try:
                    month = MONTHS[month_name]
                except KeyError as error:
                    raise ValueError(f"Unexpected EUFIC month: {raw_month!r}") from error

                country_code = COUNTRIES.get(country_name)
                if country_code is None:
                    continue

                covered_countries.add(country_name)
                key = (
                    country_code.value,
                    country_name,
                    month.value,
                    produce_type.value,
                    produce_name,
                )
                rows[key] = {
                    "country_code": country_code.value,
                    "country_name": country_name,
                    "month": month.value,
                    "produce_name": produce_name,
                    "produce_type": produce_type.value,
                    "source_name": "EUFIC",
                    "source_url": EUFIC_URL,
                    "mealdb_name": mealdb_name(produce_name),
                }

    if not rows:
        raise ValueError("EUFIC transformation produced no in-scope rows")

    warnings = [
        f"No EUFIC seasonal records found for {country_name}"
        for country_name in COUNTRIES
        if country_name not in covered_countries
    ]
    return [rows[key] for key in sorted(rows)], warnings


def write_raw_data(data: RawData, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as output_file:
        json.dump(data, output_file, ensure_ascii=False, indent=2, sort_keys=True)
        _ = output_file.write("\n")


def write_processed_csv(rows: list[SeasonalRow], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as output_file:
        writer = csv.writer(output_file)
        writer.writerow(CSV_FIELDS)
        for row in rows:
            writer.writerow([row[field] for field in CSV_FIELDS])


def parse_args() -> ScrapeArguments:
    parser = argparse.ArgumentParser(
        description="Extract and normalize EUFIC seasonal produce data."
    )
    _ = parser.add_argument("--headed", action="store_true", help="Show Chromium while scraping.")
    _ = parser.add_argument("--timeout-ms", type=int, default=30_000)
    _ = parser.add_argument("--raw-output", type=Path, default=DEFAULT_RAW_OUTPUT)
    _ = parser.add_argument("--processed-output", type=Path, default=DEFAULT_PROCESSED_OUTPUT)
    args = ScrapeArguments()
    _ = parser.parse_args(namespace=args)
    return args


def main() -> None:
    args = parse_args()
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=not args.headed)
        try:
            page = browser.new_page()
            data = extract_fvlist(page, args.timeout_ms)
        finally:
            browser.close()

    rows, warnings = transform_fvlist(data)
    write_raw_data(data, args.raw_output)
    write_processed_csv(rows, args.processed_output)

    for warning in warnings:
        print(f"Warning: {warning}", file=sys.stderr)
    print(f"Saved raw EUFIC data to {args.raw_output}")
    print(f"Saved {len(rows)} normalized rows to {args.processed_output}")


if __name__ == "__main__":
    main()
