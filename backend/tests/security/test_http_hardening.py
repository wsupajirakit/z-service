"""B5 CORS from env, B6 /docs behind a session, B8 security headers, B13 lifespan order."""

import pytest
from fastapi.testclient import TestClient

from zservice.security import tokens as session_auth


@pytest.fixture(scope="module")
def client():
    import main

    return TestClient(main.app, raise_server_exceptions=False)


def _session():
    return {"Authorization": f"Bearer {session_auth.create_token('t')}"}


def test_security_headers_on_api_and_on_401(client):
    for r in (client.get("/api/healthz"), client.get("/api/version")):
        assert r.headers["x-content-type-options"] == "nosniff"
        assert r.headers["x-frame-options"] == "DENY"
        assert r.headers["referrer-policy"] == "no-referrer"
        assert "max-age=" in r.headers["strict-transport-security"]
        assert r.headers["cache-control"] == "no-store"


def test_csp_full_for_new_ui_scripts_enforced_for_legacy(monkeypatch, env):
    from pathlib import Path

    from zservice.security import headers

    app_headers = headers.headers_for("/app/watchlist/")
    assert "frame-ancestors 'none'" in app_headers["Content-Security-Policy"]
    # The real legacy login page: its one inline <script> is allowed by hash, nothing else.
    public = Path(__file__).resolve().parents[3] / "dash" / "public"
    env(FRONTEND_DIR=str(public))
    headers.legacy_csp.cache_clear()
    try:
        legacy = headers.headers_for("/login")
        expected = headers.inline_script_hashes((public / "login.html").read_text())
        assert len(expected) == 1
        policy = legacy["Content-Security-Policy"]
        assert policy.startswith(f"script-src 'self' {expected[0]};")
        assert "object-src 'none'" in policy and "frame-ancestors 'none'" in policy
        assert "style-src 'self'" in legacy["Content-Security-Policy-Report-Only"]
    finally:
        headers.legacy_csp.cache_clear()


def test_inline_script_hash_matches_the_browser_rule():
    from zservice.security.headers import inline_script_hashes

    # CSP hashes the element's text exactly; CRLF is normalized to LF by the HTML parser.
    # base64(sha256(b"alert(1)")), computed independently with hashlib
    assert inline_script_hashes("<script>alert(1)</script>") == [
        "'sha256-bhHHL3z2vDgxUt0W3dWQOrprscmda2Y5pLsLg4GF+pI='"
    ]
    assert inline_script_hashes("<script>a\r\nb</script>") == inline_script_hashes(
        "<script>a\nb</script>"
    )
    assert inline_script_hashes('<script src="/x.js"></script>') == []


def test_docs_need_a_session(client):
    assert client.get("/docs", follow_redirects=False).status_code == 302  # to /login
    assert client.get("/openapi.json", follow_redirects=False).status_code == 302
    assert client.get("/openapi.json", headers=_session()).status_code == 200


def test_no_cors_by_default_and_wildcard_refused(client, monkeypatch, env):
    r = client.options(
        "/api/version",
        headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "GET"},
    )
    assert "access-control-allow-origin" not in r.headers
    from zservice.security import cors

    env(ZS_CORS_ORIGINS="*")
    with pytest.raises(ValueError):
        cors.allowed_origins()
    env(ZS_CORS_ORIGINS="http://localhost:5173/, http://localhost:6600")
    assert cors.allowed_origins() == ["http://localhost:5173", "http://localhost:6600"]


def test_lifespan_checks_secret_before_autostart(monkeypatch):
    import main

    from zservice.domains.jobs import autostart

    order = []
    monkeypatch.setattr(session_auth, "assert_configured", lambda: order.append("secret"))
    monkeypatch.setattr(autostart, "start_if_enabled", lambda: order.append("autostart"))
    with TestClient(main.app):
        pass
    assert order == ["secret", "autostart"]


def test_each_ui_signs_in_on_its_own_page(client):
    from zservice.web.paths import APP_BASE, APP_LOGIN

    app_page = client.get(f"{APP_BASE}settings/", follow_redirects=False)
    assert app_page.status_code == 302 and app_page.headers["location"] == APP_LOGIN
    legacy = client.get("/", follow_redirects=False)
    assert legacy.status_code == 302 and legacy.headers["location"] == "/login"
    # The new sign-in page and its bundle are public; nothing else under the base is.
    from zservice.security.middleware import is_public

    assert is_public(APP_LOGIN) and is_public(f"{APP_BASE}assets/index-abc.js")
    # The legacy sign-in page loads these before any session exists.
    assert is_public("/theme-init.js") and is_public("/favicon.svg") and is_public("/login.html")
    assert not is_public(f"{APP_BASE}settings/") and not is_public(f"{APP_BASE}login/x")
