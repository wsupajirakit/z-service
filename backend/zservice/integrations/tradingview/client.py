"""TvDatafeed construction, library tuning and the startup auth report.

Anonymous access ("unauthorized_user_token") is aggressively rate-limited by TradingView.
Set TV_USERNAME/TV_PASSWORD to log in, or TV_AUTH_TOKEN to inject a session token
directly (works even when password login is blocked by captcha).
"""

import concurrent.futures
import json
import logging
import time

from tvDatafeed import TvDatafeed

from . import config as tv_config
from .auth import STATE, current_auth_token

STARTUP_WARMUP_TIMEOUT_S = 20


def _masked(user: str) -> str:
    """The account in logs without revealing it: first character and the domain's first."""
    name, at, domain = user.partition("@")
    return f"{name[:1]}***{at}{domain[:1]}***" if at else f"{user[:1]}***"


def configure_library() -> None:
    # When TradingView soft-throttles it stalls responses instead of dropping the socket;
    # the lib's default 5s websocket read timeout then kills fetches that would have
    # succeeded a moment later. Raise it (name-mangled private attr).
    TvDatafeed._TvDatafeed__ws_timeout = tv_config.get_settings().ws_timeout
    # The anonymous constructor logs "nologin method" every time; with one instance per
    # fetch that is pure log spam. Real failures are ERROR level and remain.
    logging.getLogger("tvDatafeed.main").setLevel(logging.ERROR)


def make_tv() -> TvDatafeed:
    """Build a TvDatafeed. Every caller gets its OWN instance — get_hist keeps its
    websocket and session ids on the instance, so two threads sharing one (automate job +
    gold price poll + screener) clobber each other mid-read and the loser stalls until
    timeout. The anonymous constructor does no network I/O, so a fresh instance per
    fetch is essentially free."""
    t = TvDatafeed()
    tok = current_auth_token()
    if tok:
        t.token = tok
    return t


def warm_up_and_report() -> None:
    """Warm the login cache (fail fast on bad credentials) and print the active auth
    mode, so the startup log shows which one is in use."""
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            executor.submit(make_tv).result(timeout=STARTUP_WARMUP_TIMEOUT_S)
    except Exception as e:
        print(f"Initial TvDatafeed connection failed: {e}")
    cfg = tv_config.get_settings()
    user, manual = cfg.username, cfg.auth_token.get_secret_value()
    if user and STATE.token:
        mins = (STATE.exp - time.time()) / 60 if STATE.exp else 0
        who = _masked(user)
        print(f"TvDatafeed: logged in as {who} (token expires in {mins:.0f} min, auto re-login)")
    elif user and manual:
        print(f"TvDatafeed: login as {_masked(user)} FAILED — falling back to TV_AUTH_TOKEN")
    elif user:
        print(f"TvDatafeed: login as {_masked(user)} FAILED — falling back to anonymous")
    if manual and not (user and STATE.token):
        print(f"TvDatafeed: TV_AUTH_TOKEN applied{_expiry_note(manual)}")


def _expiry_note(token: str) -> str:
    try:
        exp = json.loads(jwt_payload(token))["exp"]
    except Exception:
        return ""
    mins = (exp - time.time()) / 60
    return f" (expires in {mins:.0f} min)" if mins > 0 else " — EXPIRED, refresh or remove it"


def jwt_payload(token: str) -> bytes:
    import base64

    return base64.urlsafe_b64decode(token.split(".")[1] + "==")
