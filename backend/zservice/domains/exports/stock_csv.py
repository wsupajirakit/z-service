"""ztrade_export_<interval>_part<n>.csv builder (from main.py, split into small steps;
tests/characterization pins the bytes stock-radar reads)."""

import csv
import io
from datetime import timedelta

import pandas as pd

from zservice.domains.market_data import config as md_config
from zservice.market.bars import INTERVAL_DURATIONS
from zservice.market.calendar import get_market_state, nyse_cal
from zservice.market.sessions import US_STOCK_EXCHANGES, get_bar_session_type

from .selection import fetch_export_rows, select_export_symbols

COLUMNS = [
    "Symbol", "Datetime", "Open", "High", "Low", "Close", "Volume",
    "EMA_20", "EMA_50", "EMA_100", "EMA_200", "RSI", "OBV", "CMF", "VWAP", "FVG",
    "RVOL", "RVOL_Deviation", "IPI", "IPI_Status", "Is_Closed_Bar", "Session",
    "Session_Minutes", "Rvol_Tod", "Atr14", "Dollar_Volume", "Gap_Flag", "Split_Adjusted",
    "Last_Split", "Ema_Stack", "Ipi_Valid",
]  # fmt: skip
# Columns copied straight from the stored record (after Symbol), in file order.
_RAW_FIELDS = [
    "datetime", "open", "high", "low", "close", "volume", "EMA_20", "EMA_50", "EMA_100",
    "EMA_200", "RSI", "OBV", "CMF", "VWAP", "FVG", "RVOL", "RVOL_Deviation", "IPI",
    "IPI_Status",
]  # fmt: skip
_INVALID_IPI_STATUS = ["N/A (ext)", "N/A (low vol)", "N/A (open)"]
_SCHEDULE_MARGIN = timedelta(days=7)


def build_export_csv_bytes(
    interval: str, part: int = 1, list_name: str | None = None, rows=None
) -> bytes:
    """The history-export CSV for one interval/part, as bytes.

    Shared by /api/export and /api/export_zip. `rows` may be pre-fetched so a caller
    building both parts of an interval queries Mongo once (halves export_zip work).
    """
    if rows is None:
        rows = fetch_export_rows(interval, list_name)
    # Normal symbols (count == expected) + current short-history symbols; see
    # select_export_symbols for what is still dropped.
    parsed, expected_count, short_history = select_export_symbols(rows, interval)
    half = len(parsed) // 2
    selected_rows = parsed[:half] if part == 1 else parsed[half:]

    output = io.StringIO()
    _write_metadata(output, selected_rows, expected_count, short_history)
    writer = csv.writer(output)
    writer.writerow(COLUMNS)
    for row in selected_rows:
        _write_symbol(writer, row, interval)
    # utf-8-sig adds the BOM (Byte Order Mark) so Excel detects UTF-8 automatically
    return output.getvalue().encode("utf-8-sig")


def _write_metadata(output, selected_rows, expected_count, short_history) -> None:
    """Comment header. Written directly (NOT via csv.writer): a comment that contains a
    comma — e.g. "(ET wall time, no offset suffix)" — would be quoted by csv.writer, so
    the line would start with '"' instead of '#', and readers that skip on a leading '#'
    (pandas comment='#') would mis-parse it as the header."""
    meta = _asof(selected_rows)
    output.write(f"# data_asof_utc: {meta['utc']}\r\n")
    output.write(f"# data_asof_et: {meta['et']}\r\n")
    output.write(f"# market_state: {meta['state']}\r\n")
    output.write(
        f"# tz_base: America/New_York ET wall time no offset suffix | dst_active: {meta['dst']}\r\n"
    )
    output.write(f"# cmf_period: {md_config.get_settings().cmf_period}\r\n")
    # Bar-count disclosure. bars_expected = the normal per-symbol count; every symbol of
    # THIS INTERVAL (part1 + part2 alike) with fewer bars is listed as SYM=N — a recent
    # listing/spin-off, its EMA/RSI/CMF are seeded from its first bar. The list is the
    # same in both parts so either header is enough.
    output.write(f"# bars_expected: {expected_count if expected_count is not None else 'N/A'}\r\n")
    sh = ",".join(f"{s}={n}" for s, n in sorted(short_history.items()))
    output.write(f"# short_history: {sh or 'none'}\r\n")


def _asof(selected_rows) -> dict:
    """As-of stamps of the part, from its first symbol's fetch timestamp."""
    meta = {"state": "UNKNOWN", "utc": "N/A", "et": "N/A", "dst": "false"}
    if not selected_rows:
        return meta
    try:
        dt = pd.to_datetime(selected_rows[0][2])
        if dt.tzinfo is None:
            dt = dt.tz_localize("UTC")
        dt_utc = dt.tz_convert("UTC")
        dt_et = dt_utc.tz_convert("America/New_York")
        meta["state"] = get_market_state(dt_utc)
        meta["utc"] = dt_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
        meta["et"] = dt_et.isoformat()
        meta["dst"] = "true" if dt_et.dst() != timedelta(0) else "false"
    except Exception as ex:
        print(f"Error computing CSV metadata: {ex}")
    return meta


def _write_symbol(writer, row, interval: str) -> None:
    """One symbol's bars. A failing record skips the rest of that symbol only (the rows
    already written stay), as before."""
    sym, records, exch = row[0], row[1], row[4]
    us_stock = exch.upper() in US_STOCK_EXCHANGES
    sched = _schedule(records) if us_stock and records else None
    try:
        for rec in records:
            writer.writerow(_record_row(sym, rec, interval, sched, us_stock))
    except Exception:  # a malformed stored row ends the symbol, as before
        return


def _schedule(records):
    """NYSE schedule around the symbol's bars, for fields older rows may lack."""
    try:
        first_date = pd.to_datetime(records[0].get("datetime")).date() - _SCHEDULE_MARGIN
        last_date = pd.to_datetime(records[-1].get("datetime")).date() + _SCHEDULE_MARGIN
        return nyse_cal.schedule(start_date=first_date.isoformat(), end_date=last_date.isoformat())
    except Exception:
        return None


def _default(value, fallback):
    return fallback if value is None else value


def _record_row(sym, rec: dict, interval: str, sched, us_stock: bool) -> list:
    """CSV row for one stored bar; fields missing in older rows are derived."""
    is_closed = _default(rec.get("is_closed_bar"), True)
    dt_val = pd.to_datetime(rec.get("datetime"))
    session_type = rec.get("session")
    if session_type is None:
        session_type = get_bar_session_type(dt_val, sched, us_stock, interval)
    sm = rec.get("session_minutes")
    if sm is None:
        sm = _session_minutes(dt_val, interval, sched, us_stock)
    rvol_tod = rec.get("rvol_tod")
    if rvol_tod is None:
        rvol_tod = rec.get("RVOL_slot", rec.get("RVOL", ""))
    dollar_volume = rec.get("dollar_volume")
    if dollar_volume is None:
        dollar_volume = (rec.get("close", 0) or 0) * (rec.get("volume", 0) or 0)
    return [
        sym,
        *(rec.get(field, "") for field in _RAW_FIELDS),
        is_closed,
        session_type,
        sm,
        rvol_tod,
        _default(rec.get("atr14"), rec.get("ATR", "")),
        dollar_volume,
        _default(rec.get("gap_flag"), 0.0),
        _default(rec.get("split_adjusted"), True),
        _default(rec.get("last_split"), "N/A"),
        _ema_stack(rec),
        _ipi_valid(rec, is_closed),
    ]


def _session_minutes(dt_val, interval: str, sched, us_stock: bool) -> float:
    if not (us_stock and sched is not None):
        if interval in INTERVAL_DURATIONS:
            return INTERVAL_DURATIONS[interval].total_seconds() / 60.0
        return {"1d": 1440.0, "1w": 10080.0}.get(interval, 0.0)
    t_date = dt_val.floor("D")
    if t_date not in sched.index:
        return 390.0 if interval == "1d" else (1950.0 if interval == "1w" else 0.0)
    day = sched.loc[t_date]
    mins = (day["market_close"] - day["market_open"]).total_seconds() / 60.0
    if interval in INTERVAL_DURATIONS:
        return INTERVAL_DURATIONS[interval].total_seconds() / 60.0
    if interval == "1w":
        monday = dt_val.floor("D")
        week_days = sched.loc[monday : monday + pd.Timedelta(days=6)]
        return sum(
            (d["market_close"] - d["market_open"]).total_seconds() / 60.0
            for _, d in week_days.iterrows()
        )
    return mins  # 1d and anything else


def _ema_stack(rec: dict) -> str:
    stack = rec.get("ema_stack")
    if stack is not None:
        return stack
    e20, e50, e100, e200 = (rec.get(f"EMA_{n}") for n in (20, 50, 100, 200))
    if e20 is None or e50 is None or e100 is None or e200 is None:
        return "mixed"
    if e20 > e50 > e100 > e200:
        return "bull"
    if e20 < e50 < e100 < e200:
        return "bear"
    return "mixed"


def _ipi_valid(rec: dict, is_closed):
    valid = rec.get("ipi_valid")
    if valid is not None:
        return valid
    return (
        (rec.get("IPI") is not None)
        and is_closed
        and (rec.get("IPI_Status") not in _INVALID_IPI_STATUS)
    )
