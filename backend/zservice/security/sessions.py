"""Browser session cookies + CSRF (plan item B4; OWASP CSRF Prevention Cheat Sheet).

On login the server sets two cookies next to the JSON token the legacy dashboard reads:
* `__Host-zs_session` — the JWT; HttpOnly, Secure, SameSite=Strict, Path=/ (JavaScript can
  never read it, so XSS cannot steal it)
* `__Host-zs_csrf` — HMAC(secret, session token): a *signed* double-submit token bound to
  the session. Readable by the web UI, which echoes it in the X-ZS-CSRF header.

A state-changing request authenticated by the session cookie must carry a matching
X-ZS-CSRF header, must not be cross-site per Fetch Metadata, and its Origin (when sent)
must match the Host. Bearer tokens and the legacy JS-set z_token cookie keep working
unchanged; a Bearer header is never attached by the browser on its own.
"""

import base64
import hashlib
import hmac
from collections.abc import Mapping

from zservice.security import tokens

SESSION_COOKIE = "__Host-zs_session"
CSRF_COOKIE = "__Host-zs_csrf"
CSRF_HEADER = "x-zs-csrf"
UNSAFE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})
_BLOCKED_FETCH_SITES = frozenset({"cross-site", "same-site"})


def csrf_token_for(session_token: str) -> str:
    key = hashlib.sha256(b"zs-csrf|" + tokens._secret()).digest()
    mac = hmac.new(key, session_token.encode(), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(mac).rstrip(b"=").decode()


def set_session_cookies(response, token: str) -> None:
    max_age = tokens.TOKEN_TTL_SECONDS
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=max_age,
        path="/",
        secure=True,
        httponly=True,
        samesite="strict",
    )
    response.set_cookie(
        CSRF_COOKIE,
        csrf_token_for(token),
        max_age=max_age,
        path="/",
        secure=True,
        httponly=False,
        samesite="strict",
    )


def clear_session_cookies(response) -> None:
    for name in (SESSION_COOKIE, CSRF_COOKIE):
        response.delete_cookie(name, path="/", secure=True, samesite="strict")


def csrf_failure(method: str, headers: Mapping[str, str], token: str) -> str | None:
    """Why a cookie-authenticated request must be refused, or None when it may pass."""
    if method not in UNSAFE_METHODS:
        return None
    if headers.get("sec-fetch-site", "") in _BLOCKED_FETCH_SITES:
        return "cross-site request refused"
    origin = headers.get("origin")
    if origin and origin.split("://", 1)[-1].rstrip("/") != headers.get("host", ""):
        return "origin does not match"
    supplied = headers.get(CSRF_HEADER, "")
    if not supplied or not hmac.compare_digest(supplied, csrf_token_for(token)):
        return "missing or invalid CSRF token"
    return None
