import base64
import hashlib
import hmac
import json
import uuid
from datetime import UTC, datetime, timedelta
from typing import TypeGuard, cast

from app.core.config import settings

ACCESS_TOKEN_TYPE = "access"
JWT_ALGORITHM = "HS256"
type JsonValue = str | int | float | bool | None | list["JsonValue"] | dict[str, "JsonValue"]


class TokenDecodeError(ValueError):
    pass


def create_access_token(
    user_id: uuid.UUID,
    expires_delta: timedelta | None = None,
    now: datetime | None = None,
) -> str:
    issued_at = now or datetime.now(UTC)
    expires_at = issued_at + (
        expires_delta or timedelta(minutes=settings.auth_access_token_expire_minutes)
    )
    payload: dict[str, JsonValue] = {
        "sub": str(user_id),
        "type": ACCESS_TOKEN_TYPE,
        "iat": int(issued_at.timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    return _encode_jwt(payload)


def decode_access_token(token: str, now: datetime | None = None) -> uuid.UUID:
    payload = _decode_jwt(token)
    if payload.get("type") != ACCESS_TOKEN_TYPE:
        raise TokenDecodeError("Unexpected token type")

    expires_at = payload.get("exp")
    if not isinstance(expires_at, int):
        raise TokenDecodeError("Token expiry is missing")
    if expires_at < int((now or datetime.now(UTC)).timestamp()):
        raise TokenDecodeError("Token has expired")

    subject = payload.get("sub")
    if not isinstance(subject, str):
        raise TokenDecodeError("Token subject is missing")

    try:
        return uuid.UUID(subject)
    except ValueError as e:
        raise TokenDecodeError("Token subject is not a valid user id") from e


def _encode_jwt(payload: dict[str, JsonValue]) -> str:
    header: dict[str, JsonValue] = {"alg": JWT_ALGORITHM, "typ": "JWT"}
    signing_input = ".".join(
        (
            _base64url_encode_json(header),
            _base64url_encode_json(payload),
        )
    )
    signature = _sign(signing_input)
    return f"{signing_input}.{signature}"


def _decode_jwt(token: str) -> dict[str, JsonValue]:
    parts = token.split(".")
    if len(parts) != 3:
        raise TokenDecodeError("Invalid token structure")

    signing_input = ".".join(parts[:2])
    expected_signature = _sign(signing_input)
    if not hmac.compare_digest(parts[2], expected_signature):
        raise TokenDecodeError("Invalid token signature")

    try:
        header = _decode_json_object(parts[0])
        payload = _decode_json_object(parts[1])
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as e:
        raise TokenDecodeError("Invalid token payload") from e

    if header.get("alg") != JWT_ALGORITHM:
        raise TokenDecodeError("Unexpected token algorithm")
    return payload


def _sign(signing_input: str) -> str:
    signature = hmac.new(
        settings.auth_secret_key.encode("utf-8"),
        signing_input.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    return _base64url_encode(signature)


def _base64url_encode_json(value: dict[str, JsonValue]) -> str:
    return _base64url_encode(
        json.dumps(value, separators=(",", ":"), sort_keys=True).encode("utf-8")
    )


def _base64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _decode_json_object(value: str) -> dict[str, JsonValue]:
    padding = "=" * (-len(value) % 4)
    decoded = cast(object, json.loads(base64.urlsafe_b64decode(value + padding).decode("utf-8")))
    if not isinstance(decoded, dict):
        raise TokenDecodeError("Invalid token payload")

    json_object: dict[str, JsonValue] = {}
    for key, item in cast(dict[object, object], decoded).items():
        if not isinstance(key, str) or not _is_json_value(item):
            raise TokenDecodeError("Invalid token payload")
        json_object[key] = item
    return json_object


def _is_json_value(value: object) -> TypeGuard[JsonValue]:
    if value is None or isinstance(value, str | int | float | bool):
        return True
    if isinstance(value, list):
        return all(_is_json_value(item) for item in cast(list[object], value))
    if isinstance(value, dict):
        return all(
            isinstance(key, str) and _is_json_value(item)
            for key, item in cast(dict[object, object], value).items()
        )
    return False
