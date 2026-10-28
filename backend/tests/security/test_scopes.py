"""Every call the home machine's scripts make today must be allowed by the scopes the
home key gets; everything else must be denied (default deny)."""

import pytest

from zservice.security.machine import scope_allows

HOME = frozenset({"read", "jobs", "gold:jobs", "watchlist:write"})

# (method, path) taken from load_all.sh, fetch_csv.sh, fill_short_hist.py,
# fetch_new_symbols.py, start_auto_all.py, add_symbols_*.py, fix_tickers_1019.py,
# wait_zsvc_1d1w.py and the gold export docs.
SCRIPT_CALLS = [
    ("GET", "/api/export_zip"),
    ("GET", "/api/automate/status"),
    ("GET", "/api/history"),
    ("GET", "/api/history/123"),
    ("GET", "/api/watchlist"),
    ("GET", "/api/symbols"),
    ("GET", "/api/gold/export"),
    ("GET", "/api/version"),
    ("GET", "/api/export/check"),
    ("GET", "/api/inbound-events"),
    ("GET", "/api/stock_radar/history"),
    ("POST", "/api/automate"),
    ("POST", "/api/auto/stop"),
    ("POST", "/api/auto/start"),
    ("POST", "/api/auto/start_all"),
    ("POST", "/api/stock_radar/scan"),
    ("POST", "/api/watchlist"),
    ("PUT", "/api/watchlist/TREND-1019"),
    ("DELETE", "/api/watchlist/TREND-1019/ROLL"),
]

DENIED_FOR_HOME = [
    ("GET", "/api/drive/files"),
    ("GET", "/api/admin/key_audit"),
    ("POST", "/api/settings/tv_token"),
    ("POST", "/api/settings/timezone"),
    ("DELETE", "/api/history"),
    ("POST", "/api/history/cleanup"),
    ("DELETE", "/api/radar_round/202610231753_0c27a843"),
    ("POST", "/api/portfolio"),
    ("POST", "/api/earning_scan/scan"),
    ("PATCH", "/api/watchlist/X"),
    ("GET", "/docs"),
]


@pytest.mark.parametrize("method,path", SCRIPT_CALLS)
def test_home_key_allows_every_script_call(method, path):
    assert scope_allows(HOME, method, path)


@pytest.mark.parametrize("method,path", DENIED_FOR_HOME)
def test_home_key_denies_everything_else(method, path):
    assert not scope_allows(HOME, method, path)


def test_read_scope_cannot_write():
    assert not scope_allows(frozenset({"read"}), "POST", "/api/watchlist")
    assert not scope_allows(frozenset({"read"}), "POST", "/api/automate")


def test_admin_scope_allows_anything():
    assert scope_allows(frozenset({"admin"}), "DELETE", "/api/history")
