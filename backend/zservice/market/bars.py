"""Bar timing: whether an intraday bar has closed, and 1h -> session-aligned 4h resampling
(moved unchanged from main.py)."""

import math
from datetime import timedelta

import pandas as pd

INTERVAL_DURATIONS = {
    "15m": timedelta(minutes=15),
    "30m": timedelta(minutes=30),
    "1h": timedelta(hours=1),
    "4h": timedelta(hours=4),
}


def is_bar_closed(ts, interval, exchange, sched, now_et):
    now_et = pd.Timestamp(now_et)
    if interval in INTERVAL_DURATIONS:
        close_time = ts + INTERVAL_DURATIONS[interval]
        return now_et >= close_time

    elif interval == "1d":
        ts_date = ts.floor("D")
        today = now_et.floor("D")
        if ts_date < today:
            return True
        elif ts_date == today:
            # check if we have schedule for this day
            if sched is not None and ts_date.tz_localize(None) in sched.index:
                day = sched.loc[ts_date.tz_localize(None)]
                market_close = day["market_close_et"]
                return now_et >= market_close
            else:
                # crypto fallback (ends at 00:00 next day)
                return now_et >= ts_date + timedelta(days=1)
        else:
            return False

    elif interval == "1w":
        monday = ts.floor("D")
        friday = monday + timedelta(days=4)
        today = now_et.floor("D")

        if today > friday:
            return True
        elif today == friday:
            if sched is not None and friday.tz_localize(None) in sched.index:
                day = sched.loc[friday.tz_localize(None)]
                market_close = day["market_close_et"]
                return now_et >= market_close
            else:
                return now_et >= friday + timedelta(days=1)
        else:
            return False

    return True


def resample_to_4h(df, sched, is_us_stock):
    buckets = []
    for ts, _row in df.iterrows():
        ts_date_naive = ts.floor("D").tz_localize(None)
        if sched is not None and ts_date_naive in sched.index:
            market_open = sched.loc[ts_date_naive, "market_open_et"]
        else:
            # fallback if not a trading day or no schedule
            if is_us_stock:
                market_open = ts.floor("D") + pd.Timedelta(hours=9, minutes=30)  # default 09:30
            else:
                market_open = ts.floor("D")  # midnight

        offset_hours = (ts - market_open).total_seconds() / 3600.0
        bucket_idx = math.floor(offset_hours / 4.0)
        anchor = market_open + pd.Timedelta(hours=bucket_idx * 4)
        buckets.append(anchor)

    df = df.copy()
    df["anchor"] = buckets

    resampled = df.groupby("anchor").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
    )
    resampled.index.name = "datetime"
    return resampled
