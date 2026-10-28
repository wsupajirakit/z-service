"""Step 2: NYSE schedule, the still-forming last bar, non-session bars, session tags."""

import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pandas as pd

from zservice.market.bars import INTERVAL_DURATIONS, is_bar_closed
from zservice.market.calendar import nyse_cal
from zservice.market.sessions import check_in_rth, get_bar_session_type, get_weekly_sess_ratio

log = logging.getLogger("zs.market_data")

RTH_MINUTES = 390.0  # a full NYSE regular session
SCHEDULE_MARGIN = timedelta(days=7)


def us_schedule(df: pd.DataFrame, us_stock: bool):
    """NYSE schedule around the bars (with ET open/close columns), or None."""
    if not us_stock or df.empty:
        return None
    try:
        start_date = df.index.min().date() - SCHEDULE_MARGIN
        end_date = df.index.max().date() + SCHEDULE_MARGIN
        sched = nyse_cal.schedule(start_date=start_date.isoformat(), end_date=end_date.isoformat())
        sched["market_open_et"] = sched["market_open"].dt.tz_convert("America/New_York")
        sched["market_close_et"] = sched["market_close"].dt.tz_convert("America/New_York")
        return sched
    except Exception as ex:
        print(f"Error loading market calendar: {ex}")
        return None


def split_open_bar(df: pd.DataFrame, symbol: str, interval: str, exchange: str, sched):
    """(closed bars, the still-forming last bar or None). Closed bars get is_closed_bar."""
    open_bar_row = None
    if not df.empty:
        last_index = df.index[-1]
        now_et = datetime.now(ZoneInfo("America/New_York"))
        if not is_bar_closed(last_index, interval, exchange, sched, now_et):
            print(f"[{symbol}] Last bar at {last_index} is still open/running. Separating it.")
            open_bar_row = df.iloc[-1:].copy()
            df = df.iloc[:-1].copy()
    if not df.empty:
        df["is_closed_bar"] = True
    return df, open_bar_row


def drop_non_session_bars(df: pd.DataFrame, interval: str, us_stock: bool, sched):
    """Drop holiday / weekend candles (1w: weeks without any session)."""
    if not df.empty and us_stock and sched is not None:
        if interval in ["1h", "4h", "1d"]:
            df = df[df.index.floor("D").tz_localize(None).isin(sched.index)].copy()
        elif interval == "1w":
            weekly_ratios = [get_weekly_sess_ratio(t, sched) for t in df.index]
            df["sess_ratio"] = weekly_ratios
            df = df[df["sess_ratio"] > 0.0].copy()
    return df


def tag_sessions(df: pd.DataFrame, interval: str, us_stock: bool, sched) -> None:
    """sess_ratio (share of a full session), in_rth and session label, in place."""
    if df.empty:
        return
    if "sess_ratio" not in df.columns:
        if interval == "1d" and us_stock and sched is not None:
            df["sess_ratio"] = [_day_ratio(t.floor("D").tz_localize(None), sched) for t in df.index]
        else:
            df["sess_ratio"] = 1.0
    df["in_rth"] = [check_in_rth(t, sched, us_stock) for t in df.index]
    df["session"] = [get_bar_session_type(t, sched, us_stock, interval) for t in df.index]


def _day_ratio(t_date, sched) -> float:
    if t_date in sched.index:
        day = sched.loc[t_date]
        return (day["market_close"] - day["market_open"]).total_seconds() / 60.0 / RTH_MINUTES
    return 1.0


def session_minutes(df: pd.DataFrame, interval: str, us_stock: bool, sched) -> None:
    """session_minutes and half_day for every bar (the open one included), in place."""
    minutes, half_days = [], []
    for t in df.index:
        t_date = t.floor("D")
        if us_stock and sched is not None and t_date in sched.index:
            day = sched.loc[t_date]
            mins = (day["market_close"] - day["market_open"]).total_seconds() / 60.0
            minutes.append(_session_minutes_us(t, interval, mins, sched))
            half_days.append(mins / 60.0 < 5.0)
        else:
            # Fallback for crypto/gold or if sched is None
            minutes.append(_session_minutes_24h(interval))
            half_days.append(False)
    df["session_minutes"] = minutes
    df["half_day"] = half_days


def _session_minutes_us(t, interval: str, mins: float, sched) -> float:
    if interval in INTERVAL_DURATIONS:
        return INTERVAL_DURATIONS[interval].total_seconds() / 60.0
    if interval == "1d":
        return mins
    if interval == "1w":
        monday = t.floor("D")
        sunday = monday + pd.Timedelta(days=6)
        week_days = sched.loc[monday:sunday]
        return sum(
            (day["market_close"] - day["market_open"]).total_seconds() / 60.0
            for _, day in week_days.iterrows()
        )
    return mins


def _session_minutes_24h(interval: str) -> float:
    if interval in INTERVAL_DURATIONS:
        return INTERVAL_DURATIONS[interval].total_seconds() / 60.0
    if interval == "1d":
        return 1440.0
    if interval == "1w":
        return 10080.0
    return 0.0
