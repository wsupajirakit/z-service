"""The auth gate.

Everything is protected except the login page, its assets and the auth endpoints. It is a
middleware, not per-route dependencies, so a newly added route can never be left
unprotected by accident. Order of checks: public path -> machine key (zsk_ / legacy
PULL_KEY) -> browser session (Bearer JWT, legacy z_token cookie or HttpOnly cookie).

A session token must verify, not be expired and not be revoked (revocation.py).
State-changing requests are refused when the only credential is a cookie the browser
attaches on its own, unless that cookie is the HttpOnly session with a valid CSRF token:
the legacy JS-set `z_token` cookie is SameSite=Lax, which a sibling subdomain ("same-site")
can still ride, and the legacy dashboard sends a Bearer header on every API call anyway.
"""

from fastapi.responses import JSONResponse, RedirectResponse

from zservice.domains.health.routes import PATH as HEALTH_PATH
from zservice.security import config as security_config
from zservice.security import revocation, sessions, tokens
from zservice.security.client_ip import client_ip
from zservice.security.machine import registry
from zservice.web.paths import APP_BASE, APP_LOGIN, APP_PUBLIC_PATHS, APP_PUBLIC_PREFIXES

PUBLIC_PATHS = {
    "/login",
    "/login.html",
    "/api/auth/status",
    "/api/auth/login",
    "/api/auth/register",
    "/api/auth/logout",  # clearing cookies must work even with an expired session
    "/favicon.ico",
    "/favicon.svg",
    "/theme-init.js",  # the sign-in page applies the saved theme and language before paint
    HEALTH_PATH,
    # /docs and /openapi.json are no longer public (plan B6): they need a session.
}
# Build assets must load so a sign-in page can render: the legacy UI's and the new UI's.
# Inbound events authenticate by their Standard Webhooks signature, not by a session.
PUBLIC_PREFIXES = ("/assets/", "/static/", "/api/events/inbound/", *APP_PUBLIC_PREFIXES)

BEARER, LEGACY_COOKIE, SESSION_COOKIE = "bearer", "legacy_cookie", "session_cookie"


def is_public(path: str) -> bool:
    # A path with dot segments or empty segments could match a public prefix yet resolve
    # elsewhere ("/assets/../index.html"): such a path is never public.
    if "//" in path or any(seg in (".", "..") for seg in path.split("/")):
        return False
    return path in PUBLIC_PATHS or path in APP_PUBLIC_PATHS or path.startswith(PUBLIC_PREFIXES)


def _is_preflight(request) -> bool:
    """A CORS preflight, and only while cross-origin access is configured (dev servers)."""
    return (
        request.method == "OPTIONS"
        and bool(request.headers.get("access-control-request-method"))
        and bool(security_config.get_settings().cors_origins)
    )


def _presents_legacy_key(request) -> bool:
    return bool(
        request.headers.get("x-pull-key", "").strip()
        or (request.query_params.get("pull_key") or "").strip()
    )


def login_redirect(path: str) -> RedirectResponse:
    """Each UI signs in on its own page: the new UI at APP_LOGIN, the legacy one at /login."""
    target = APP_LOGIN if path.startswith(APP_BASE) else "/login"
    return RedirectResponse(url=target, status_code=302)


async def require_auth(request, call_next):
    path = request.url.path
    if _is_preflight(request) or is_public(path):
        return await call_next(request)

    machine = registry.current()
    decision = machine.authorize(request.method, path, request.headers, request.query_params)
    # A valid key is decided above and never counted; only wrong keys feed the guess limit.
    wrong_key = (decision is not None and decision.status == 401) or (
        decision is None and _presents_legacy_key(request)
    )
    if wrong_key:
        wait = machine.guesses.hit(client_ip(request))
        if wait is not None:
            return JSONResponse(
                {"detail": "too many wrong keys"},
                status_code=429,
                headers={"Retry-After": str(wait)},
            )
    if decision is not None:
        ip = client_ip(request)
        if not decision.allowed:
            machine.audit.record(decision, request.method, path, ip, decision.status)
            headers = {"Retry-After": str(decision.retry_after)} if decision.retry_after else None
            return JSONResponse(
                {"detail": decision.reason}, status_code=decision.status, headers=headers
            )
        response = await call_next(request)
        machine.audit.record(decision, request.method, path, ip, response.status_code)
        return response

    token, source = session_token(request)
    payload = tokens.decode_token(token)
    if payload is None or revocation.is_revoked(payload):
        if path.startswith("/api/"):
            return JSONResponse({"detail": "Unauthorized"}, status_code=401)
        # Browser hitting a UI page without a session -> that UI's sign-in page.
        return login_redirect(path)
    reason = _cookie_write_refusal(request, token, source)
    if reason:
        return JSONResponse({"detail": reason}, status_code=403)
    return await call_next(request)


def session_token(request) -> tuple[str, str]:
    """(token, where it came from). Bearer header first, then the legacy JS-set z_token
    cookie, then the HttpOnly session cookie (plan B4)."""
    header = request.headers.get("authorization", "")
    if header.lower().startswith("bearer ") and header[7:].strip():
        return header[7:].strip(), BEARER
    legacy = request.cookies.get("z_token", "")
    if legacy:
        return legacy, LEGACY_COOKIE
    return request.cookies.get(sessions.SESSION_COOKIE, ""), SESSION_COOKIE


def _cookie_write_refusal(request, token: str, source: str) -> str | None:
    if source == BEARER:
        return None  # a browser never attaches an Authorization header on its own
    if source == LEGACY_COOKIE:
        if request.method in sessions.UNSAFE_METHODS:
            return "state-changing requests need the Authorization header"
        return None
    return sessions.csrf_failure(request.method, request.headers, token)
