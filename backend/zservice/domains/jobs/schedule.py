"""TF-aware scheduling for the auto job (moved from main.py).

Every symbol is still fetched every round. What is skipped is re-fetching a TIMEFRAME whose
bar has not closed since the last pull: a 1d/1w bar changes once per session, not once per
15-minute round. Re-pulling all four every round burned ~73% of the round time AND rewrote
already-closed bars (the "1W moved mid-week" artifact the radar health check flagged).
Keys are persisted in Mongo so a restart does not trigger a needless full pull.
"""

import json
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from zservice.core.job_state import add_log
from zservice.db.repos import settings as settings_repo

from . import config as jobs_config

# Continuous auto sequence (mirrors the frontend AUTO_STEPS): (timeframe, extended_session)
AUTO_STEPS = [("1h", True), ("4h", True), ("1d", False), ("1w", False)]
_TF_BAR_KEY_SETTING = "auto_last_tf_bar_key"
_ET = ZoneInfo("America/New_York")
# Newest closed bar per timeframe that was already fetched. One shared dict, mutated in
# place (never rebound), so every importer sees the same state.
_last_tf_bar_key: dict[str, str] = {}


def _load_tf_bar_keys():
    """Restore the per-TF 'newest closed bar' markers saved by the previous process."""
    try:
        raw = settings_repo.settings_get(_TF_BAR_KEY_SETTING)
        if raw:
            loaded = json.loads(raw)
            if isinstance(loaded, dict):
                _last_tf_bar_key.clear()
                _last_tf_bar_key.update({str(k): str(v) for k, v in loaded.items()})
    except Exception as e:
        add_log(
            f"[auto] could not restore TF bar keys ({e}) — first round will fetch all timeframes",
            logging.WARNING,
        )


def _save_tf_bar_keys():
    try:
        settings_repo.settings_set(_TF_BAR_KEY_SETTING, json.dumps(_last_tf_bar_key))
    except Exception as e:
        add_log(f"[auto] could not persist TF bar keys: {e}", logging.WARNING)


def _last_completed_session_date(now_et):
    """Date of the most recent 16:00 ET close (previous day before today's close)."""
    d = now_et.date()
    if now_et.hour < 16:
        d -= timedelta(days=1)
    return d


def _tf_bar_key(tf: str, now_et) -> str:
    """Identity of the newest CLOSED bar for this timeframe. Changes => refetch.

    1d and 1w both roll on the daily close: the weekly bar is still forming during
    the week, so it is refreshed once per session (not once per week) to keep the
    current week's values current, while still ending the per-round rewrites.
    """
    if tf == "1h":
        return f"1h|{now_et.date()}|{now_et.hour}"
    if tf == "4h":
        return f"4h|{now_et.date()}|{now_et.hour // 4}"
    if tf in ("1d", "1w"):
        return f"{tf}|{_last_completed_session_date(now_et)}"
    return f"{tf}|{now_et.date()}|{now_et.hour}"


def steps_due(now_et=None, force_all=False):
    """AUTO_STEPS filtered to the timeframes whose newest closed bar changed.

    force_all=True -> legacy mode: all 4 timeframes every round, closed bar or not.
    Needed after adding new symbols: they have no 1d/1w bars in the DB yet, and the
    default mode waits for the bar key to change, so 1d/1w could stay missing for days.
    """
    if jobs_config.get_settings().force_all_tf or force_all:
        now_et = now_et or datetime.now(_ET)
        return list(AUTO_STEPS), {tf: _tf_bar_key(tf, now_et) for tf, _ in AUTO_STEPS}
    now_et = now_et or datetime.now(_ET)
    due, keys = [], {}
    for tf, ext in AUTO_STEPS:
        key = _tf_bar_key(tf, now_et)
        if _last_tf_bar_key.get(tf) != key:
            due.append((tf, ext))
            keys[tf] = key
    if not due:  # 1h always keeps the round alive even inside the same hour
        tf, ext = AUTO_STEPS[0]
        due, keys = [(tf, ext)], {tf: _tf_bar_key(tf, now_et)}
    return due, keys
