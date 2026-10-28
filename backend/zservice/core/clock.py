"""Display clock: the configured display timezone used for stored timestamps, the web display and
Telegram messages, so all of them show the same wall-clock time.

Stored as a fixed UTC offset in minutes plus a human label (no tzdata dependency). Lives
in core because every domain stamps rows with it; the settings domain exposes the routes.
"""

from datetime import datetime, timedelta, timezone

from zservice.db.repos import settings as settings_repo

DEFAULT_TZ_OFFSET_MIN = 420  # UTC+7 (Asia/Bangkok)
DEFAULT_TZ_LABEL = "Asia/Bangkok (UTC+7)"


def get_tz_setting() -> dict:
    vals = settings_repo.settings_get_many(["tz_offset_minutes", "tz_label"])
    try:
        offset = int(vals.get("tz_offset_minutes", DEFAULT_TZ_OFFSET_MIN))
    except (TypeError, ValueError):
        offset = DEFAULT_TZ_OFFSET_MIN
    label = vals.get("tz_label") or DEFAULT_TZ_LABEL
    return {"offset_minutes": offset, "label": label}


def set_tz_setting(offset_minutes: int, label: str) -> None:
    settings_repo.settings_set("tz_offset_minutes", str(offset_minutes))
    settings_repo.settings_set("tz_label", label)


def current_tz() -> timezone:
    return timezone(timedelta(minutes=get_tz_setting()["offset_minutes"]))


def current_tz_label() -> str:
    return get_tz_setting()["label"]


def now_iso() -> str:
    """Now in the display timezone, ISO 8601 with offset — the stamp stored on rows."""
    return datetime.now(current_tz()).isoformat()


def tz_suffix() -> str:
    """Human tz tag for folder names, e.g. 'UTC+7' or 'UTC-5:30'."""
    mins = get_tz_setting()["offset_minutes"]
    sign = "+" if mins >= 0 else "-"
    h, m = divmod(abs(mins), 60)
    return f"UTC{sign}{h}" + (f":{m:02d}" if m else "")


def fmt_wall(dt: datetime) -> str:
    """Wall-clock stamp used in job summaries: 'YYYY-MM-DD HH:MM:SS' (no offset)."""
    return dt.strftime("%Y-%m-%d %H:%M:%S")
