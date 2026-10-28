"""NYSE calendar and the market state at a given instant (moved unchanged from main.py)."""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pandas as pd
import pandas_market_calendars as mcal

# Built once at import; schedule() lookups reuse it.

nyse_cal = mcal.get_calendar("NYSE")


def get_market_state(now_utc: datetime, sched=None) -> str:
    """Return the market state for a given UTC datetime based on NYSE schedule."""
    et = now_utc.astimezone(ZoneInfo("America/New_York"))
    d_str = et.strftime("%Y-%m-%d")
    d_timestamp = pd.Timestamp(d_str)

    if sched is None:
        try:
            start_str = (et - timedelta(days=10)).strftime("%Y-%m-%d")
            end_str = (et + timedelta(days=10)).strftime("%Y-%m-%d")
            sched = nyse_cal.schedule(start_date=start_str, end_date=end_str)
        except Exception:
            return "UNKNOWN"

    if d_timestamp not in sched.index:
        return "CLOSED_HOLIDAY_OR_WEEKEND"

    day = sched.loc[d_timestamp]
    o = day["market_open"]
    c = day["market_close"]

    # half day check (duration less than 5 hours)
    half = (c - o).total_seconds() / 3600.0 < 5.0

    # Compare with timezone-aware datetimes
    if now_utc < o - timedelta(hours=5.5):
        return "PREMARKET_EARLY"
    elif now_utc < o:
        return "PREMARKET"
    elif now_utc < c:
        return "OPEN_HALF" if half else "OPEN_RTH"
    elif now_utc < c + timedelta(hours=4):
        return "AFTERHOURS"
    else:
        return "CLOSED_POST"
