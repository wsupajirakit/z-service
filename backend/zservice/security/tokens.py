"""Single-user auth tokens: password hashing (PBKDF2) and HS256 JWT valid 24h (moved from
backend/auth.py, which re-exports these names).

Deliberately dependency-free — HS256 JWT is ~30 lines of stdlib hmac/hashlib,
so the deploy image needs no new packages. Secret comes from AUTH_SECRET.

There is no fallback secret: without AUTH_SECRET (>= 28 bytes) no token can be minted or
verified (every session is rejected), and the server refuses to boot (main.py startup
calls assert_configured). Offline tools that import main without serving never notice.
"""

import base64
import functools
import hashlib
import hmac
import json
import os
import time

from zservice.security import config as security_config

_MIN_SECRET_BYTES = 28  # 28 random characters carry well over 128 bits


def _secret() -> bytes:
    raw = security_config.get_settings().auth_secret.get_secret_value().encode()
    if len(raw) < _MIN_SECRET_BYTES:
        raise RuntimeError(f"AUTH_SECRET must be set to at least {_MIN_SECRET_BYTES} bytes")
    return raw


def assert_configured() -> None:
    """Raise at server startup when AUTH_SECRET is missing or too short."""
    _secret()


TOKEN_TTL_SECONDS = 24 * 60 * 60
# OWASP Password Storage Cheat Sheet: PBKDF2-HMAC-SHA256 with 600,000 iterations. Hashes
# with fewer rounds still verify and are upgraded on the next successful login.
_PBKDF2_ROUNDS = 600_000


def _b64e(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def _b64d(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


# --- password hashing (PBKDF2-HMAC-SHA256, salt stored alongside) -----------
def hash_password(password: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _PBKDF2_ROUNDS)
    return f"pbkdf2${_PBKDF2_ROUNDS}${_b64e(salt)}${_b64e(dk)}"


def needs_rehash(stored: str) -> bool:
    """True when a stored hash uses fewer rounds than the current setting."""
    try:
        scheme, rounds, _salt, _dk = stored.split("$")
        return scheme != "pbkdf2" or int(rounds) < _PBKDF2_ROUNDS
    except ValueError:
        return True


@functools.cache
def _dummy_hash() -> str:
    return hash_password(os.urandom(16).hex())


def burn_password_check(password: str) -> None:
    """Spend the same time as a real check when the username is unknown, so response
    timing does not reveal valid usernames."""
    verify_password(password, _dummy_hash())


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, rounds, salt_b64, dk_b64 = stored.split("$")
        if scheme != "pbkdf2":
            return False
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(), _b64d(salt_b64), int(rounds))
        return hmac.compare_digest(dk, _b64d(dk_b64))
    except Exception:
        return False


# --- JWT (HS256) ------------------------------------------------------------
def create_token(username: str) -> str:
    now = int(time.time())
    header = _b64e(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode())
    payload = _b64e(
        json.dumps(
            {"sub": username, "iat": now, "exp": now + TOKEN_TTL_SECONDS, "jti": _jti()},
            separators=(",", ":"),
        ).encode()
    )
    signing_input = f"{header}.{payload}".encode()
    sig = _b64e(hmac.new(_secret(), signing_input, hashlib.sha256).digest())
    return f"{header}.{payload}.{sig}"


def _jti() -> str:
    """Random token id, so logout can revoke this one token (revocation.py)."""
    return _b64e(os.urandom(12))


def decode_token(token: str):
    """Return the payload dict, or None if the token is invalid/expired."""
    try:
        header, payload, sig = token.split(".")
        expected = _b64e(
            hmac.new(_secret(), f"{header}.{payload}".encode(), hashlib.sha256).digest()
        )
        if not hmac.compare_digest(sig, expected):
            return None
        if json.loads(_b64d(header)) != {"alg": "HS256", "typ": "JWT"}:
            return None  # only the header this module writes
        data = json.loads(_b64d(payload))
        return data if _claims_ok(data, int(time.time())) else None
    except Exception:
        return None


CLOCK_SKEW_S = 60


def _claims_ok(data: object, now: int) -> bool:
    """A subject, issued in the past (small skew allowed), not yet expired, and never valid
    for longer than the TTL a token is issued with."""
    if not isinstance(data, dict):
        return False
    sub, iat, exp = data.get("sub"), data.get("iat"), data.get("exp")
    if not isinstance(sub, str) or not sub or not isinstance(iat, int) or not isinstance(exp, int):
        return False
    nbf = data.get("nbf", iat)
    if not isinstance(nbf, int) or nbf > now + CLOCK_SKEW_S or iat > now + CLOCK_SKEW_S:
        return False
    return now <= exp and exp - iat <= TOKEN_TTL_SECONDS
