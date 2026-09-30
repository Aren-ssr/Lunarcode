"""Small, dependency-light helpers for passwords, sessions, and trial access."""

import base64
import hashlib
import hmac
import secrets
import time

PBKDF2_ITERATIONS = 600_000
SESSION_SECONDS = 60 * 60 * 24 * 30
TRIAL_SECONDS = 20 * 60


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PBKDF2_ITERATIONS)
    return (
        "pbkdf2_sha256$"
        + str(PBKDF2_ITERATIONS)
        + "$"
        + base64.urlsafe_b64encode(salt).decode()
        + "$"
        + base64.urlsafe_b64encode(digest).decode()
    )


def verify_password(password: str, encoded: str) -> bool:
    try:
        scheme, rounds, salt_text, digest_text = encoded.split("$")
        if scheme != "pbkdf2_sha256":
            return False
        salt = base64.urlsafe_b64decode(salt_text.encode())
        expected = base64.urlsafe_b64decode(digest_text.encode())
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, int(rounds))
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def new_session_token() -> str:
    return secrets.token_urlsafe(32)


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def trial_is_active(expires_at: int, now: int | None = None) -> bool:
    return (int(time.time()) if now is None else now) < expires_at
