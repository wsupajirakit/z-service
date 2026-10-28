"""The times the page must state whenever it says "wait" or "close above".

User rule, 13 Aug 2026: every place that says wait/close must say
  * what to wait for — which bar of which timeframe closes
  * when it closes — in US (ET) and Thai time
  * which day to place the order once the trigger fires — the date in both zones

Every time comes from the **real NYSE calendar** (pandas_market_calendars), never an
assumed 16:00 close — holidays and half days (13:00 ET close) answer differently, and
being one trading day off means placing the order on the wrong day.

A round's as-of is "when the data was cut"; everything is computed from it, never from
the current time, so an old round still reads as what one had to wait for back then.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pandas as pd
import pandas_market_calendars as mcal

ET = ZoneInfo("America/New_York")
TH = ZoneInfo("Asia/Bangkok")

_CAL = mcal.get_calendar("NYSE")

TH_DAYS = ["จันทร์", "อังคาร", "พุธ", "พฤหัสฯ", "ศุกร์", "เสาร์", "อาทิตย์"]
TH_MONTHS = [
    "ม.ค.",
    "ก.พ.",
    "มี.ค.",
    "เม.ย.",
    "พ.ค.",
    "มิ.ย.",
    "ก.ค.",
    "ส.ค.",
    "ก.ย.",
    "ต.ค.",
    "พ.ย.",
    "ธ.ค.",
]


def _schedule(start: datetime, days: int = 30) -> pd.DataFrame:
    """The real NYSE trading-day schedule (holidays skipped, half days known)."""
    s = (start - timedelta(days=5)).date()
    e = (start + timedelta(days=days)).date()
    return _CAL.schedule(start_date=s.isoformat(), end_date=e.isoformat())


def fmt_both(dt_et: datetime) -> dict:
    """The same instant in both zones, with ready-to-show Thai text.

    Returns {et, th, both, date_et, date_th} — `both` is the line the page shows as-is.
    """
    if dt_et.tzinfo is None:
        dt_et = dt_et.replace(tzinfo=ET)
    dt_th = dt_et.astimezone(TH)
    d_et = f"{TH_DAYS[dt_et.weekday()]} {dt_et.day} {TH_MONTHS[dt_et.month - 1]}"
    d_th = f"{TH_DAYS[dt_th.weekday()]} {dt_th.day} {TH_MONTHS[dt_th.month - 1]}"
    et_s = f"{d_et} {dt_et:%H:%M} ET"
    th_s = f"{d_th} {dt_th:%H:%M} ไทย"
    return {
        "et": et_s,
        "th": th_s,
        "both": f"{et_s}  =  {th_s}",
        "et_iso": dt_et.isoformat(),
        "th_iso": dt_th.isoformat(),
        "date_et": dt_et.strftime("%Y-%m-%d"),
        "date_th": dt_th.strftime("%Y-%m-%d"),
    }


def _next_close(asof_et: datetime, sched: pd.DataFrame) -> tuple[datetime, bool]:
    """The next market close after the as-of, and whether it is a half day."""
    for _, row in sched.iterrows():
        close_et = row["market_close"].tz_convert(ET).to_pydatetime()
        if close_et > asof_et:
            open_et = row["market_open"].tz_convert(ET).to_pydatetime()
            half = (close_et - open_et) < timedelta(hours=5)
            return close_et, half
    raise ValueError("ไม่พบวันทำการถัดไปในตารางปฏิทิน")


def _next_session_open(after: datetime, sched: pd.DataFrame) -> datetime:
    for _, row in sched.iterrows():
        open_et = row["market_open"].tz_convert(ET).to_pydatetime()
        if open_et > after:
            return open_et
    raise ValueError("ไม่พบเวลาเปิดตลาดถัดไป")


def _next_4h_close(asof_et: datetime, sched: pd.DataFrame) -> datetime:
    """When the 4h bar the formula actually uses closes.

    Checked against real CSVs (2026-08-13): stock 4H bars sit on the extended-session
    grid starting 01:30/05:30/09:30/13:30/17:30 ET, and the formula's prep_frames
    (lib.py) keeps only bars starting 08:00–16:00, i.e. the 09:30 and 13:30 bars
    => the confirming bars **close at 13:30 and 17:30 ET** each trading day
    (an earlier version used 08:00/12:00/16:00, the index/FX grid — wrong for stocks).

    A half day (13:00 close) has no 13:30 bar — the 09:30 bar ends at the real bell.
    """
    for _, row in sched.iterrows():
        open_et = row["market_open"].tz_convert(ET).to_pydatetime()
        close_et = row["market_close"].tz_convert(ET).to_pydatetime()
        half = (close_et - open_et) < timedelta(hours=5)
        d = open_et.date()
        if half:
            cands = [close_et]
        else:
            cands = [
                datetime(d.year, d.month, d.day, 13, 30, tzinfo=ET),
                datetime(d.year, d.month, d.day, 17, 30, tzinfo=ET),
            ]
        for cand in cands:
            if cand > asof_et:
                return cand
    raise ValueError("ไม่พบแท่ง 4 ชม. ถัดไปในตารางปฏิทิน")


def _next_1h_close(asof_et: datetime, sched: pd.DataFrame) -> datetime:
    """When the 1h bar the formula actually uses closes — RTH bars only.

    The formula's prep_frames keeps 1H bars starting 09:00–15:xx (the 09:00 bar carries
    the open) => usable bars close on the hour 10:00–16:00 ET · on a half day the last
    one closes at the real bell. Extended bars (closing 17:00–20:00) are in the file but
    dropped by the formula — never waited for."""
    for _, row in sched.iterrows():
        open_et = row["market_open"].tz_convert(ET).to_pydatetime()
        close_et = row["market_close"].tz_convert(ET).to_pydatetime()
        d = open_et.date()
        h = 10
        while True:
            cand = datetime(d.year, d.month, d.day, h, 0, tzinfo=ET)
            if cand > close_et:
                break
            if cand > asof_et:
                return cand
            h += 1
        if close_et > asof_et and close_et.minute != 0:  # a half day does not close on the hour
            return close_et
    raise ValueError("ไม่พบแท่ง 1 ชม. ถัดไปในตารางปฏิทิน")


def _friday_close(asof_et: datetime, sched: pd.DataFrame) -> datetime:
    """A weekly bar closes at the closing bell of that week's last trading day."""
    last = None
    for _, row in sched.iterrows():
        close_et = row["market_close"].tz_convert(ET).to_pydatetime()
        if close_et <= asof_et:
            continue
        if last is not None and close_et.weekday() < last.weekday():
            break  # crossed into the next week
        last = close_et
        if close_et.weekday() == 4:  # Friday
            break
    return last


def bar_close(asof_iso: str, tf: str) -> dict | None:
    """When the next bar of this timeframe closes (counted from the round's as-of).

    tf: '1h' | '4h' | '1d' | '1w'
    """
    asof = _parse_et(asof_iso)
    if asof is None:
        return None
    sched = _schedule(asof, days=20)
    try:
        if tf == "1d":
            close_et, half = _next_close(asof, sched)
            label = "แท่งรายวันปิด (ระฆังปิดตลาด)" + (" — วันครึ่งวัน" if half else "")
        elif tf == "1w":
            close_et = _friday_close(asof, sched)
            label = "แท่งรายสัปดาห์ปิด (ระฆังปิดวันศุกร์)"
        elif tf == "4h":
            close_et = _next_4h_close(asof, sched)
            label = "แท่ง 4 ชม. ปิด"
        else:
            close_et = _next_1h_close(asof, sched)
            label = "แท่ง 1 ชม. ปิด"
    except (ValueError, AttributeError):
        return None
    if close_et is None:
        return None
    out = fmt_both(close_et)
    out["label"] = label
    out["tf"] = tf
    return out


def order_window(asof_iso: str, tf: str = "1d") -> dict | None:
    """If this bar closes through the trigger, at which market open to place the order.

    Returns both the bar close (wait for the result first) and the next market open
    (the day to place the order) in both zones — the whole answer to "the trigger
    fired, which day do I place the order" in one place.
    """
    close = bar_close(asof_iso, tf)
    if not close:
        return None
    asof = _parse_et(asof_iso)
    sched = _schedule(asof, days=20)
    close_et = datetime.fromisoformat(close["et_iso"])
    try:
        open_et = _next_session_open(close_et, sched)
    except ValueError:
        return None
    o = fmt_both(open_et)
    return {
        "bar_close": close,
        "order_open": o,
        "text": (
            f"รอ{close['label']} {close['both']} → ถ้าปิดผ่าน trigger "
            f"ตั้ง order ไว้ตอนเปิดตลาด {o['both']}"
        ),
    }


def _parse_et(asof_iso: str | None) -> datetime | None:
    """A round's as-of (with an offset or as ET wall clock) -> ET datetime."""
    if not asof_iso:
        return None
    try:
        dt = datetime.fromisoformat(str(asof_iso).replace("Z", "+00:00").strip()[:32])
    except ValueError:
        try:
            dt = datetime.fromisoformat(str(asof_iso).strip()[:19])
        except ValueError:
            return None
    return dt.replace(tzinfo=ET) if dt.tzinfo is None else dt.astimezone(ET)


def clock_pack(asof_iso: str) -> dict:
    """Every time the page needs for a round — computed once and attached to the round."""
    out = {"asof": None, "bars": {}, "order": {}}
    asof = _parse_et(asof_iso)
    if asof is None:
        return out
    out["asof"] = fmt_both(asof)
    for tf in ("1h", "4h", "1d", "1w"):
        b = bar_close(asof_iso, tf)
        if b:
            out["bars"][tf] = b
    for tf in ("1d", "4h"):
        o = order_window(asof_iso, tf)
        if o:
            out["order"][tf] = o
    return out
