from __future__ import annotations

import argparse
import json
import math
import platform
import statistics
import time
from dataclasses import asdict, dataclass
from http.client import HTTPResponse
from typing import Protocol, cast
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class BenchmarkResult:
    mode: str
    requests: int
    warmups: int
    month: int
    limit: int
    status_code: int
    returned_items: int
    eligible_items: int
    minimum_ms: float
    median_ms: float
    mean_ms: float
    p95_ms: float
    p99_ms: float
    maximum_ms: float
    durations_ms: list[float]


class BenchmarkArguments(Protocol):
    base_url: str
    email: str
    password: str
    mode: str
    requests: int
    warmups: int
    month: int
    limit: int
    timeout_seconds: float


def percentile(values: list[float], percentile_value: float) -> float:
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * percentile_value
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def decode_json_object(body: bytes) -> dict[str, object]:
    decoded = cast(object, json.loads(body))
    if not isinstance(decoded, dict):
        raise ValueError("Expected the response body to contain a JSON object")

    result: dict[str, object] = {}
    for key, value in cast(dict[object, object], decoded).items():
        if not isinstance(key, str):
            raise ValueError("Expected every response object key to be a string")
        result[key] = value
    return result


def require_string(payload: dict[str, object], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str):
        raise ValueError(f"Expected response field {key!r} to be a string")
    return value


def require_integer(payload: dict[str, object], key: str) -> int:
    value = payload.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"Expected response field {key!r} to be an integer")
    return value


def require_list(payload: dict[str, object], key: str) -> list[object]:
    value = payload.get(key)
    if not isinstance(value, list):
        raise ValueError(f"Expected response field {key!r} to be a list")
    return cast(list[object], value)


def request_json(
    url: str,
    *,
    method: str = "GET",
    payload: dict[str, object] | None = None,
    form: dict[str, str] | None = None,
    headers: dict[str, str] | None = None,
    timeout: float,
) -> tuple[int, dict[str, object]]:
    request_headers = dict(headers or {})
    body: bytes | None = None
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        request_headers["Content-Type"] = "application/json"
    elif form is not None:
        body = urlencode(form).encode("utf-8")
        request_headers["Content-Type"] = "application/x-www-form-urlencoded"
    request = Request(url, data=body, headers=request_headers, method=method)
    try:
        with cast(HTTPResponse, urlopen(request, timeout=timeout)) as response:
            return response.status, decode_json_object(response.read())
    except HTTPError as error:
        return error.code, decode_json_object(error.read())


def authenticate(base_url: str, email: str, password: str, timeout: float) -> str:
    registration_status, registration = request_json(
        f"{base_url}/users",
        method="POST",
        payload={
            "email": email,
            "password": password,
            "profile": {"country_code": "GB"},
        },
        timeout=timeout,
    )
    if registration_status not in {201, 409}:
        raise RuntimeError(f"Registration failed: {registration_status} {registration}")
    token_status, token = request_json(
        f"{base_url}/auth/token",
        method="POST",
        form={"username": email, "password": password},
        timeout=timeout,
    )
    if token_status != 200:
        raise RuntimeError(f"Authentication failed: {token_status} {token}")
    return require_string(token, "access_token")


def run_benchmark(args: BenchmarkArguments) -> dict[str, object]:
    access_token = authenticate(args.base_url, args.email, args.password, args.timeout_seconds)
    headers = {"Authorization": f"Bearer {access_token}"}
    endpoint = f"{args.base_url}/me/recommendations/feed?month={args.month}&limit={args.limit}"

    for _ in range(args.warmups):
        status_code, _ = request_json(
            endpoint,
            headers=headers,
            timeout=args.timeout_seconds,
        )
        if status_code != 200:
            raise RuntimeError(f"Warm-up request failed with {status_code}")

    durations: list[float] = []
    final_status = 0
    payload: dict[str, object] = {}
    for _ in range(args.requests):
        started = time.perf_counter_ns()
        final_status, payload = request_json(
            endpoint,
            headers=headers,
            timeout=args.timeout_seconds,
        )
        elapsed_ms = (time.perf_counter_ns() - started) / 1_000_000
        if final_status != 200:
            raise RuntimeError(f"Measured request failed with {final_status}")
        durations.append(elapsed_ms)

    items = require_list(payload, "items")
    result = BenchmarkResult(
        mode=args.mode,
        requests=args.requests,
        warmups=args.warmups,
        month=args.month,
        limit=args.limit,
        status_code=final_status,
        returned_items=len(items),
        eligible_items=require_integer(payload, "total"),
        minimum_ms=min(durations),
        median_ms=statistics.median(durations),
        mean_ms=statistics.fmean(durations),
        p95_ms=percentile(durations, 0.95),
        p99_ms=percentile(durations, 0.99),
        maximum_ms=max(durations),
        durations_ms=durations,
    )
    return {
        "environment": {
            "platform": platform.platform(),
            "python": platform.python_version(),
            "base_url": args.base_url,
        },
        "result": asdict(result),
    }


def parse_args() -> BenchmarkArguments:
    parser = argparse.ArgumentParser(
        description="Measure authenticated Seasonly recommendation response latency."
    )
    _ = parser.add_argument("--base-url", default="http://127.0.0.1:8001/api/v1")
    _ = parser.add_argument("--email", required=True)
    _ = parser.add_argument("--password", required=True)
    _ = parser.add_argument("--mode", choices=("cold", "warm"), required=True)
    _ = parser.add_argument("--requests", type=int, default=50)
    _ = parser.add_argument("--warmups", type=int, default=5)
    _ = parser.add_argument("--month", type=int, default=8)
    _ = parser.add_argument("--limit", type=int, default=24)
    _ = parser.add_argument("--timeout-seconds", type=float, default=10.0)
    args = cast(BenchmarkArguments, cast(object, parser.parse_args()))
    if args.requests < 1 or args.warmups < 0:
        parser.error("requests must be positive and warmups cannot be negative")
    return args


if __name__ == "__main__":
    print(json.dumps(run_benchmark(parse_args()), indent=2, sort_keys=True))
