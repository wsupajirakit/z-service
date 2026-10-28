"""Security pass 25 Oct: secrets on disk and in logs, Telegram escaping, Drive ids."""

import json
import logging
import os
import stat
from datetime import UTC, datetime, timedelta

import pytest

from zservice.core import logging as zs_logging
from zservice.core.errors import ApiError
from zservice.domains.jobs import summary
from zservice.integrations import drive
from zservice.integrations.tradingview import auth as tv_auth


def test_token_cache_is_owner_only_and_atomic(tmp_path, monkeypatch):
    path = tmp_path / ".tv_token_cache.json"
    path.write_text("{}")
    path.chmod(0o644)  # an old world-readable file is tightened on the next write
    monkeypatch.setattr(tv_auth, "TOKEN_CACHE_FILE", str(path))
    tv_auth.save_cached_login("tok", 4_102_444_800.0)
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert json.loads(path.read_text()) == {"token": "tok", "exp": 4_102_444_800.0}
    assert not (tmp_path / ".tv_token_cache.json.tmp").exists()


def test_access_log_masks_query_secrets():
    record = logging.LogRecord(
        "uvicorn.access", logging.INFO, "", 0, '%s - "%s %s HTTP/%s" %d',
        ("1.2.3.4:5", "GET", "/api/export?interval=1d&pull_key=s3cret&token=t0k", "1.1", 200),
        None,
    )  # fmt: skip
    zs_logging._RedactQuerySecrets().filter(record)
    line = record.getMessage()
    assert "s3cret" not in line and "t0k" not in line and "interval=1d" in line


def test_unwritable_log_dir_does_not_stop_the_boot(monkeypatch, tmp_path):
    locked = tmp_path / "ro"
    locked.mkdir()
    locked.chmod(0o500)
    try:
        monkeypatch.setattr(zs_logging, "AUTOMATE_LOG_FILE", str(locked / "automate.log"))
        if os.access(locked, os.W_OK):
            pytest.skip("running as a user that ignores directory permissions")
        assert zs_logging._file_handler() is None
    finally:
        locked.chmod(0o700)


def test_telegram_summary_escapes_settings_and_symbols(monkeypatch):
    monkeypatch.setattr(summary, "current_tz_label", lambda: "UTC<b>")
    start = datetime(2026, 10, 25, tzinfo=UTC)
    text = summary.summary_text("t", start, start + timedelta(seconds=5), ["1d"],
                                [("1d", False, 1, ["A&B", "<x>"])], 2, 80)  # fmt: skip
    assert "UTC&lt;b&gt;" in text and "A&amp;B, &lt;x&gt;" in text and "<x>" not in text


def test_drive_ids_are_checked_before_any_api_call(monkeypatch):
    monkeypatch.setattr(drive, "_drive_service", lambda: pytest.fail("no API call expected"))
    for bad in ("x' in parents or name contains 'a", "short", "a/b/c/d/e/f/g"):
        with pytest.raises(ApiError) as err:
            drive._assert_under_root(None, bad)
        assert err.value.code == "drive.bad_id"
