"""Which stored snapshots go into an export (moved unchanged from main.py)."""

import json
from datetime import timedelta

import pandas as pd

from zservice.db.repos import history as history_repo

# How far a SHORT-HISTORY symbol's newest bar may trail the batch's newest bar and
# still count as current. Calendar time, so a weekend / market holiday between the
# two fetches never drops a live symbol; a halted, delisted or long-unrefreshed
# series is older than this and stays out of the export.
SHORT_HISTORY_GRACE = {
    "15m": timedelta(days=4),
    "30m": timedelta(days=4),
    "1h": timedelta(days=4),
    "4h": timedelta(days=4),
    "1d": timedelta(days=5),
    "1w": timedelta(days=14),
}


def fetch_export_rows(interval: str, list_name: str | None = None):
    """Latest snapshot per symbol for an interval (optionally watchlist-scoped)."""
    if list_name and list_name != "All Symbols":
        names = [n.strip() for n in list_name.split(",")] if "," in list_name else list_name
        return history_repo.history_latest_per_symbol(interval, names)
    return history_repo.history_latest_per_symbol(interval)


def newest_bar_ts(records):
    """Newest bar stamp of a stored result as a naive ET Timestamp (None if unparsable)."""
    try:
        ts = pd.to_datetime(records[-1].get("datetime"))
    except Exception:
        return None
    if ts is None or pd.isna(ts):
        return None
    if ts.tzinfo is not None:
        ts = ts.tz_convert("America/New_York").tz_localize(None)
    return ts


def select_export_symbols(rows, interval: str):
    """Pick which stored snapshots go into an export, in their original order.

    Every symbol is stored with `rows` bars (80) — the expected count is the most
    common one (ties -> the larger count). A symbol with FEWER bars is a recent
    listing / spin-off whose whole TradingView history is shorter than `rows`; it
    used to be dropped as "broken" (count != mode), so new IPOs vanished from every
    1W export. It is now KEPT when its newest bar is current (no older than the
    batch's typical newest bar minus SHORT_HISTORY_GRACE) and reported in
    `short` so the CSV header can name it. Still dropped: unparsable / empty
    results, counts ABOVE the expected count, and short series whose newest bar is
    stale or unparsable.

    Returns (selected, expected_count, short) where selected is a list of
    (symbol, records, timestamp, count, exchange) and short is {symbol: count}.
    """
    from collections import Counter

    parsed = []
    for row in rows or []:
        try:
            records = json.loads(row["result_json"])
        except Exception:  # noqa: S112 — unparsable stored JSON = broken row, dropped
            continue
        if not isinstance(records, list) or not records:
            continue
        parsed.append((row["symbol"], records, row["timestamp"], len(records), row["exchange"]))
    if not parsed:
        return [], None, {}

    counts = Counter(p[3] for p in parsed)
    expected = max(counts, key=lambda c: (counts[c], c))

    newest = {p[0]: newest_bar_ts(p[1]) for p in parsed if p[3] <= expected}
    ref_counts = Counter(
        newest[p[0]] for p in parsed if p[3] == expected and newest[p[0]] is not None
    )
    ref = max(ref_counts, key=lambda t: (ref_counts[t], t)) if ref_counts else None
    grace = SHORT_HISTORY_GRACE.get(interval, timedelta(days=4))

    selected, short = [], {}
    for p in parsed:
        if p[3] == expected:
            selected.append(p)
        elif p[3] < expected:
            ts = newest[p[0]]
            if ts is not None and (ref is None or ts >= ref - grace):
                selected.append(p)
                short[p[0]] = p[3]
    return selected, expected, short
