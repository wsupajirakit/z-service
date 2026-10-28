"""/api/auth/{status,register,login,logout} (public paths) and /api/auth/password.

login/register still return the token in JSON (the legacy dashboard stores it) and also
set the HttpOnly session + CSRF cookies used by the new web UI (plan B4).

Hardening (security pass, 25 Oct):
* brute force: attempts per IP + username, and per IP alone, in sliding windows
* unknown usernames cost the same PBKDF2 time as known ones (no timing oracle)
* hashes with fewer rounds than the current setting are upgraded on the next login
* registration (first run only) is closed unless ZS_ALLOW_REGISTER is on (config.py)
* logout ends the session server-side (revocation.py); a password change ends every
  older session and hands the caller a fresh one
"""

import logging

from fastapi import APIRouter, Request, Response

from zservice.core.clock import now_iso
from zservice.core.errors import ApiError
from zservice.db.repos import users as users_repo
from zservice.security import revocation, sessions, tokens
from zservice.security.client_ip import client_ip
from zservice.security.middleware import BEARER, SESSION_COOKIE, session_token
from zservice.security.rate_limit import SlidingWindow

from . import config as auth_config
from .schemas import AuthRequest, PasswordChangeRequest

router = APIRouter()
log = logging.getLogger("zs.auth")

# NIST SP 800-63B rev. 4: single-factor passwords SHOULD be at least 15 characters; 12 is
# the floor here so a passphrase still fits comfortably. Existing passwords keep working.
MIN_PASSWORD_LEN = 12
_cfg = auth_config.get_settings()
_ATTEMPTS = SlidingWindow(_cfg.login_rate_limit, _cfg.login_rate_window_s)
_IP_ATTEMPTS = SlidingWindow(_cfg.login_ip_rate_limit, _cfg.login_rate_window_s)


def _guard(request: Request, username: str) -> None:
    ip = client_ip(request)
    wait = _IP_ATTEMPTS.hit(ip) or _ATTEMPTS.hit(f"{ip}|{username.lower()}")
    if wait is not None:
        raise ApiError(
            429,
            "auth.rate_limited",
            "too many attempts",
            params={"retry_after": int(wait)},
            headers={"Retry-After": str(wait)},
        )


def _registration_open() -> bool:
    return auth_config.get_settings().allow_register


def _check_new_password(password: str) -> None:
    if len(password) < MIN_PASSWORD_LEN:
        raise ApiError(
            400,
            "auth.password_short",
            f"password ต้องยาวอย่างน้อย {MIN_PASSWORD_LEN} ตัวอักษร",
            params={"min": MIN_PASSWORD_LEN},
        )


def _issue(response: Response, username: str) -> dict:
    token = tokens.create_token(username)
    sessions.set_session_cookies(response, token)
    return {"status": "ok", "token": token}


@router.get("/api/auth/status")
def auth_status():
    """Tells the login page whether to show Register (first run) or Login."""
    try:
        registered = users_repo.user_exists()
    except Exception as e:
        # Public route: the driver error names database hosts, so it stays in the log.
        log.error("auth status: user lookup failed: %s", e)
        raise ApiError(500, "auth.db_error", "DB error") from None
    return {"registered": registered, "registration_open": not registered and _registration_open()}


@router.post("/api/auth/register")
def auth_register(req: AuthRequest, request: Request, response: Response):
    username = req.username.strip()
    _guard(request, username)
    if not _registration_open():
        raise ApiError(
            403,
            "auth.registration_closed",
            "registration is closed (set ZS_ALLOW_REGISTER=1 for the first run)",
        )
    if not username or not req.password:
        raise ApiError(400, "auth.missing_fields", "ต้องกรอกทั้ง username และ password")
    _check_new_password(req.password)
    created = users_repo.user_create(username, tokens.hash_password(req.password), now_iso())
    if not created:
        raise ApiError(403, "auth.user_exists", "มี user อยู่แล้ว — สมัครซ้ำไม่ได้")
    return _issue(response, username)


@router.post("/api/auth/login")
def auth_login(req: AuthRequest, request: Request, response: Response):
    username = req.username.strip()
    _guard(request, username)
    user = users_repo.user_get(username)
    if not user:
        tokens.burn_password_check(req.password)
        raise ApiError(401, "auth.bad_credentials", "username หรือ password ไม่ถูกต้อง")
    if not tokens.verify_password(req.password, user["password_hash"]):
        raise ApiError(401, "auth.bad_credentials", "username หรือ password ไม่ถูกต้อง")
    if tokens.needs_rehash(user["password_hash"]):
        _upgrade_hash(user["username"], req.password)
    return _issue(response, user["username"])


def _upgrade_hash(username: str, password: str) -> None:
    try:
        users_repo.user_set_password(username, tokens.hash_password(password), now_iso())
    except Exception as e:  # the login itself is valid; retry the upgrade next time
        log.warning("password hash upgrade failed: %s", e)


@router.post("/api/auth/logout")
def auth_logout(request: Request, response: Response):
    """Clear the cookies and end the presented session on the server. Public on purpose
    (an expired session must still be able to clear its cookies), so the session is
    only revoked when the request proves it is ours: a Bearer header, or the HttpOnly
    cookie with a valid CSRF token. The legacy UI clears its own stored token."""
    token, source = session_token(request)
    payload = tokens.decode_token(token)
    proven = source == BEARER or (
        source == SESSION_COOKIE
        and sessions.csrf_failure(request.method, request.headers, token) is None
    )
    if payload is not None and proven:
        try:
            revocation.revoke_token(payload)
        except Exception as e:
            log.error("logout: revocation not stored: %s", e)
            raise ApiError(503, "auth.db_error", "DB error") from None
    sessions.clear_session_cookies(response)
    return {"status": "ok", "revoked": payload is not None and proven}


@router.post("/api/auth/password")
def auth_change_password(req: PasswordChangeRequest, request: Request, response: Response):
    """Change the password (behind the auth gate: needs a session, CSRF for cookies; no
    machine key scope reaches it). Every older session ends; the caller gets a new one."""
    token, _ = session_token(request)
    payload = tokens.decode_token(token) or {}
    username = str(payload.get("sub") or "")
    _guard(request, username)
    user = users_repo.user_get(username)
    if not user or not tokens.verify_password(req.current_password, user["password_hash"]):
        # 403, not 401: the session is fine, and clients treat 401 as "signed out".
        raise ApiError(403, "auth.wrong_current_password", "current password is wrong")
    _check_new_password(req.new_password)
    if req.new_password == req.current_password:
        raise ApiError(400, "auth.password_unchanged", "new password equals the current one")
    users_repo.user_set_password(username, tokens.hash_password(req.new_password), now_iso())
    revocation.revoke_all()
    return _issue(response, username)
