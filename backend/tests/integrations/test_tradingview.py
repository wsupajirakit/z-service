"""TradingView auth state, token routes and throttle — offline (no sign-in, no sockets)."""

import base64
import json
import time

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from zservice.integrations.tradingview import auth, mode, throttle


def _jwt(exp: float) -> str:
    payload = base64.urlsafe_b64encode(json.dumps({"exp": exp}).encode()).decode().rstrip("=")
    return f"h.{payload}.s"


@pytest.fixture
def clean_auth(monkeypatch, tmp_path):
    monkeypatch.setattr(auth, "TOKEN_CACHE_FILE", str(tmp_path / "cache.json"))
    auth.STATE.token, auth.STATE.exp, auth.STATE.next_retry = None, 0.0, 0.0
    yield auth.STATE
    auth.STATE.token, auth.STATE.exp, auth.STATE.next_retry = None, 0.0, 0.0


def test_jwt_exp_and_garbage():
    assert auth.jwt_exp(_jwt(1234.0)) == 1234.0
    assert auth.jwt_exp("not-a-jwt") == 0.0


def test_mode_2_uses_env_token_and_mode_3_is_anonymous(monkeypatch, env, clean_auth):
    env(TV_AUTH_TOKEN="tok")
    monkeypatch.setattr(auth, "get_tv_mode_setting", lambda: 2)
    assert auth.current_auth_token() == "tok"
    monkeypatch.setattr(auth, "get_tv_mode_setting", lambda: 3)
    assert auth.current_auth_token() is None


def test_mode_1_backs_off_after_a_failed_signin(monkeypatch, env, clean_auth):
    calls = []
    env(TV_USERNAME="u", TV_PASSWORD="p")
    monkeypatch.setattr(auth, "get_tv_mode_setting", lambda: 1)
    monkeypatch.setattr(
        auth, "signin", lambda u, p: calls.append(1) or (None, "recaptcha_required")
    )
    assert auth.current_auth_token() is None
    assert auth.current_auth_token() is None  # inside the backoff window: no second sign-in
    assert len(calls) == 1
    assert clean_auth.next_retry - time.time() > auth.RECAPTCHA_BACKOFF_S - 5


def test_token_routes_and_reset(clean_auth, monkeypatch):
    from zservice.domains.tradingview.routes import router

    monkeypatch.setattr(mode.settings_repo, "settings_set", lambda *a: None)
    monkeypatch.setattr(mode.settings_repo, "settings_get", lambda *a: "3")
    app = FastAPI()
    app.include_router(router)
    c = TestClient(app)
    assert c.get("/api/settings/tv_token").json() == {"status": "none"}
    assert c.post("/api/settings/tv_token", json={"token": " "}).status_code == 400
    assert (
        c.post("/api/settings/tv_token", json={"token": _jwt(time.time() - 5)}).status_code == 400
    )
    ok = c.post("/api/settings/tv_token", json={"token": _jwt(time.time() + 3600)}).json()
    assert ok["status"] == "active" and 55 < ok["expires_in_minutes"] <= 60
    assert c.post("/api/settings/tv_mode", json={"mode": 9}).status_code == 400
    assert c.post("/api/settings/tv_mode", json={"mode": 3}).json() == {"mode": 3}
    assert clean_auth.token is None  # changing the mode forgets the token


def test_throttle_spaces_requests(env):
    env(TV_MIN_REQUEST_INTERVAL="0.05", TV_COOLDOWN_SECONDS="120")
    t = throttle.Throttle()
    start = time.monotonic()
    for _ in range(3):
        t.wait_turn()
    assert time.monotonic() - start >= 0.09
    t.trip_cooldown("X")
    assert t.cooldown_left() > 120 - 1
