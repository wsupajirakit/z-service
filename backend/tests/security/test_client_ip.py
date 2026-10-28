"""Login rate limit keys on an address the client cannot choose (X-Forwarded-For)."""

from types import SimpleNamespace

from starlette.datastructures import Headers

from zservice.core import config as zs_config
from zservice.security.client_ip import client_ip


def _trust(monkeypatch, value):
    if value is None:
        monkeypatch.delenv("FORWARDED_ALLOW_IPS", raising=False)
    else:
        monkeypatch.setenv("FORWARDED_ALLOW_IPS", value)
    zs_config.reset()


def _req(peer, xff=()):
    raw = [(b"x-forwarded-for", v.encode()) for v in xff]
    return SimpleNamespace(client=SimpleNamespace(host=peer), headers=Headers(raw=raw))


def test_wildcard_trust_uses_the_hop_the_proxy_added(monkeypatch):
    _trust(monkeypatch, "*")
    # uvicorn would report the spoofed leftmost entry as the peer
    assert client_ip(_req("6.6.6.6", ["6.6.6.6, 203.0.113.9"])) == "203.0.113.9"
    assert client_ip(_req("1.1.1.1", ["1.1.1.1", "203.0.113.9:5555"])) == "203.0.113.9"
    assert client_ip(_req("::1", ["[2001:db8::1]:443"])) == "2001:db8::1"
    assert client_ip(_req("10.0.0.2")) == "10.0.0.2"


def test_explicit_proxy_list_keeps_uvicorn_choice(monkeypatch):
    _trust(monkeypatch, "10.0.0.0/8")
    assert client_ip(_req("203.0.113.9", ["6.6.6.6, 203.0.113.9"])) == "203.0.113.9"
    _trust(monkeypatch, None)
    assert client_ip(_req("203.0.113.9", ["6.6.6.6"])) == "203.0.113.9"


def test_rotating_spoofed_xff_hits_the_login_limit(monkeypatch):
    import main
    from fastapi.testclient import TestClient

    from zservice.db.repos import users as users_repo
    from zservice.domains.auth import routes as auth_routes
    from zservice.security.rate_limit import SlidingWindow

    _trust(monkeypatch, "*")
    monkeypatch.setattr(users_repo, "user_get", lambda _u: None)
    monkeypatch.setattr(auth_routes, "_IP_ATTEMPTS", SlidingWindow(3, 60))
    monkeypatch.setattr(auth_routes, "_ATTEMPTS", SlidingWindow(50, 60))
    client = TestClient(main.app, raise_server_exceptions=False)
    codes = [
        client.post(
            "/api/auth/login",
            json={"username": f"u{i}", "password": "x"},
            headers={"X-Forwarded-For": f"198.51.100.{i}, 203.0.113.9"},
        ).status_code
        for i in range(5)
    ]
    assert codes == [401, 401, 401, 429, 429]
