"""Settings read/write helpers (moved unchanged from main.py; main re-exports them).

The display timezone itself lives in zservice/core/clock.py (every domain stamps rows with
it); this module re-exports it so the settings routes have one place to call.
"""

from zservice.core.clock import (
    DEFAULT_TZ_LABEL,
    DEFAULT_TZ_OFFSET_MIN,
    current_tz,
    current_tz_label,
    get_tz_setting,
    set_tz_setting,
)
from zservice.db.repos import settings as settings_repo
from zservice.integrations.tradingview.mode import get_tv_mode_setting, set_tv_mode_setting

__all__ = [
    "DEFAULT_TZ_LABEL",
    "DEFAULT_TZ_OFFSET_MIN",
    "current_tz",
    "current_tz_label",
    "get_tv_mode_setting",
    "get_tz_setting",
    "set_tv_mode_setting",
    "set_tz_setting",
]

TZ_OFFSET_RANGE_MIN = (-720, 840)  # UTC-12 .. UTC+14
TZ_LABEL_MAX_LEN = 60

DEFAULT_AUTO_SKIP_MINUTES = 15
AUTO_SKIP_RANGE = (1, 100)

# Where finished jobs send their results, per category (stock/gold) x channel
# (drive/telegram), toggled independently. Server-side auto jobs read the same setting.
# Default: all on.
DEST_KEYS = ["dest_stock_drive", "dest_stock_telegram", "dest_gold_drive", "dest_gold_telegram"]


def _int_setting(key: str, default: int) -> int:
    try:
        val = settings_repo.settings_get(key)
        if val is not None:
            return int(val)
    except Exception:  # noqa: S110 — a broken or missing DB value falls back to the default
        pass
    return default


def get_auto_skip_minutes_setting() -> int:
    return _int_setting("auto_skip_minutes", DEFAULT_AUTO_SKIP_MINUTES)


def set_auto_skip_minutes_setting(minutes: int) -> None:
    settings_repo.settings_set("auto_skip_minutes", str(minutes))


def get_dest_setting() -> dict:
    vals = settings_repo.settings_get_many(DEST_KEYS)
    return {k: (vals.get(k, "1") != "0") for k in DEST_KEYS}  # unset means on


def set_dest_setting(values: dict) -> None:
    for k in DEST_KEYS:
        if k in values:
            settings_repo.settings_set(k, "1" if values[k] else "0")
