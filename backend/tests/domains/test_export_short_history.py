"""Export symbol selection: short-history symbols are kept, broken ones dropped.

Regression guard for the 1W export silently dropping every recent listing /
spin-off (ARXS, SKHY, SPCX, ...): the old filter kept ONLY symbols whose stored
bar count equalled the mode (80), so a stock with 16-73 weekly bars of total
history never reached the CSV.

Runs offline against the real builder (`_build_export_csv_bytes`) with fake
Mongo rows — no DB, no TradingView:

    venv/bin/python -m pytest tests/domains/test_export_short_history.py
"""

import io
import json
import os
import re
from datetime import datetime, timedelta

os.environ.setdefault("ZS_AUTOSTART", "0")


# Offline: present-but-empty keys stop load_dotenv from filling in DB / TradingView
# credentials, so importing main neither connects to Mongo nor logs in to TV.


import pandas as pd

from zservice.domains.exports import selection, stock_csv

N_COLS = 31


NEWEST_1W = datetime(2026, 10, 19)  # a Monday — weekly bar stamp


NEWEST_1D = datetime(2026, 10, 21)  # a Wednesday


def bars(n, newest, step):
    """n stored records ending at `newest`, oldest first (the shape process_symbol stores)."""
    out = []
    for i in range(n):
        t = newest - step * (n - 1 - i)
        px = 10.0 + i
        out.append(
            {
                "datetime": t.strftime("%Y-%m-%d %H:%M:%S"),
                "open": px,
                "high": px + 1,
                "low": px - 1,
                "close": px + 0.5,
                "volume": 1000 + i,
                "EMA_20": px,
                "EMA_50": px,
                "EMA_100": px,
                "EMA_200": px,
                "is_closed_bar": True,
            }
        )
    return out


def row(sym, records=None, raw=None, exchange="NASDAQ"):
    return {
        "symbol": sym,
        "timestamp": "2026-10-22T07:04:49+07:00",
        "exchange": exchange,
        "result_json": raw if raw is not None else json.dumps(records),
    }


def weekly(sym, n, newest=NEWEST_1W):
    return row(sym, bars(n, newest, timedelta(days=7)))


def daily(sym, n, newest=NEWEST_1D):
    return row(sym, bars(n, newest, timedelta(days=1)))


def parse(raw: bytes):
    """(meta dict, data frame, raw text) — the way stock-radar's read_meta reads it."""
    text = raw.decode("utf-8-sig")
    meta = {}
    for line in text.splitlines():
        if not line.startswith("#"):
            break
        m = re.match(r"#\s*([\w]+):\s*(.+)", line)
        if m:
            meta[m.group(1)] = m.group(2).strip()
    df = pd.read_csv(io.StringIO(text), comment="#")
    return meta, df, text


def export_both(interval, rows):
    p1 = parse(stock_csv.build_export_csv_bytes(interval, 1, rows=rows))
    p2 = parse(stock_csv.build_export_csv_bytes(interval, 2, rows=rows))
    return p1, p2


def test_normal_symbols_unchanged():
    rows = [weekly(s, 80) for s in ["AAA", "BBB", "CCC", "DDD", "EEE", "FFF"]]
    (m1, d1, t1), (m2, d2, t2) = export_both("1w", rows)
    assert sorted(d1.Symbol.unique()) == ["AAA", "BBB", "CCC"]
    assert sorted(d2.Symbol.unique()) == ["DDD", "EEE", "FFF"]
    assert d1.groupby("Symbol").size().eq(80).all() and d2.groupby("Symbol").size().eq(80).all()
    assert m1["bars_expected"] == "80" and m1["short_history"] == "none"
    assert m2["short_history"] == "none"
    assert len(d1.columns) == N_COLS, len(d1.columns)
    for t in (t1, t2):
        meta_lines = [line for line in t.splitlines() if line and not line[0].isalpha()]
        assert all(line.startswith("#") for line in meta_lines), meta_lines


def test_short_history_current_kept():
    rows = [
        weekly("AAA", 80),
        weekly("ARXS", 28),
        weekly("BBB", 80),
        weekly("CCC", 80),
        weekly("SKHY", 16),
        weekly("ZZZ", 80),
    ]
    (m1, d1, _), (m2, d2, _) = export_both("1w", rows)
    got = pd.concat([d1, d2])
    sizes = got.groupby("Symbol").size().to_dict()
    assert sizes == {"AAA": 80, "ARXS": 28, "BBB": 80, "CCC": 80, "SKHY": 16, "ZZZ": 80}, sizes
    # both parts carry the full interval-wide list, so reading either header is enough
    assert m1["short_history"] == m2["short_history"] == "ARXS=28,SKHY=16", m1["short_history"]
    assert m1["bars_expected"] == "80"
    assert len(got.columns) == N_COLS


def test_short_history_daily_weekend_gap_kept():
    # newest daily bar on Friday while the batch is on Wednesday after a long weekend
    rows = [
        daily("AAA", 80),
        daily("BBB", 80),
        daily("SKHY", 73, newest=NEWEST_1D - timedelta(days=5)),
    ]
    (m1, d1, _), (_m2, d2, _) = export_both("1d", rows)
    assert "SKHY" in set(d1.Symbol) | set(d2.Symbol)
    assert m1["short_history"] == "SKHY=73"


def test_stale_and_broken_dropped():
    rows = [
        weekly("AAA", 80),
        weekly("BBB", 80),
        weekly("CCC", 80),
        weekly("DDD", 80),
        weekly("DEAD", 20, newest=NEWEST_1W - timedelta(days=60)),  # stale short series
        weekly("BIG", 100),  # count > expected
        row("EMPTY", []),  # empty result
        row("JUNK", raw="not json"),  # unparsable
        row("NODATE", [{"datetime": "garbage", "close": 1.0}] * 5),
    ]  # short + unparsable stamp
    (m1, d1, _), (_m2, d2, _) = export_both("1w", rows)
    got = set(d1.Symbol) | set(d2.Symbol)
    assert got == {"AAA", "BBB", "CCC", "DDD"}, got
    assert m1["short_history"] == "none" and m1["bars_expected"] == "80"


def test_daily_stale_short_dropped():
    rows = [
        daily("AAA", 80),
        daily("BBB", 80),
        daily("OLD", 40, newest=NEWEST_1D - timedelta(days=12)),
    ]
    (_m1, d1, _), (_m2, d2, _) = export_both("1d", rows)
    assert "OLD" not in set(d1.Symbol) | set(d2.Symbol)


def test_part_split():
    syms = [f"S{i:02d}" for i in range(11)]
    rows = [weekly(s, 80 if i % 3 else 20 + i) for i, s in enumerate(syms)]
    (m1, d1, _), (m2, d2, _) = export_both("1w", rows)
    p1, p2 = list(dict.fromkeys(d1.Symbol)), list(dict.fromkeys(d2.Symbol))
    assert not set(p1) & set(p2), "a symbol landed in both parts"
    assert p1 + p2 == syms, (p1, p2)  # nothing lost, original order kept
    assert len(p1) == len(syms) // 2 and len(p2) == len(syms) - len(syms) // 2
    assert m1["short_history"] == m2["short_history"]


def test_tie_prefers_larger_count():
    # watchlist-scoped export: one normal name and one new listing -> expected must be 80, not 16
    sel, expected, short = selection.select_export_symbols(
        [weekly("NEWCO", 16), weekly("OLDCO", 80)], "1w"
    )
    assert expected == 80, expected
    assert [p[0] for p in sel] == ["NEWCO", "OLDCO"] and short == {"NEWCO": 16}


def test_empty_input():
    raw = stock_csv.build_export_csv_bytes("1w", 1, rows=[])
    meta, df, _ = parse(raw)
    assert df.empty and list(df.columns)[:2] == ["Symbol", "Datetime"]
    assert meta["bars_expected"] == "N/A" and meta["short_history"] == "none"
