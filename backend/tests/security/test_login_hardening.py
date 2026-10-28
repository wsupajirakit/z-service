"""Sign-in hardening: wrong keys are throttled per client (a valid key never is), tokens
must carry exactly our header and sane claims, public paths cannot be reached through dot
segments, OPTIONS only skips the gate for a real preflight with CORS on, inbound HMAC keys
have a minimum length, and the TradingView account is masked in logs."""

import base64
import hashlib
import hmac
import json
import time

import pytest
from pydantic import ValidationError

from zservice.domains.inbound_events.config import MIN_SECRET_BYTES, Sender
from zservice.domains.inbound_events.verify import _hmac_ok
from zservice.integrations.tradingview.client import _masked
from zservice.security import tokens
from zservice.security.machine.auth import WRONG_KEY_LIMIT
from zservice.security.middleware import is_public

LEGACY = "legacy-secret-value"


@pytest.fixture
def client():
    import main
    from fastapi.testclient import TestClient

    from zservice.core import config
    from zservice.security import machine
    from zservice.security.machine import registry

    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("PULL_KEY", LEGACY)
        config.reset()
        registry.use(machine.from_env())  # a fresh guess counter for this test
        yield TestClient(main.app, raise_server_exceptions=False)
    config.reset()
    registry.use(machine.from_env())


def test_wrong_keys_are_throttled_but_the_right_key_never_is(client):
    for _ in range(WRONG_KEY_LIMIT):
        assert client.get("/api/version", headers={"X-Pull-Key": "guess"}).status_code == 401
    blocked = client.get("/api/version", params={"pull_key": "guess"})
    assert blocked.status_code == 429 and int(blocked.headers["Retry-After"]) >= 1
    assert (
        client.get(
            "/api/version", headers={"Authorization": "Bearer zsk_nope_" + "x" * 40}
        ).status_code
        == 429
    )
    # The real key, from the same client, still works (header and query).
    assert client.get("/api/version", headers={"X-Pull-Key": LEGACY}).status_code == 200
    assert client.get("/api/version", params={"pull_key": LEGACY}).status_code == 200


def test_requests_without_a_key_are_not_counted(client):
    for _ in range(WRONG_KEY_LIMIT + 5):
        assert client.get("/api/version").status_code == 401


def _signed(header: dict, payload: dict) -> str:
    def b64(obj: dict) -> str:
        return base64.urlsafe_b64encode(json.dumps(obj).encode()).rstrip(b"=").decode()

    head, body = b64(header), b64(payload)
    sig = hmac.new(tokens._secret(), f"{head}.{body}".encode(), hashlib.sha256).digest()
    return f"{head}.{body}.{base64.urlsafe_b64encode(sig).rstrip(b'=').decode()}"


@pytest.mark.parametrize(
    "header,payload",
    [
        ({"alg": "none", "typ": "JWT"}, {}),
        ({"alg": "HS512", "typ": "JWT"}, {}),
        ({"alg": "HS256"}, {}),
        ({"alg": "HS256", "typ": "JWT"}, {"sub": ""}),
        ({"alg": "HS256", "typ": "JWT"}, {"sub": 5}),
        ({"alg": "HS256", "typ": "JWT"}, {"iat": "now"}),
        ({"alg": "HS256", "typ": "JWT"}, {"iat": int(time.time()) + 3600}),
        ({"alg": "HS256", "typ": "JWT"}, {"nbf": int(time.time()) + 3600}),
        ({"alg": "HS256", "typ": "JWT"}, {"exp": int(time.time()) + 10 * tokens.TOKEN_TTL_SECONDS}),
        ({"alg": "HS256", "typ": "JWT"}, {"exp": int(time.time()) - 1}),
    ],
)
def test_tokens_need_our_header_and_sane_claims(env, header, payload):
    env(AUTH_SECRET="s" * 40)
    now = int(time.time())
    claims = {"sub": "me", "iat": now, "exp": now + 60, **payload}
    assert tokens.decode_token(_signed(header, claims)) is None


def test_a_token_we_issue_still_decodes(env):
    env(AUTH_SECRET="s" * 40)
    assert tokens.decode_token(tokens.create_token("me"))["sub"] == "me"


@pytest.mark.parametrize(
    "path", ["/assets/../index.html", "/assets/./x.js", "//assets/x.js", "/static/../api/version"]
)
def test_dot_segments_are_never_public(path):
    assert not is_public(path)


def test_ordinary_public_paths_still_are():
    assert is_public("/assets/index-abc.js") and is_public("/login") and is_public("/api/healthz")


def test_options_is_gated_when_cors_is_off(client):
    assert (
        client.options("/api/version", headers={"Access-Control-Request-Method": "GET"}).status_code
        == 401
    )


def test_short_inbound_secrets_are_refused():
    short = "whsec_" + base64.b64encode(b"k" * (MIN_SECRET_BYTES - 1)).decode()
    with pytest.raises(ValidationError):
        Sender(name="engine", secret=short)
    assert not _hmac_ok(short, b"body", "sig")
    ok = "whsec_" + base64.b64encode(b"k" * MIN_SECRET_BYTES).decode()
    assert Sender(name="engine", secret=ok).secret is not None


def test_the_tradingview_account_is_masked():
    assert _masked("someone@example.com") == "s***@e***"
    assert "someone" not in _masked("someone@example.com")
    assert _masked("plainuser") == "p***"
