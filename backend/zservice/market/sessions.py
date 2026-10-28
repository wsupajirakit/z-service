"""Session labels for a bar (PRE / RTH / POST / HALF / CLOSED) and RTH coverage
(moved unchanged from main.py)."""

import pandas as pd

# Exchanges whose bars follow the NYSE calendar (sessions, holidays, half days).
US_STOCK_EXCHANGES = ["NYSE", "NASDAQ", "AMEX", "NYSE ARCA", "NYSEARCA", "BATS", "CBOE", "ARCX"]


def get_bar_session_type(t, sched, is_us_stock, interval) -> str:
    """Return the session type label (PRE, POST, HALF, RTH, CLOSED) for a given bar timestamp."""
    if not is_us_stock:
        return "RTH"

    t_et = t
    if t_et.tzinfo is None:
        t_et = t_et.tz_localize("America/New_York")
    else:
        t_et = t_et.tz_convert("America/New_York")

    t_date = t_et.floor("D").tz_localize(None)
    if sched is not None and t_date not in sched.index:
        return "CLOSED"

    hour = t_et.hour
    minute = t_et.minute
    time_val = hour + (minute / 60.0)

    if 4.0 <= time_val < 9.5:
        return "PRE"
    elif 9.5 <= time_val < 16.0:
        return "RTH"
    elif 16.0 <= time_val < 20.0:
        return "POST"
    else:
        return "CLOSED"


def check_in_rth(ts, sched, is_us_stock):
    if not is_us_stock:
        return True

    ts_et = ts
    if ts_et.tzinfo is None:
        ts_et = ts_et.tz_localize("America/New_York")
    else:
        ts_et = ts_et.tz_convert("America/New_York")

    ts_date = ts_et.floor("D").tz_localize(None)
    if sched is not None and ts_date not in sched.index:
        return False

    hour = ts_et.hour
    minute = ts_et.minute
    time_val = hour + (minute / 60.0)
    return 9.5 <= time_val < 16.0


def get_weekly_sess_ratio(ts, sched):
    # ts is a weekly bar timestamp (Monday)
    monday = ts.floor("D").tz_localize(None)
    sunday = monday + pd.Timedelta(days=6)

    # filter sched index for days in this week
    week_days = sched.loc[monday:sunday]
    if len(week_days) == 0:
        return 0.0

    total_minutes = 0.0
    for _idx, day in week_days.iterrows():
        day_minutes = (day["market_close"] - day["market_open"]).total_seconds() / 60.0
        total_minutes += day_minutes

    return total_minutes / 1950.0
