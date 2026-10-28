import json
from datetime import date

from zservice.security.machine import MachineAuth, hash_secret, load_keys
from zservice.security.machine.audit import Audit
from zservice.security.rate_limit import SlidingWindow

SECRET = "s" * 43
KEY = f"zsk_home_{SECRET}"
LEGACY = "legacy-secret-value"


def _auth(limit=100, legacy=LEGACY, expires="2027-01-01", scopes=("read", "jobs")):
    keys = load_keys(
        json.dumps(
            [
                {
                    "id": "home",
                    "scopes": list(scopes),
                    "sha256": hash_secret(SECRET),
                    "expires": expires,
                }
            ]
        )
    )
    return MachineAuth(keys, legacy, SlidingWindow(limit, 60), Audit(50))


def _bearer(token):
    return {"authorization": f"Bearer {token}"}


def test_no_credential_falls_through():
    assert _auth().authorize("GET", "/api/history", {}, {}) is None


def test_valid_key_within_scope():
    d = _auth().authorize("POST", "/api/automate", _bearer(KEY), {})
    assert d.allowed and d.principal == "home" and not d.deprecated


def test_wrong_secret_and_unknown_id_are_401():
    auth = _auth()
    assert auth.authorize("GET", "/api/history", _bearer(f"zsk_home_{'x' * 43}"), {}).status == 401
    assert auth.authorize("GET", "/api/history", _bearer(f"zsk_nobody_{SECRET}"), {}).status == 401
    assert auth.authorize("GET", "/api/history", _bearer("zsk_garbage"), {}).status == 401


def test_out_of_scope_is_403():
    d = _auth().authorize("POST", "/api/watchlist", _bearer(KEY), {})
    assert not d.allowed and d.status == 403


def test_expired_key_is_401():
    d = _auth(expires="2026-01-01").authorize(
        "GET", "/api/history", _bearer(KEY), {}, today=date(2026, 10, 24)
    )
    assert d.status == 401 and d.reason == "key expired"


def test_key_in_query_string_is_not_accepted():
    assert _auth(legacy="").authorize("GET", "/api/history", {}, {"api_key": KEY}) is None


def test_rate_limit_returns_429_with_retry_after():
    auth = _auth(limit=2)
    for _ in range(2):
        assert auth.authorize("GET", "/api/history", _bearer(KEY), {}).allowed
    d = auth.authorize("GET", "/api/history", _bearer(KEY), {})
    assert d.status == 429 and d.retry_after >= 1


def test_legacy_pull_key_reaches_only_what_the_scripts_use_and_is_flagged():
    auth = _auth()
    query = auth.authorize("GET", "/api/export_zip", {}, {"pull_key": LEGACY})
    assert query.allowed and query.deprecated and query.via == "query"
    # Every endpoint the home scripts call (stock-radar + z-service root scripts, 25 Oct).
    used = [
        ("GET", "/api/export"), ("GET", "/api/export_zip"), ("GET", "/api/export/check"),
        ("GET", "/api/automate/status"), ("GET", "/api/version"), ("GET", "/api/inbound-events"),
        ("GET", "/api/stock_radar/history"), ("POST", "/api/stock_radar/scan"),
        ("GET", "/api/symbols"), ("GET", "/api/history"), ("GET", "/api/history/42"),
        ("POST", "/api/auto/start"), ("POST", "/api/auto/start_all"), ("POST", "/api/auto/stop"),
        ("POST", "/api/automate"), ("POST", "/api/gold/automate"),
        ("POST", "/api/gold/automate/stop"), ("POST", "/api/watchlist"),
        ("PUT", "/api/watchlist/WL01"), ("DELETE", "/api/watchlist/WL01/AAA"),
    ]  # fmt: skip
    for method, path in used:
        assert auth.authorize(method, path, {"x-pull-key": LEGACY}, {}).allowed, path
        assert auth.authorize(method, path, {}, {"pull_key": LEGACY}).allowed, path
    for method, path in [("DELETE", "/api/history"), ("GET", "/api/admin/key_audit"),
                         ("POST", "/api/settings/tv_token"), ("POST", "/api/portfolio"),
                         ("GET", "/api/drive/files"), ("POST", "/api/auth/password")]:  # fmt: skip
        d = auth.authorize(method, path, {"x-pull-key": LEGACY}, {})
        assert not d.allowed and d.status == 403 and d.deprecated, path


def test_wrong_legacy_key_falls_through_and_disabled_legacy_is_ignored():
    assert _auth().authorize("GET", "/api/history", {"x-pull-key": "nope"}, {}) is None
    assert _auth(legacy="").authorize("GET", "/api/history", {"x-pull-key": LEGACY}, {}) is None


def test_audit_never_stores_the_key():
    auth = _auth()
    d = auth.authorize("GET", "/api/history", _bearer(KEY), {})
    auth.audit.record(d, "GET", "/api/history", "1.2.3.4", 200)
    assert SECRET not in json.dumps(auth.audit.recent())
    assert auth.audit.summary()["callers"][0]["principal"] == "home"
