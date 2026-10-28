"""Timestamps of a round: the display clock, ET wall time with a real offset, hour gaps.

Timestamps are stored raw. Wall-clock ET values coming out of the screen get a real
America/New_York offset attached (`*_iso`) so the browser can render them in ET or GMT+7
exactly, including across DST — no offset is ever hard-coded.
"""

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from . import deps

ET = ZoneInfo("America/New_York")


UTC = UTC


def now_iso() -> str:
    """Now, in the app's configured display timezone (same clock the history
    rows and Telegram messages use), as an offset-aware ISO string."""
    try:
        return datetime.now(deps.app().current_tz()).isoformat()
    except Exception:
        return datetime.now().astimezone().isoformat()


def et_iso(wall) -> str | None:
    """'2026-08-12 08:23:00' (ET wall clock, no offset) -> the same instant with
    the true America/New_York offset for that date ('...-04:00' in EDT). The UI
    needs this to convert to GMT+7 without guessing whether DST was on."""
    if wall in (None, ""):
        return None
    try:
        dt = datetime.fromisoformat(str(wall).strip().replace("Z", "")[:19])
    except ValueError:
        return None
    return dt.replace(tzinfo=ET).isoformat()


def parse_ts(iso: str | None):
    """Parse a stored ISO timestamp (offset-aware or naive) -> datetime, or None."""
    if not iso:
        return None
    try:
        dt = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt


def ts_key(iso: str | None):
    """Sort key for stored timestamps. String order is NOT safe here: the app's
    display timezone is a user setting, so history rows written before and after
    a change carry different offsets and would sort by wall clock, not instant."""
    dt = parse_ts(iso)
    if dt is None:
        return datetime.max.replace(tzinfo=UTC)
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def hours_between(a: str | None, b: str | None) -> float | None:
    """Signed hours from a to b. Direction matters: data can legitimately be
    stamped AHEAD of the clock (when the CSV has no as-of header, the screen
    falls back to the end of the newest bar — a weekly bar ends up to 7 days
    out), and calling that "old data" would be flatly wrong."""
    da, db = parse_ts(a), parse_ts(b)
    if da is None or db is None:
        return None
    if (da.tzinfo is None) != (db.tzinfo is None):  # can't compare mixed kinds
        return None
    return (db - da).total_seconds() / 3600.0


def spread_hours(a: str | None, b: str | None) -> float | None:
    """How far apart two timestamps are, direction ignored."""
    h = hours_between(a, b)
    return None if h is None else abs(h)
