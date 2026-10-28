"""What a round reads: per-timeframe freshness in Mongo, the requested timeframe subset, and
the export CSV set written with the exact builders /api/export_zip uses.

CSVs are written to a throwaway temp dir instead of being piped in-memory, because
`lib.run_screen(csv_dir)` is the single entry point that runs every formula, and feeding it
a directory keeps this package free of any re-implementation of the screen.
"""

import io
import os

import pandas as pd

from zservice.core.messages import coded

from . import deps
from .clock import now_iso, ts_key
from .config import TIMEFRAMES
from .errors import RadarError


def normalize_timeframes(timeframes) -> list[str]:
    """Validate + order a requested timeframe subset. None/empty = all four.
    Raises RadarError on an unknown timeframe (the API turns that into a 400)."""
    if not timeframes:
        return list(TIMEFRAMES)
    picked, seen = [], set()
    for raw in timeframes:
        tf = str(raw).strip().lower()
        if tf not in TIMEFRAMES:
            raise RadarError(f"unknown timeframe {raw!r} — use any of {TIMEFRAMES}")
        if tf not in seen:
            seen.add(tf)
            picked.append(tf)
    return [tf for tf in TIMEFRAMES if tf in seen]


def list_names(list_name: str | None):
    """Mirror _fetch_export_rows: 'All Symbols'/empty = the whole history."""
    if not list_name or list_name == "All Symbols":
        return None
    return [n.strip() for n in list_name.split(",")] if "," in list_name else list_name


def tf_status(list_name: str | None = None) -> dict:
    """Per timeframe: how many symbols are stored and when the rows the export
    will actually read were written.

    `fetched_at` is the timestamp z-service stamps on a batch when it SAVES the
    fetched TradingView data for that timeframe (main.py `_run_step` writes one
    unified timestamp per timeframe batch), so it marks the end of that fetch
    round — not the moment the bars themselves closed.
    """
    names = list_names(list_name)
    out = {}
    for tf in TIMEFRAMES:
        st = deps.store().history_tf_stats(tf, names)
        ts = sorted(st["timestamps"], key=ts_key)
        out[tf] = {
            "symbols_count": st["symbols_count"],
            "fetched_at_min": ts[0] if ts else None,
            "fetched_at_max": ts[-1] if ts else None,
            "fetched_at_distinct": len(set(ts)),
            # >0 means some symbols hold several rows for this timeframe (one per
            # extended_session flag). Harmless now that the export reads the
            # freshest row, but worth clearing out — it doubles the collection.
            "duplicate_symbols": st.get("duplicate_symbols", 0),
            "rows_total": st.get("rows_total", st["symbols_count"]),
            "has_data": st["symbols_count"] > 0,
        }
    fresh = [v["fetched_at_max"] for v in out.values() if v["fetched_at_max"]]
    return {
        "timeframes": out,
        "list_name": list_name or None,
        "newest_fetched_at": max(fresh) if fresh else None,
        "generated_at": now_iso(),
    }


def _csv_scan(raw: bytes) -> tuple[str | None, int]:
    """(newest bar Datetime, distinct symbols) of an export CSV we just built.
    Two columns only — the full parse happens once, inside the screen."""
    text = raw.decode("utf-8-sig", errors="replace")
    body = "".join(
        ln for ln in text.splitlines(keepends=True) if not ln.lstrip('"').startswith("#")
    )
    try:
        d = pd.read_csv(io.StringIO(body), usecols=["Symbol", "Datetime"])
    except Exception:
        return None, 0
    if d.empty:
        return None, 0
    newest = pd.to_datetime(d.Datetime, format="mixed", errors="coerce").max()
    return (None if pd.isna(newest) else str(newest)), int(d.Symbol.nunique())


def report_progress(progress, phase: str, message: dict) -> None:
    """`message` is a coded(...) dict: the job keeps its text and code side by side."""
    if progress:
        progress(phase, message)


def build_csv_set(
    csv_dir: str, timeframes: list[str], list_name: str | None, progress=None
) -> tuple[list[str], dict, list[str]]:
    """Write the export CSV set for `timeframes` (+ the formula file) into
    `csv_dir` using the export builders — byte-identical to /api/export_zip.
    Returns (timeframes actually written, per-tf metadata, skipped timeframes)."""
    m = deps.app()
    written, tf_meta, skipped = [], {}, []

    for tf in timeframes:
        label = tf.upper()
        message = coded("radar.fetching_tf", f"ดึงข้อมูล {label} จาก DB", tf=label)
        report_progress(progress, "building", message)
        rows = m.fetch_export_rows(tf, list_name)  # one Mongo read per tf
        if not rows:
            skipped.append(tf)
            continue
        parts = {}
        for part in (1, 2):
            raw = m.build_export_csv_bytes(tf, part, list_name, rows=rows)
            path = os.path.join(csv_dir, f"ztrade_export_{tf}_part{part}.csv")
            with open(path, "wb") as f:
                f.write(raw)
            parts[part] = _csv_scan(raw)

        stamps = sorted({r["timestamp"] for r in rows if r.get("timestamp")}, key=ts_key)
        bars = [b for b, _ in parts.values() if b]
        tf_meta[tf] = {
            "symbols_fetched": len(rows),
            "symbols_in_csv": sum(n for _, n in parts.values()),
            "fetched_at_min": stamps[0] if stamps else None,
            "fetched_at_max": stamps[-1] if stamps else None,
            "fetched_at_distinct": len(stamps),
            "bar_asof": max(bars) if bars else None,
        }
        written.append(tf)

    report_progress(
        progress, "building", coded("radar.formula_csv", "สร้างไฟล์สูตร + ข่าว (formula csv)")
    )
    with open(os.path.join(csv_dir, "ztrade_formula.csv"), "wb") as f:
        f.write(m.build_formula_csv_bytes())  # carries the live news rows

    return written, tf_meta, skipped
