"""Security pass 25 Oct: registration gate, login hardening, server-side revocation,
password change, bounded rate-limit tables."""

import hashlib
import hmac
import json
import os
import time

import pytest
from fastapi.testclient import TestClient

from zservice.db.repos import settings as settings_repo
from zservice.db.repos import users as users_repo
from zservice.security import revocation, sessions, tokens
from zservice.security import tokens as session_auth
from zservice.security.rate_limit import SlidingWindow

STRONG = "correct horse battery"


class FakeUsers:
    """The single user + the settings collection, in memory."""

    def __init__(self, password: str = STRONG, rounds_hash: str | None = None):
        self.user = {
            "username": "me",
            "password_hash": rounds_hash or session_auth.hash_password(password),
        }
        self.settings: dict = {}
        self.updates: list = []

    def user_get(self, username):
        return dict(self.user) if self.user and username == self.user["username"] else None

    def user_exists(self):
        return self.user is not None

    def user_set_password(self, username, password_hash, updated_at):
        self.user["password_hash"] = password_hash
        self.updates.append(username)
        return True

    def settings_get(self, key):
        return self.settings.get(key)

    def settings_set(self, key, value):
        self.settings[key] = value

    def settings_get_many(self, keys):
        return {k: self.settings[k] for k in keys if k in self.settings}


@pytest.fixture
def world(monkeypatch):
    import main

    from zservice.domains.auth import routes as auth_routes

    fake = FakeUsers()
    for repo, names in (
        (users_repo, ("user_get", "user_exists", "user_set_password")),
        (settings_repo, ("settings_get", "settings_set", "settings_get_many")),
    ):
        for name in names:
            monkeypatch.setattr(repo, name, getattr(fake, name))
    monkeypatch.setattr(auth_routes, "_ATTEMPTS", SlidingWindow(50, 60))
    monkeypatch.setattr(auth_routes, "_IP_ATTEMPTS", SlidingWindow(50, 60))
    revocation._invalidate()
    yield TestClient(main.app, raise_server_exceptions=False), fake, auth_routes
    revocation._invalidate()


def _bearer(token):
    return {"Authorization": f"Bearer {token}"}


def _login(client, password=STRONG):
    return client.post("/api/auth/login", json={"username": "me", "password": password})


def test_registration_is_closed_unless_enabled(world, monkeypatch, env):
    client, fake, _ = world
    fake.user = None
    body = {"username": "new", "password": "a long enough passphrase"}
    env(ZS_ALLOW_REGISTER=None)
    assert client.get("/api/auth/status").json() == {
        "registered": False,
        "registration_open": False,
    }
    r = client.post("/api/auth/register", json=body)
    assert r.status_code == 403 and r.json()["code"] == "auth.registration_closed"
    env(ZS_ALLOW_REGISTER="1")
    assert client.get("/api/auth/status").json()["registration_open"] is True
    short = client.post("/api/auth/register", json={"username": "new", "password": "short"})
    assert short.status_code == 400 and short.json()["params"] == {"min": 12}


def test_status_hides_database_errors(world, monkeypatch):
    client, _, _ = world

    def boom():
        raise RuntimeError("cluster0-shard-00-01.secret.mongodb.net:27017: timed out")

    monkeypatch.setattr(users_repo, "user_exists", boom)
    r = client.get("/api/auth/status")
    assert r.status_code == 500 and "mongodb.net" not in r.text


def test_unknown_user_costs_a_password_check(world, monkeypatch):
    client, _, _ = world
    burned = []
    monkeypatch.setattr(tokens, "burn_password_check", lambda pw: burned.append(pw))
    r = client.post("/api/auth/login", json={"username": "ghost", "password": "x"})
    assert r.status_code == 401 and burned == ["x"]


def test_old_hash_is_upgraded_on_login(world):
    client, fake, _ = world
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", STRONG.encode(), salt, 120_000)
    b64 = session_auth._b64e
    fake.user["password_hash"] = f"pbkdf2$120000${b64(salt)}${b64(dk)}"  # the old setting
    assert tokens.needs_rehash(fake.user["password_hash"])
    assert _login(client).status_code == 200 and fake.updates == ["me"]
    assert not tokens.needs_rehash(fake.user["password_hash"])
    assert _login(client).status_code == 200 and fake.updates == ["me"]  # upgraded once


def test_per_ip_limit_stops_username_rotation(world, monkeypatch):
    client, _, auth_routes = world
    monkeypatch.setattr(auth_routes, "_IP_ATTEMPTS", SlidingWindow(3, 60))
    codes = [
        client.post("/api/auth/login", json={"username": f"u{i}", "password": "x"}).status_code
        for i in range(4)
    ]
    assert codes == [401, 401, 401, 429]


def test_bearer_logout_revokes_only_that_token(world):
    client, fake, _ = world
    first, second = _login(client).json()["token"], _login(client).json()["token"]
    assert client.get("/api/version", headers=_bearer(first)).status_code == 200
    r = client.post("/api/auth/logout", headers=_bearer(first))
    assert r.json()["revoked"] is True and len(fake.settings[revocation.JTI_KEY]) == 1
    assert client.get("/api/version", headers=_bearer(first)).status_code == 401
    assert client.get("/api/version", headers=_bearer(second)).status_code == 200


def test_logout_without_proof_only_clears_cookies(world):
    client, fake, _ = world
    token = _login(client).json()["token"]
    cookie = {"Cookie": f"{sessions.SESSION_COOKIE}={token}"}
    r = client.post("/api/auth/logout", headers=cookie)  # no CSRF header: could be forged
    assert r.status_code == 200 and r.json()["revoked"] is False
    assert revocation.JTI_KEY not in fake.settings
    proven = {**cookie, "X-ZS-CSRF": sessions.csrf_token_for(token), "Host": "testserver"}
    assert client.post("/api/auth/logout", headers=proven).json()["revoked"] is True


def test_token_without_jti_is_ended_by_a_cutoff(world):
    client, fake, _ = world
    now = int(time.time())
    legacy = _token_without_jti(iat=now - 5)
    assert client.get("/api/version", headers=_bearer(legacy)).status_code == 200
    client.post("/api/auth/logout", headers=_bearer(legacy))
    assert fake.settings[revocation.BEFORE_KEY] >= now
    assert client.get("/api/version", headers=_bearer(legacy)).status_code == 401


def test_password_change_ends_older_sessions(world):
    client, fake, _ = world
    old = _login(client).json()["token"]
    other = _token_without_jti(iat=int(time.time()) - 60)  # e.g. a stolen older token
    body = {"current_password": STRONG, "new_password": "an even longer passphrase"}
    wrong = client.post("/api/auth/password", json={**body, "current_password": "nope"},
                        headers=_bearer(old))  # fmt: skip
    assert wrong.status_code == 403 and wrong.json()["code"] == "auth.wrong_current_password"
    r = client.post("/api/auth/password", json=body, headers=_bearer(old))
    assert r.status_code == 200 and r.json()["token"]
    assert client.get("/api/version", headers=_bearer(other)).status_code == 401
    assert client.get("/api/version", headers=_bearer(r.json()["token"])).status_code == 200
    assert session_auth.verify_password("an even longer passphrase", fake.user["password_hash"])
    same = {"current_password": body["new_password"], "new_password": body["new_password"]}
    again = client.post("/api/auth/password", json=same, headers=_bearer(r.json()["token"]))
    assert again.json()["code"] == "auth.password_unchanged"


def test_password_change_needs_a_session(world):
    client, _, _ = world
    body = {"current_password": STRONG, "new_password": "an even longer passphrase"}
    assert client.post("/api/auth/password", json=body).status_code == 401


def test_oversized_credentials_are_rejected(world):
    client, _, _ = world
    r = client.post("/api/auth/login", json={"username": "me", "password": "x" * 2000})
    assert r.status_code == 422


def test_rate_limit_table_stays_bounded():
    window = SlidingWindow(5, 60, max_keys=100)
    for i in range(1000):
        window.hit(f"k{i}", now=0.0)
    assert len(window) == 100
    window.hit("fresh", now=120.0)  # every older key is idle past the window
    assert len(window) == 1


def _token_without_jti(iat: int) -> str:
    """A token as minted before tokens carried a jti."""
    header = session_auth._b64e(b'{"alg":"HS256","typ":"JWT"}')
    body = json.dumps({"sub": "me", "iat": iat, "exp": iat + 3600}, separators=(",", ":"))
    payload = session_auth._b64e(body.encode())
    sig = hmac.new(session_auth._secret(), f"{header}.{payload}".encode(), hashlib.sha256)
    return f"{header}.{payload}.{session_auth._b64e(sig.digest())}"
