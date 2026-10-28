"""TradingView auth token: mode selection, disk cache and sign-in with backoff (state in
STATE: token, expiry, retry time and its lock).

Login tokens live ~4h. The current one is cached on disk so restarts (dev --reload
restarts constantly) reuse it instead of signing in again — frequent sign-ins from one IP
trip TradingView's recaptcha and block login.
"""

import base64
import contextlib
import json
import os
import threading
import time
from pathlib import Path

from zservice.core import runtime
from zservice.core.logging import logger

from . import config as tv_config
from .mode import get_tv_mode_setting

BACKEND_DIR = Path(__file__).resolve().parents[3]  # same folder main.py used before
# The cache holds a live TradingView session token: it lives in ZS_STATE_DIR (the image sets
# a directory owned by the non-root app user) and is written owner-only (0600).
STATE_DIR = Path(runtime.get_settings().state_dir or BACKEND_DIR)
TOKEN_CACHE_FILE = str(STATE_DIR / ".tv_token_cache.json")
REFRESH_MARGIN_S = 600  # re-login when the token has less than this left
RECAPTCHA_BACKOFF_S = 3600
LOGIN_BACKOFF_S = 600
_SIGNIN_URL = "https://www.tradingview.com/accounts/signin/"
# tvdatafeed's own bare POST is rejected with {"code": "rate_limit"}: TradingView blocks
# requests without a real browser User-Agent (verified live against the endpoint).
_BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)


def load_cached_login() -> tuple[str | None, float]:
    try:
        with open(TOKEN_CACHE_FILE) as f:
            d = json.load(f)
        tok, exp = d.get("token"), float(d.get("exp", 0))
        if tok and exp - time.time() > REFRESH_MARGIN_S:
            return tok, exp
    except Exception:  # noqa: S110 — no or unreadable cache means sign in again
        pass
    return None, 0.0


def save_cached_login(tok: str, exp: float) -> None:
    """Write owner-only, via a temp file + rename so a crash never leaves half a file."""
    tmp = f"{TOKEN_CACHE_FILE}.tmp"
    try:
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as f:
            json.dump({"token": tok, "exp": exp}, f)
        os.chmod(tmp, 0o600)  # O_CREAT's mode does not apply to an existing file
        os.replace(tmp, TOKEN_CACHE_FILE)
    except Exception:
        with contextlib.suppress(OSError):
            os.remove(tmp)


def jwt_exp(tok: str) -> float:
    try:
        payload = json.loads(base64.urlsafe_b64decode(tok.split(".")[1] + "=="))
        return float(payload["exp"])
    except Exception:
        return 0.0


def signin(username: str, password: str) -> tuple[str | None, str | None]:
    """Sign in; return (auth_token, None) or (None, error_code)."""
    try:
        import requests

        r = requests.post(
            _SIGNIN_URL,
            data={"username": username, "password": password, "remember": "on"},
            headers={
                "Referer": "https://www.tradingview.com",
                "Origin": "https://www.tradingview.com",
                "User-Agent": _BROWSER_UA,
            },
            timeout=15,
        )
        j = r.json()
        tok = (j.get("user") or {}).get("auth_token")
        if tok:
            return tok, None
        detail = str({k: v for k, v in j.items() if k != "user"})[:200]
        logger.warning(f"TradingView signin rejected: {detail}")
        return None, (j.get("code") or "rejected")
    except Exception as e:
        logger.warning(f"TradingView signin failed: {e}")
    return None, "network"


class TvAuthState:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.token, self.exp = load_cached_login()  # survive restarts without re-signin
        self.next_retry = 0.0  # backoff after a failed login (sign-in rate limit)


STATE = TvAuthState()


def current_auth_token() -> str | None:
    """Best available token for the selected tv_login_mode (1 login, 2 token, 3 none)."""
    mode = get_tv_mode_setting()
    if mode == 1:
        return _login_mode_token()
    if mode == 2:
        manual = tv_config.get_settings().auth_token.get_secret_value() or None
        if not manual:
            logger.warning(
                "TV login mode set to 2 (Pure Token) but TV_AUTH_TOKEN is not set in env."
            )
        return manual
    return None  # mode 3: classic anonymous


def _login_mode_token() -> str | None:
    cfg = tv_config.get_settings()
    username, password = cfg.username, cfg.password.get_secret_value()
    if not (username and password):
        logger.warning(
            "TV login mode set to 1 (User+Pass) but TV_USERNAME or TV_PASSWORD is not set in env."
        )
        return None
    now = time.time()
    with STATE.lock:
        if STATE.token and (STATE.exp == 0 or STATE.exp - now > REFRESH_MARGIN_S):
            return STATE.token
        if now >= STATE.next_retry:
            tok, err = signin(username, password)
            if tok:
                STATE.token, STATE.exp = tok, jwt_exp(tok)
                save_cached_login(tok, STATE.exp)
                return tok
            wait = RECAPTCHA_BACKOFF_S if err == "recaptcha_required" else LOGIN_BACKOFF_S
            STATE.next_retry = now + wait
            logger.warning(
                f"TradingView login failed ({err}) — falling back to anonymous, "
                f"next attempt in {wait // 60} min"
            )
        elif STATE.token and (STATE.exp == 0 or STATE.exp > now):
            return STATE.token
    return None


def reset_login() -> None:
    """Forget the current token and its disk cache (after the login mode changes)."""
    with STATE.lock:
        STATE.token, STATE.exp, STATE.next_retry = None, 0.0, 0.0
        if os.path.exists(TOKEN_CACHE_FILE):
            # A stale cache only costs one extra sign-in.
            with contextlib.suppress(Exception):
                os.remove(TOKEN_CACHE_FILE)


def set_token(token: str, exp: float) -> None:
    with STATE.lock:
        STATE.token, STATE.exp = token, exp
        save_cached_login(token, exp)


def token_status() -> dict:
    """Expiry info for the current token (never the token itself)."""
    with STATE.lock:
        if STATE.token and STATE.exp > time.time():
            mins_left = (STATE.exp - time.time()) / 60
            return {"status": "active", "expires_in_minutes": round(mins_left, 1)}
        if STATE.token:
            return {"status": "expired"}
        return {"status": "none"}
