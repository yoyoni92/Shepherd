"""Password hashing for app_users - stdlib pbkdf2 (no bcrypt/passlib dependency).

Shared by db/seed.py and fleet-api so seeding and login agree on the format
``pbkdf2_sha256$<iters>$<salt_hex>$<hash_hex>``.
"""
import hashlib
import hmac
import secrets

_ALGO = "pbkdf2_sha256"
_ITERATIONS = 200_000


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _ITERATIONS)
    return f"{_ALGO}${_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, iters, salt_hex, hash_hex = stored.split("$")
    except (ValueError, AttributeError):
        return False
    if algo != _ALGO:
        return False
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), int(iters))
    return hmac.compare_digest(digest.hex(), hash_hex)
