"""The real middleware in main.py, end to end through FastAPI's TestClient (offline)."""

import json

import pytest

SECRET = "t" * 43
KEY = f"zsk_home_{SECRET}"
READ_KEY = f"zsk_reader_{SECRET}"
LEGACY = "legacy-secret-value"


@pytest.fixture(scope="module")
def client():
    from zservice.security.machine import hash_secret

    entries = [
        {
            "id": "home",
            "scopes": ["read", "jobs", "watchlist:write"],
            "sha256": hash_secret(SECRET),
            "expires": "2099-01-01",
        },
        {
            "id": "reader",
            "scopes": ["read"],
            "sha256": hash_secret(SECRET),
            "expires": "2099-01-01",
        },
    ]
    import main
    from fastapi.testclient import TestClient

    from zservice.core import config
    from zservice.security import machine
    from zservice.security.machine import registry

    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("ZS_API_KEYS", json.dumps(entries))
        mp.setenv("PULL_KEY", LEGACY)
        config.reset()
        registry.use(machine.from_env())  # rebuild with the env above
    yield TestClient(main.app, raise_server_exceptions=False)
    config.reset()
    registry.use(machine.from_env())  # back to the plain test environment


def test_no_credential_is_401(client):
    assert client.get("/api/version").status_code == 401


def test_scoped_key_reads(client):
    r = client.get("/api/version", headers={"Authorization": f"Bearer {KEY}"})
    assert r.status_code == 200


def test_read_key_cannot_write(client):
    r = client.post("/api/auto/stop", headers={"Authorization": f"Bearer {READ_KEY}"})
    assert r.status_code == 403


def test_key_cannot_reach_admin_audit(client):
    r = client.get("/api/admin/key_audit", headers={"Authorization": f"Bearer {KEY}"})
    assert r.status_code == 403


def test_bad_key_is_401_not_a_session_fallthrough(client):
    r = client.get("/api/version", headers={"Authorization": f"Bearer zsk_home_{'x' * 43}"})
    assert r.status_code == 401 and r.json()["detail"] == "invalid key"


def test_legacy_pull_key_still_works_header_and_query(client):
    assert client.get("/api/version", headers={"X-Pull-Key": LEGACY}).status_code == 200
    assert client.get(f"/api/version?pull_key={LEGACY}").status_code == 200


def test_browser_session_sees_audit_with_deprecated_caller(client):
    from zservice.security import tokens as session_auth

    token = session_auth.create_token("tester")
    r = client.get("/api/admin/key_audit", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    body = r.json()
    assert body["legacy_pull_key_enabled"] is True
    assert any(c["principal"] == "legacy-pull-key" for c in body["summary"]["callers"])
    assert SECRET not in r.text and LEGACY not in r.text


def test_healthz_is_public_and_carries_no_data(client):
    r = client.get("/api/healthz")
    assert r.status_code == 200 and r.json() == {"status": "ok"}
