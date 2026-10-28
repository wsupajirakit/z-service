"""B4 HttpOnly session cookie + signed double-submit CSRF, B9 login rate limit."""

import pytest
from fastapi.testclient import TestClient

from zservice.security import sessions
from zservice.security import tokens as session_auth


@pytest.fixture
def client(monkeypatch):
    import main

    from zservice.db.repos import users as users_repo
    from zservice.domains.auth import routes as auth_routes

    hashed = session_auth.hash_password("pw123456")
    monkeypatch.setattr(
        users_repo,
        "user_get",
        lambda u: {"username": u, "password_hash": hashed} if u == "me" else None,
    )
    monkeypatch.setattr(auth_routes, "_ATTEMPTS", auth_routes.SlidingWindow(3, 60))
    return TestClient(main.app, raise_server_exceptions=False)


def _cookie_headers(token, csrf=None, **extra):
    headers = {"Cookie": f"{sessions.SESSION_COOKIE}={token}", "Host": "testserver", **extra}
    if csrf:
        headers["X-ZS-CSRF"] = csrf
    return headers


def test_login_sets_hardened_cookies_and_keeps_the_json_token(client):
    r = client.post("/api/auth/login", json={"username": "me", "password": "pw123456"})
    assert r.status_code == 200 and r.json()["token"]
    cookies = r.headers.get_list("set-cookie")
    session = next(c for c in cookies if c.startswith(sessions.SESSION_COOKIE))
    csrf = next(c for c in cookies if c.startswith(sessions.CSRF_COOKIE))
    for flag in ("HttpOnly", "Secure", "SameSite=strict", "Path=/"):
        assert flag.lower() in session.lower()
    assert "httponly" not in csrf.lower() and "secure" in csrf.lower()


def test_cookie_session_reads_without_csrf(client):
    token = session_auth.create_token("me")
    assert client.get("/api/version", headers=_cookie_headers(token)).status_code == 200


def test_cookie_session_writes_need_matching_csrf(client):
    token = session_auth.create_token("me")
    url = "/api/auto/stop"
    assert client.post(url, headers=_cookie_headers(token)).status_code == 403
    assert client.post(url, headers=_cookie_headers(token, "wrong")).status_code == 403
    good = sessions.csrf_token_for(token)
    assert client.post(url, headers=_cookie_headers(token, good)).status_code == 200
    blocked = _cookie_headers(token, good, **{"Sec-Fetch-Site": "cross-site"})
    assert client.post(url, headers=blocked).status_code == 403
    foreign = _cookie_headers(token, good, Origin="https://evil.example")
    assert client.post(url, headers=foreign).status_code == 403


def test_bearer_writes_and_legacy_cookie_reads_only(client):
    token = session_auth.create_token("me")
    bearer = {"Authorization": f"Bearer {token}"}
    assert client.post("/api/auto/stop", headers=bearer).status_code == 200
    # The JS-set z_token cookie is SameSite=Lax: a sibling subdomain could ride it, and the
    # legacy dashboard sends a Bearer header on every API call, so it only authorizes reads.
    legacy = {"Cookie": f"z_token={token}"}
    assert client.get("/api/version", headers=legacy).status_code == 200
    r = client.post("/api/auto/stop", headers=legacy)
    assert r.status_code == 403 and "Authorization header" in r.json()["detail"]
    assert client.post("/api/auto/stop", headers={**legacy, **bearer}).status_code == 200


def test_logout_clears_cookies(client):
    r = client.post("/api/auth/logout")
    assert r.status_code == 200
    assert all("max-age=0" in c.lower() for c in r.headers.get_list("set-cookie"))


def test_login_is_rate_limited(client):
    body = {"username": "me", "password": "wrong"}
    codes = [client.post("/api/auth/login", json=body).status_code for _ in range(4)]
    assert codes == [401, 401, 401, 429]
    r = client.post("/api/auth/login", json=body)
    assert r.status_code == 429 and int(r.headers["retry-after"]) >= 1
