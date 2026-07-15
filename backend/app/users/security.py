import hashlib
import hmac
import secrets

PASSWORD_HASH_ALGORITHM = "pbkdf2_sha256"
PASSWORD_HASH_ITERATIONS = 600_000
SALT_BYTES = 16
DUMMY_PASSWORD_SALT = bytes.fromhex("00000000000000000000000000000000")


def _dummy_password_hash() -> str:
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        b"seasonly-dummy-password",
        DUMMY_PASSWORD_SALT,
        PASSWORD_HASH_ITERATIONS,
    )
    return (
        f"{PASSWORD_HASH_ALGORITHM}${PASSWORD_HASH_ITERATIONS}$"
        f"{DUMMY_PASSWORD_SALT.hex()}${digest.hex()}"
    )


DUMMY_PASSWORD_HASH = _dummy_password_hash()


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(SALT_BYTES)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PASSWORD_HASH_ITERATIONS,
    )
    return f"{PASSWORD_HASH_ALGORITHM}${PASSWORD_HASH_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        algorithm, iterations_value, salt_hex, digest_hex = password_hash.split("$", 3)
        iterations = int(iterations_value)
        salt = bytes.fromhex(salt_hex)
        expected_digest = bytes.fromhex(digest_hex)
    except (ValueError, TypeError):
        return False

    if algorithm != PASSWORD_HASH_ALGORITHM:
        return False

    actual_digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        iterations,
    )
    return hmac.compare_digest(actual_digest, expected_digest)
