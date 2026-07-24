import re
from dataclasses import dataclass

from fastapi import Request

COUNTRY_HEADERS = (
    "cf-ipcountry",
    "x-country-code",
    "x-vercel-ip-country",
    "x-appengine-country",
)
REGION_HEADERS = (
    "cf-region-code",
    "x-region-code",
    "x-vercel-ip-country-region",
    "x-appengine-region",
)
REGION_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9_-]{0,19}$")


@dataclass(frozen=True)
class CoarseLocation:
    country_code: str
    region_code: str | None
    source: str = "coarse_header"


def infer_coarse_location(
    request: Request,
    *,
    trust_headers: bool = False,
) -> CoarseLocation | None:
    if not trust_headers:
        return None
    country_code = _first_valid_country_code(request)
    if country_code is None:
        return None

    return CoarseLocation(
        country_code=country_code,
        region_code=_first_valid_region_code(request),
    )


def _first_valid_country_code(request: Request) -> str | None:
    for header in COUNTRY_HEADERS:
        value = request.headers.get(header)
        if value is None:
            continue

        country_code = value.strip().upper()
        if len(country_code) == 2 and country_code.isalpha() and country_code != "XX":
            return country_code
    return None


def _first_valid_region_code(request: Request) -> str | None:
    for header in REGION_HEADERS:
        value = request.headers.get(header)
        if value is None:
            continue

        region_code = value.strip().upper()
        if REGION_PATTERN.fullmatch(region_code):
            return region_code
    return None
