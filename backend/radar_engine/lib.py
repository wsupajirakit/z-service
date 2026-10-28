"""radar_lib — reusable fund-manager functions for the CSV/UIPT screen (Mode C).

Everything the skill previously rebuilt ad-hoc per session lives here:
loading, sanity checks, tz normalization, indicator recompute (CMF/OBV/RVOL/IPI),
Layer-0 regime, sector flow map, UIPT staging + kill switch, coil detector,
entry levels, portfolio marks, compact digest, and history snapshots.

Design goal: `radar_run.py` prints ONE compact digest; all detail goes to
history/<asof>/full.json so future sessions read files instead of recomputing.
"""
from __future__ import annotations
import glob, hashlib, io, json, math, os, re
import numpy as np
import pandas as pd

TFS = ["1w", "1d", "4h", "1h"]
BAR_HOURS = {"1h": 1, "4h": 4, "1d": 24, "1w": 168}
# symbols that are indices/futures/fx/crypto — no equity session, some no volume
NONEQ_KNOWN = {"BTCUSDT", "DXY", "US10", "US10Y", "VIX", "VIX3M", "VIX9D", "WTI",
               "XAUUSD", "USDTHB", "TICK", "NDX", "SPX", "MOVE"}
MACRO_ROW_ORDER = ["SPY", "NDX", "IWM", "VIX", "VIX9D", "VIX3M", "US10", "US10Y",
                   "DXY", "USDTHB", "XAUUSD", "WTI", "BTCUSDT", "HYG", "TICK"]
ETF_KNOWN = {"SMH", "SOXX", "IGV", "SKYY", "BOTZ", "ROBO", "PAVE", "FIW", "UFO",
             "CIBR", "XBI", "XLF", "XLU", "XLV", "XLK", "XLI", "XLE", "XLRE",
             "COPX", "LQD", "IYT", "XHB", "XME", "ITA", "IWM", "SPY", "QQQ", "HYG"}
TRIPWIRES = {"US10Y": 4.55, "DXY_BREAKOUT": 101.8, "DXY_REJECT": 100.0, "WTI": 72.0}


# ---------------------------------------------------------------- loading ----

def newest_parts(csv_dir: str, tf: str) -> list[str]:
    """Pick the newest part1+part2 per timeframe (handles '(N)' suffix copies)."""
    out = []
    for part in ("part1", "part2"):
        cands = glob.glob(os.path.join(csv_dir, f"ztrade_export_{tf}_{part}*.csv"))
        if cands:
            out.append(max(cands, key=os.path.getmtime))
    return out


def newest_formula(csv_dir: str) -> str | None:
    cands = glob.glob(os.path.join(csv_dir, "ztrade_formula*.csv"))
    return max(cands, key=os.path.getmtime) if cands else None


def fingerprint(paths: list[str]) -> str:
    """CONTENT hash with normalized names: a re-uploaded duplicate like
    'ztrade_export_1d_part1(9).csv' (new name+mtime, same bytes) yields the
    same fingerprint, so auto mode correctly reuses the saved snapshot."""
    h = hashlib.sha1()
    for p in sorted(paths, key=lambda x: re.sub(r"\(\d+\)", "", os.path.basename(x))):
        h.update(re.sub(r"\(\d+\)", "", os.path.basename(p)).encode())
        with open(p, "rb") as f:
            h.update(f.read())
    return h.hexdigest()[:16]


def clean_csv(csv_dir: str) -> list[str]:
    """Delete superseded ztrade csv copies; keep the newest (mtime) per
    normalized name (tf/part + formula). Returns removed basenames."""
    removed, groups = [], {}
    for p in glob.glob(os.path.join(csv_dir, "ztrade_*.csv")):
        groups.setdefault(re.sub(r"\(\d+\)", "", os.path.basename(p)), []).append(p)
    for ps in groups.values():
        keep = max(ps, key=os.path.getmtime)
        for p in ps:
            if p != keep:
                os.remove(p)
                removed.append(os.path.basename(p))
    return removed


def clean_history(base: str, keep: int = 10) -> list[str]:
    """Delete oldest snapshots, keep the newest `keep`. Returns removed names."""
    import shutil
    removed = []
    snaps = list_snapshots(base)
    for s in (snaps[:-keep] if keep > 0 else snaps):
        shutil.rmtree(os.path.join(base, s))
        removed.append(s)
    latest = os.path.join(base, "LATEST")
    if snaps and keep > 0:
        with open(latest, "w") as f:
            f.write(snaps[-1])
    elif os.path.exists(latest):
        os.remove(latest)
    return removed


def read_meta(path: str) -> dict:
    meta = {}
    with open(path, encoding="utf-8-sig") as f:
        for line in f:
            # tolerate a comment line that a buggy exporter csv-quoted, so it
            # begins with '"#' instead of '#'
            probe = line.lstrip('"')
            if not probe.startswith("#"):
                break
            m = re.match(r"#\s*([\w]+):\s*(.+)", probe)
            if m:
                meta[m.group(1)] = m.group(2).rstrip('"').strip()
    return meta


def _read_export(path: str) -> pd.DataFrame:
    """Read one export csv, skipping metadata even when a comment line was
    csv-quoted (starts with '\"#') — pandas comment='#' misses those."""
    with open(path, encoding="utf-8-sig") as fh:
        lines = [ln for ln in fh if not ln.lstrip('"').startswith("#")]
    return pd.read_csv(io.StringIO("".join(lines)))


def load_exports(csv_dir: str) -> tuple[dict, dict, list[str], dict]:
    """Return ({tf: df}, meta, file_list, {tf: meta}). Missing timeframes are skipped.

    z-service fetches a timeframe only when that timeframe's bar has closed, so the
    four exports carry DIFFERENT `# data_asof_*` stamps — 1h may be hours newer than
    1w. Each file's header is therefore kept separately in `metas`; `meta` is the
    header of the FRESHEST leg and exists only for display/back-compat. Never use a
    single global as-of to judge bars of another timeframe.
    """
    tfs, files, metas = {}, [], {}
    for tf in TFS:
        parts = newest_parts(csv_dir, tf)
        if not parts:
            continue
        files += parts
        metas[tf] = read_meta(parts[0])
        d = pd.concat([_read_export(p) for p in parts], ignore_index=True)
        d["Datetime"] = pd.to_datetime(d["Datetime"], format="mixed")
        tfs[tf] = d.sort_values(["Symbol", "Datetime"]).reset_index(drop=True)
    fresh_tf = max(metas, key=lambda t: metas[t].get("data_asof_et") or "", default=None)
    meta = metas.get(fresh_tf, {}) if fresh_tf else {}
    return tfs, meta, files, metas


def load_news(csv_dir: str) -> list[str]:
    path = newest_formula(csv_dir)
    if not path:
        return []
    rows = pd.read_csv(path, encoding="utf-8-sig")
    news = rows[rows.Section == "LATEST_FINANCIAL_NEWS"]
    out = []
    for _, r in news.iterrows():
        if "Source" in str(r.Key):
            continue
        title = str(r.Value).rsplit(", http", 1)[0]
        # strip a leading RFC-2822 or ISO date stamp
        title = re.sub(r"^(\w{3}, )?\d{1,2} \w{3} \d{4} [\d:]+ ([+\-]\d{4}|GMT|UTC|\w{3}),\s*", "", title)
        title = re.sub(r"^\d{4}-\d{2}-\d{2} [\d:]+,\s*", "", title)
        src = r.Key if pd.notna(r.Key) else (r.Subsection if pd.notna(r.Subsection) else "")
        out.append(f"[{src}] {title}")
    return out


# --------------------------------------------- tz normalization + sanity ----

def detect_et_offset(tfs: dict) -> int:
    """Old exports (tz bug) stamp bars at trueET-7h. Detect from the modal
    time-of-day of 1d bars: correct exports stamp daily bars at 09:30 ET."""
    if "1d" not in tfs:
        return 0
    d = tfs["1d"]
    tod = d.Datetime.dt.hour * 60 + d.Datetime.dt.minute
    modal = tod.mode().iloc[0]
    offset_min = (9 * 60 + 30) - modal
    # snap to whole hours ±30m; anything weird -> assume already correct
    hours = round(offset_min / 60)
    return hours if abs(offset_min - hours * 60) <= 31 and hours != 0 else 0


def normalize_et(tfs: dict) -> tuple[dict, int]:
    off = detect_et_offset(tfs)
    if off:
        for tf in tfs:
            tfs[tf]["Datetime"] = tfs[tf]["Datetime"] + pd.Timedelta(hours=off)
    return tfs, off


def infer_asof(tfs: dict, meta: dict) -> pd.Timestamp:
    """as-of in ET. Prefer export header; fall back to newest bar end."""
    if meta.get("data_asof_et"):
        try:
            return pd.Timestamp(meta["data_asof_et"]).tz_localize(None)
        except Exception:
            pass
    ends = [tfs[tf].Datetime.max() + pd.Timedelta(hours=BAR_HOURS[tf]) for tf in tfs]
    return max(ends)


def tf_asofs(tfs: dict, metas: dict) -> dict:
    """{tf: as-of Timestamp} — each timeframe judged by ITS OWN file header.

    Falls back to that timeframe's newest bar end when the header is missing, so a
    header-less export is treated as "fetched exactly when its last bar closed"
    rather than inheriting somebody else's clock.
    """
    out = {}
    for tf, d in tfs.items():
        stamp = (metas.get(tf) or {}).get("data_asof_et")
        if stamp:
            try:
                out[tf] = pd.Timestamp(stamp).tz_localize(None)
                continue
            except Exception:
                pass
        out[tf] = d.Datetime.max() + pd.Timedelta(hours=BAR_HOURS[tf])
    return out


def equity_only(d: pd.DataFrame) -> pd.DataFrame:
    """Drop the 24-hour macro series (crypto / FX / rates / commodities).

    Those series keep printing bars on weekends and US market holidays. Mixing them
    into a market-wide "newest bar / newest closed bar" makes the clock claim a
    daily close exists on a day the US stock market never opened — which is exactly
    what happened on Labor Day (Mon 7 Sep 2026): only BTCUSDT/DXY/US10/US10Y/
    USDTHB/WTI/XAUUSD had bars, yet bar_clock reported `1d last_closed_bar =
    2026-09-07` and `can_judge_daily_close = True` against a Monday close that never
    happened. Every equity verdict must be measured against the equity calendar.
    """
    if "Symbol" not in getattr(d, "columns", []):
        return d
    eq = d[~d.Symbol.isin(NONEQ_KNOWN)]
    return eq if len(eq) else d


def equity_session_days(d1: pd.DataFrame | None, min_symbols: int = 20) -> set:
    """Dates on which the US equity market actually traded, read from the data itself.

    Self-updating: no hardcoded holiday table to go stale. A date counts as a real
    session only when at least `min_symbols` distinct equities printed a bar that
    day, so a partial/broken export cannot be mistaken for a holiday (or a holiday
    for a session, since the 24h series are excluded first).
    """
    if d1 is None or not len(d1) or "Symbol" not in getattr(d1, "columns", []):
        return set()
    eq = equity_only(d1)
    per_day = eq.groupby(eq.Datetime.dt.normalize()).Symbol.nunique()
    return set(per_day[per_day >= min_symbols].index)


def _last_daily_close_due(now: pd.Timestamp, session_days: set | None = None) -> pd.Timestamp:
    """The most recent RTH close (16:00 ET) that should already exist at `now`.

    When `session_days` is supplied (the real equity trading calendar derived from
    the export), walk back to the most recent day the market actually opened — so
    market holidays are skipped, not just weekends.
    """
    d = now.normalize() + pd.Timedelta(hours=16)
    if now < d:
        d -= pd.Timedelta(days=1)
    if session_days:
        for _ in range(15):               # 15 days back covers any US holiday cluster
            if d.normalize() in session_days:
                return d
            d -= pd.Timedelta(days=1)
    while d.weekday() >= 5:               # Sat/Sun -> walk back to Friday
        d -= pd.Timedelta(days=1)
    return d


def bar_clock(tfs: dict, asofs: dict, metas: dict) -> dict:
    """Per-timeframe freshness record — the answer to "is this bar new or is it the
    same one as last round?".

    For each tf: when the file was fetched, its newest bar, its newest CLOSED bar,
    how stale that is against the fetch time, and whether the export is fresh enough
    to carry the latest closed daily bar. `can_judge_daily_close` is the machine
    form of skill rule (v): if the 1d export was pulled before 16:00 ET, no
    "held the close / stop hit on the close" verdict may be made from it.
    """
    clock, newest_asof = {}, (max(asofs.values()) if asofs else None)
    sess_days = equity_session_days(tfs.get("1d"))
    for tf, d in tfs.items():
        asof = asofs[tf]
        # --- equity calendar only: the 24h macro series print on holidays/weekends
        # and would otherwise fabricate a "close" on a day the market never opened.
        d_eq = equity_only(d)
        d_non = d[d.Symbol.isin(NONEQ_KNOWN)] if "Symbol" in getattr(d, "columns", []) else d.iloc[0:0]
        last = d_eq.Datetime.max()
        closed = d_eq[d_eq.Is_Closed_Bar != False] if "Is_Closed_Bar" in d_eq else d_eq  # noqa: E712
        last_closed = closed.Datetime.max() if len(closed) else None
        # "is the newest bar still forming?" — trust the exporter's Is_Closed_Bar flag
        # when present. The wall-clock rule (bar_start + BAR_HOURS > as-of) only works
        # intraday: a 1d bar is stamped at the 09:30 OPEN but closes at 16:00, so +24h
        # would call every finished daily bar "forming".
        if last_closed is not None or "Is_Closed_Bar" in d:
            forming = last_closed is None or last_closed < last
        else:
            forming = bool(last + pd.Timedelta(hours=BAR_HOURS[tf]) > asof)
        rec = {
            "asof_et": str(asof),
            "market_state": (metas.get(tf) or {}).get("market_state"),
            "last_bar": str(last),
            "last_closed_bar": str(last_closed) if last_closed is not None else None,
            "forming_bar_present": bool(forming),
            "bar_age_min": int(round((asof - last).total_seconds() / 60)),
            "closed_bar_age_min": (
                int(round((asof - last_closed).total_seconds() / 60)) if last_closed is not None else None),
            "behind_newest_leg_min": (
                int(round((newest_asof - asof).total_seconds() / 60)) if newest_asof is not None else 0),
        }
        # keep the 24h reading visible instead of silently dropping it
        if len(d_non):
            rec["noneq_last_bar"] = str(d_non.Datetime.max())
            rec["scope"] = "US equities only (24h macro series reported separately)"
        if tf in ("1h", "4h"):
            # intraday only: everything up to here is guaranteed complete at this as-of
            rec["complete_through"] = str(asof - pd.Timedelta(hours=BAR_HOURS[tf]))
        if tf == "1d":
            need = _last_daily_close_due(asof, sess_days)
            have = last_closed if last_closed is not None else last
            rec["daily_close_due"] = str(need)
            rec["has_latest_daily_close"] = bool(have is not None and have.normalize() >= need.normalize())
            rec["can_judge_daily_close"] = bool(asof >= need and rec["has_latest_daily_close"])
            # weekdays with no equity session between the last close and now = holidays
            hol = []
            if sess_days:
                probe = need.normalize() + pd.Timedelta(days=1)
                while probe <= asof.normalize():
                    if probe.weekday() < 5 and probe not in sess_days and probe < asof.normalize():
                        hol.append(str(probe.date()))
                    probe += pd.Timedelta(days=1)
            rec["market_holidays_skipped"] = hol
        clock[tf] = rec
    return clock


def clock_notes(clock: dict) -> list[str]:
    """Loud sanity lines about export freshness — these belong next to the CMF and
    split checks because a stale leg corrupts conclusions exactly as badly."""
    notes = []
    spread = [(tf, r["behind_newest_leg_min"]) for tf, r in clock.items()]
    lag = [f"{tf} -{m}m" for tf, m in sorted(spread, key=lambda x: -x[1]) if m > 0]
    if lag:
        notes.append("TF fetch times differ (z-service fetches a TF only when its bar "
                     f"closed): {', '.join(lag)} behind the newest leg -> judge every "
                     "bar against ITS OWN timeframe as-of, never a global one")
    d1 = clock.get("1d")
    if d1 is not None:
        hol = d1.get("market_holidays_skipped") or []
        if hol:
            notes.append(f"US MARKET HOLIDAY(S) since the last close: {', '.join(hol)} -> "
                         "no equity bars exist on those days. Any 24h series (gold/oil/"
                         "crypto/FX) that DOES show a bar there is not an equity session "
                         f"-> the newest equity daily close is {d1['daily_close_due']}, "
                         "and '%today' spans the whole gap, not one session")
        if not d1.get("can_judge_daily_close"):
            notes.append(f"RULE (v) BLOCK: 1d export as-of {d1['asof_et']} is before the "
                         f"{d1['daily_close_due']} close -> NO 'held the close' / "
                         "'stop hit on the close' verdict may be made from this snapshot")
        else:
            notes.append(f"rule (v) OK: 1d carries the {d1['daily_close_due']} close "
                         "-> daily-close verdicts are valid")
    forming = [tf for tf, r in clock.items() if r["forming_bar_present"]]
    if forming:
        notes.append(f"forming (incomplete) bars present and excluded from indicators: {forming}")
    return notes


def price_source(tfs_raw: dict, asofs: dict, s: str) -> dict | None:
    """Where `px_now` for one symbol actually comes from, and how trustworthy it is.

    Walks 1h -> 4h -> 1d and returns the first timeframe holding a bar for `s`,
    together with that bar's stamp, whether it is still forming, and how old it is
    against that file's own as-of. Reports must print this label — a forming
    pre-market 1h print must never be shown as if it were the daily close.
    """
    for tf in ("1h", "4h", "1d"):
        d = tfs_raw.get(tf)
        if d is None:
            continue
        g = d[d.Symbol == s]
        if not len(g):
            continue
        row = g.iloc[-1]
        t = row.Datetime
        asof = asofs.get(tf, t + pd.Timedelta(hours=BAR_HOURS[tf]))
        flag = None if "Is_Closed_Bar" not in g else bool(row.Is_Closed_Bar)
        return {
            "px": float(row.Close),
            "src_tf": tf,
            "bar_time": str(t),
            # exporter flag wins; the wall-clock test is only the fallback
            "forming": (not flag) if flag is not None
                       else bool(t + pd.Timedelta(hours=BAR_HOURS[tf]) > asof),
            "closed_flag": flag,
            "age_min": int(round((asof - t).total_seconds() / 60)),
            "session": (str(row.Session) if "Session" in g else None),
        }
    return None


def classify_universe(tfs: dict) -> dict:
    syms = set()
    for d in tfs.values():
        syms |= set(d.Symbol.unique())
    noneq = {s for s in syms if s in NONEQ_KNOWN}
    # zero-volume series are index-like even if not in the known list
    if "1d" in tfs:
        vol = tfs["1d"].groupby("Symbol").Volume.sum()
        noneq |= set(vol[vol <= 0].index)
    etfs = {s for s in syms - noneq if s in ETF_KNOWN} - {"SPY"}
    stocks = syms - noneq - etfs - {"SPY"}
    return {"all": sorted(syms), "noneq": sorted(noneq), "etfs": sorted(etfs),
            "stocks": sorted(stocks)}


def sanity_checks(tfs: dict, meta: dict, off: int) -> list[str]:
    notes = []
    if off:
        notes.append(f"tz-shift detected: stamps were ET-{off}h (old exporter bug) -> corrected +{off}h")
    else:
        notes.append("timestamps already ET-correct (fixed exporter)")
    for tf, d in tfs.items():
        bad = d[(d.CMF > 1) | (d.CMF < -1)]
        if len(bad):
            notes.append(f"{tf}: CMF out of [-1,1] on {bad.Symbol.nunique()} symbols -> recompute required")
    if "1d" in tfs:
        d1 = tfs["1d"]
        # oscillators/rate indices swing through zero (TICK ±1000, yields) — ratio
        # jumps there are normal, not splits; only flag real price series.
        NO_SPLIT = {"TICK", "US10Y", "US10", "VIX", "VIX9D", "VIX3M", "MOVE"}
        jump_syms = []
        for sym, g in d1.groupby("Symbol"):
            if sym in NO_SPLIT:
                continue
            r = (g.Close / g.Close.shift(1)).dropna()
            jumps = r[(r > 1.8) | (r < 0.55)]
            if len(jumps):
                i = jumps.index[-1]
                jump_syms.append(f"{sym} {g.loc[i, 'Datetime'].date()} x{r[i]:.2f}")
        if jump_syms:
            notes.append("price jumps (check split vs data error vs real vol event): "
                         + "; ".join(jump_syms[:8]) + ("..." if len(jump_syms) > 8 else ""))
    sizes = {tf: d.Symbol.nunique() for tf, d in tfs.items()}
    if len(set(sizes.values())) > 1:
        notes.append(f"symbol counts differ across TFs: {sizes}")
    missing = [tf for tf in TFS if tf not in tfs]
    if missing:
        notes.append(f"missing timeframes: {missing} (confluence depth limited)")
    return notes


# กฎ (ai) แท่งไม่ครบ/ประวัติสั้น (22 ต.ค. 2026): z-service เก็บ 80 แท่ง/ตัว คำนวณจากที่ดึงได้ ≤300 แท่ง —
# หุ้นเพิ่งเข้าตลาด/แยกบริษัทมีแท่งทั้งหมดน้อยกว่า 80 ⇒ EMA/RSI/ATR เริ่มนับจากแท่งแรก (EMA_200 ≈ ราคา IPO)
# indicator ที่คาบยาวกว่าจำนวนแท่งที่มีอยู่จริง = อ่านไม่ได้ (TradingView เองยังไม่แสดงค่า)
HIST_NEEDS = (("EMA_200", 200), ("EMA_100", 100), ("EMA_50", 50), ("RSI50", 50),
              ("CMF50", 50), ("cmf20", 20), ("ATR14", 14))


def short_history(tfs: dict, metas: dict | None = None) -> dict:
    """{tf: {"expected": n, "short": {sym: closed_bars}}} — symbols with fewer rows than
    the timeframe's normal count. The exporter header `# bars_expected` wins when present,
    else the most common row count (ties -> larger). Bars counted = closed bars only."""
    out = {}
    for tf, d in tfs.items():
        rows = d.groupby("Symbol").size()
        if rows.empty:
            continue
        vc = rows.value_counts()
        norm = int(max(vc.index, key=lambda c: (vc[c], c)))
        try:
            norm = int((metas or {}).get(tf, {}).get("bars_expected"))
        except (TypeError, ValueError):
            pass
        closed = d[d.Is_Closed_Bar != False] if "Is_Closed_Bar" in d else d  # noqa: E712
        nc = closed.groupby("Symbol").size()
        out[tf] = {"expected": norm,
                   "short": {s: int(nc.get(s, 0)) for s, n in rows.items() if n < norm}}
    return out


def hist_unreliable(bars: int) -> list[str]:
    """Indicators whose period is longer than the bars that exist (not a real read)."""
    return [k for k, need in HIST_NEEDS if bars < need]


def hist_notes(hist: dict) -> list[str]:
    notes = []
    for tf in [t for t in TFS if t in hist]:
        sh = hist[tf]["short"]
        if sh:
            lst = ", ".join(f"{s}={n}" for s, n in sorted(sh.items(), key=lambda x: x[1]))
            notes.append(f"short-history (ประวัติสั้น · กฎ ai) {tf}: {len(sh)} ตัวมีแท่งปิดน้อยกว่าปกติ "
                         f"{hist[tf]['expected']} — {lst} · indicator ที่คาบยาวกว่าจำนวนแท่ง = อ่านไม่ได้ "
                         f"(EMA_200 ≈ ราคา IPO) ⇒ ดูตาราง ⚠️ ประวัติสั้น")
    return notes


# ------------------------------------------------------------- indicators ----

def cmf_series(df: pd.DataFrame, n: int = 20) -> np.ndarray:
    hl = df.High - df.Low
    mfm = np.where(hl <= 0, 0, ((df.Close - df.Low) - (df.High - df.Close)) / hl)
    mfv = mfm * df.Volume
    return (pd.Series(mfv, index=df.index).rolling(n).sum()
            / df.Volume.rolling(n).sum()).values


def prep_frames(tfs: dict, uni: dict, asof) -> dict:
    """Per TF: drop forming bars, tag usable (RTH for equities) bars, and
    recompute flow columns per symbol. Returns {tf: {sym: df}}.

    `asof` is a {tf: Timestamp} map — each timeframe's forming-bar cut uses ITS OWN
    fetch time. Passing one global timestamp is still accepted for back-compat, but
    it is wrong whenever the exports were fetched at different times: the oldest
    leg's clock would silently delete genuinely closed bars from the newest leg.
    """
    out = {}
    per_tf = isinstance(asof, dict)
    for tf, d in tfs.items():
        d = d.copy()
        cut = asof[tf] if per_tf else asof
        if tf in ("1h", "4h"):
            # forming-bar cut by wall clock (intraday stamps are reliable)
            d = d[d.Datetime + pd.Timedelta(hours=BAR_HOURS[tf]) <= cut]
        if "Is_Closed_Bar" in d:
            d = d[d.Is_Closed_Bar != False]  # noqa: E712
        if tf == "1d" and cut is not None:
            # ซีรีส์ 24 ชม. (DXY ทอง น้ำมัน BTC 10Y USDTHB) — แท่งวันเริ่มเย็นวันก่อน (17:00–20:00 ET) และจบเวลาเดียวกัน
            # วันถัดไป แต่ exporter ติด Is_Closed_Bar=True ให้แท่งที่ยังวิ่ง ⇒ indicator และ chg% เทียบกับแท่งที่ยังไม่จบ
            # (15 ต.ค. 2026: DXY +0.11% ทั้งที่จริง −0.43%) · ตัดแท่ง non-equity ที่เวลาจบ > เวลาดึงไฟล์ 1d
            # แท่งที่ประทับเวลาเย็น (≥16:00) จบ +24 ชม. · แท่งประทับเช้า (VIX 03:15 / 09:30) จบ 16:15 วันเดียวกัน
            ne = d.Symbol.isin(uni["noneq"])
            ev = d.Datetime.dt.hour >= 16
            end = (d.Datetime + pd.Timedelta(hours=24)).where(ev, d.Datetime.dt.normalize() + pd.Timedelta(hours=16, minutes=15))
            d = d[~(ne & (end > cut))]
        hr = d.Datetime.dt.hour + d.Datetime.dt.minute / 60
        if tf == "1h":
            eq_rth = (hr >= 9.0) & (hr < 16.0)   # 09:00 straddle bar carries the open
            use = eq_rth | d.Symbol.isin(uni["noneq"])
        elif tf == "4h":
            eq_rth = (hr >= 8.0) & (hr < 16.0)   # 4H grid: 08:30 + 12:30 cover RTH
            use = eq_rth | d.Symbol.isin(uni["noneq"])
        else:
            use = pd.Series(True, index=d.index)
        d = d[use]
        per = {}
        for s, g in d.groupby("Symbol"):
            g = g.sort_values("Datetime").reset_index(drop=True)
            if g.Volume.fillna(0).sum() > 0:
                # file CMF(50) is the system CMF (trusted when in bounds);
                # cmf20 is the fast recomputed flow read
                bad = (g.CMF.abs() > 1).any() if "CMF" in g else True
                if bad:
                    g["CMF"] = cmf_series(g, 50)
                g["cmf20"] = cmf_series(g, 20)
                obv = (np.sign(g.Close.diff().fillna(0)) * g.Volume).cumsum()
                slope = obv.diff()
                sd = slope.rolling(50, min_periods=20).std()
                g["obv_slope"] = slope
                g["obv_norm"] = (slope / sd).clip(-1, 1)
                # formula-file spec: RVOL = V/SMA(V,20). Time-of-day RVOL only
                # for intraday TFs (exporter Rvol_Tod); 1D/1W always raw SMA20
                # so holiday scaling is applied exactly once (by ipi_last).
                if tf in ("1h", "4h") and "Rvol_Tod" in g and g.Rvol_Tod.notna().any():
                    g["rvol"] = g.Rvol_Tod
                else:
                    g["rvol"] = g.Volume / g.Volume.rolling(20, min_periods=10).mean()
            else:
                for c in ("cmf20", "obv_slope", "obv_norm", "rvol"):
                    g[c] = np.nan
                g["CMF"] = np.nan
            per[s] = g
        out[tf] = per
    return out


def week_scale(tfs_raw: dict, week_start: pd.Timestamp, uni: dict) -> float:
    """5/(US trading days in that week) from the 1d file — holiday-week RVOL fix.
    Count only equity symbols: crypto/fx trade weekends and would mask holidays."""
    if "1d" not in tfs_raw:
        return 1.0
    d = tfs_raw["1d"]
    eq = d[~d.Symbol.isin(uni["noneq"])]
    ref = eq[eq.Symbol == "SPY"] if (eq.Symbol == "SPY").any() else eq
    days = ref[(ref.Datetime >= week_start) & (ref.Datetime < week_start + pd.Timedelta(days=7))]
    n = days.groupby(days.Datetime.dt.date).ngroups
    return 5.0 / n if 0 < n < 5 else 1.0


def ipi_last(g: pd.DataFrame, rvol_scale: float = 1.0) -> dict:
    """IPI of the last usable bar: CMF*100 + RVOL_dev*0.5 + obv_norm*50."""
    if g is None or not len(g) or pd.isna(g.CMF.iloc[-1]):
        # แท่งไม่พอคำนวณ CMF (หุ้นประวัติสั้น/IPO ใหม่ · 22 ต.ค. 2026): คืนช่องครบเป็น None — เดิมไม่มีช่อง cmf ทำให้ uipt_stage ล้ม KeyError
        return {"ipi": None, "status": "no-vol", "cmf": None, "cmf20": None, "rvol": None}
    r = g.iloc[-1]
    rvol = (r.rvol if pd.notna(r.rvol) else 1.0) * rvol_scale
    ipi = r.CMF * 100 + (rvol - 1) * 100 * 0.5 + (r.obv_norm if pd.notna(r.obv_norm) else 0) * 50
    if rvol < 0.3:
        status = "N/A (low vol)"
    elif ipi > 50:
        status = "Accum"
    elif ipi < -20:
        status = "Dist"
    else:
        status = "Neut"
    return {"ipi": round(float(ipi), 1), "status": status, "cmf": round(float(r.CMF), 3),
            "cmf20": round(float(r.cmf20), 3) if pd.notna(r.cmf20) else None,
            "rvol": round(float(rvol), 2)}


# ------------------------------------------------------------ assessments ----

def gc(row) -> bool:
    try:
        return bool(row.Close > row.EMA_50 and row.EMA_50 > row.EMA_200)
    except Exception:
        return False


def last_row(frames, tf, s):
    g = frames.get(tf, {}).get(s)
    return (g, g.iloc[-1]) if g is not None and len(g) else (None, None)


def symbol_view(frames, s, wscale) -> dict:
    """Everything the screen needs for one symbol, one dict."""
    v = {"sym": s}
    for tf in TFS:
        g, r = last_row(frames, tf, s)
        if r is None:
            continue
        scale = wscale if tf == "1w" else 1.0
        ip = ipi_last(g, scale)
        v[tf] = {"close": round(float(r.Close), 2), "gc": gc(r),
                 "c_gt_e20": bool(r.Close > r.EMA_20), "c_gt_e50": bool(r.Close > r.EMA_50),
                 "c_gt_e200": bool(r.Close > r.EMA_200),
                 "rsi": round(float(r.RSI), 0) if pd.notna(r.RSI) else None,
                 "e20": round(float(r.EMA_20), 2), "e50": round(float(r.EMA_50), 2),
                 "e200": round(float(r.EMA_200), 2),
                 "vwap": round(float(r.VWAP), 2) if pd.notna(r.VWAP) else None,
                 "atr": round(float(r.Atr14), 2) if "Atr14" in r and pd.notna(r.Atr14) else None,
                 "dvol_m": round(float(r.Dollar_Volume) / 1e6, 0) if "Dollar_Volume" in r and pd.notna(r.Dollar_Volume) else None,
                 **ip}
    return v


def uipt_stage_short(v: dict, frames) -> dict:
    """UIPT-S staging for 1H+4H only sets (no 1D/1W). 4H is the structure gate
    (Golden Cross + flow) in place of the weekly macro filter, 1H is the trigger.
    Explicitly labelled short-only so it's never mistaken for the full 4-phase
    UIPT that requires the weekly Kill Switch."""
    h4, h1 = v.get("4h"), v.get("1h")
    if not h4:
        return {"stage": "NO-DATA", "mode": "short"}
    kill4 = h4["status"] == "Dist"
    gc4 = h4["gc"]
    struct = gc4 and (h4.get("cmf") or 0) > 0 and not kill4          # 4H structure ok
    near_ema = h4["close"] <= h4["e20"] * 1.02 or h4["close"] <= h4["e50"] * 1.02
    rsi_ok = (h4["rsi"] and 40 <= h4["rsi"] <= 68)
    setup = struct and near_ema and h4["c_gt_e200"] and rsi_ok
    p4 = False
    if h1:
        g = frames.get("1h", {}).get(v["sym"])
        obv_up = g is not None and len(g) >= 2 and (g.obv_slope.iloc[-1] or 0) > 0
        p4 = (h1["vwap"] and h1["close"] > h1["vwap"] and (h1["rvol"] or 0) > 1.5
              and obv_up and h1["status"] == "Accum")
    if kill4:
        stage = "KILL-S"
    elif struct and setup and p4:
        stage = "TRIGGER-S"
    elif struct and setup:
        stage = "SETUP-S"
    elif struct:
        stage = "WATCH-S"
    else:
        stage = "FAIL-S"
    ext200 = round((h4["close"] / h4["e200"] - 1) * 100, 0) if h4["e200"] else None
    return {"stage": stage, "mode": "short", "kill": kill4, "gc4": gc4,
            "struct": struct, "setup": setup, "p4": p4, "trap6": False,
            "ext200_pct": ext200}


def uipt_stage(v: dict, frames, mode: str = "full") -> dict:
    """4-phase UIPT staging + kill switch + rule-6 trap check for one symbol.
    mode='short' (whole dataset lacks 1D/1W) -> UIPT-S. In full mode a single
    symbol missing its 1D/1W bars is NO-DATA, NOT silently downgraded to -S
    (that would mix short stages into a medium screen)."""
    d1, w1, h4, h1 = v.get("1d"), v.get("1w"), v.get("4h"), v.get("1h")
    if mode == "short":
        return uipt_stage_short(v, frames)
    if not d1 or not w1:
        return {"stage": "NO-DATA", "reason": "missing 1D/1W bars for this symbol"}
    kill = d1["status"] == "Dist" or w1["status"] == "Dist"
    p2 = d1["gc"] and w1["gc"] and (w1["cmf"] or 0) > 0 and w1["status"] == "Accum" and not kill
    p2_loose = d1["gc"] and w1["gc"] and (w1["cmf"] or 0) > 0 and not kill
    near_ema = d1["close"] <= d1["e20"] * 1.02 or d1["close"] <= d1["e50"] * 1.02
    rsi_ok = (d1["rsi"] and 40 <= d1["rsi"] <= 60) or (h4 and h4["rsi"] and 40 <= h4["rsi"] <= 60)
    p3 = near_ema and d1["c_gt_e200"] and rsi_ok and (d1["cmf"] or 0) > 0
    p4 = False
    if h1:
        g = frames.get("1h", {}).get(v["sym"])
        obv_up = g is not None and len(g) >= 2 and (g.obv_slope.iloc[-1] or 0) > 0
        p4 = (h1["vwap"] and h1["close"] > h1["vwap"] and (h1["rvol"] or 0) > 1.5
              and obv_up and h1["status"] == "Accum")
    if kill:
        stage = "KILL"
    elif p2 and p3 and p4:
        stage = "TRIGGER"
    elif p2 and p3:
        stage = "SETUP"
    elif p2:
        stage = "MACRO-WATCH"
    elif p2_loose and p3:
        stage = "SETUP(loose)"
    elif p2_loose:
        stage = "WATCH(loose)"
    else:
        stage = "FAIL"
    # rule-6 trap: latest Dist preceded by Accum w/ rvol>1.2 and CMF still > 0
    trap = False
    g = frames.get("1h", {}).get(v["sym"])
    if g is not None and len(g) >= 10 and h1 and h1["status"] == "Dist" and (h1["cmf"] or 0) > 0:
        prior = g.iloc[-6:-1]
        pri_ipi = [ipi_last(g.iloc[:i + 1]) for i in range(len(g) - 6, len(g) - 1)]
        trap = any(p["status"] == "Accum" and (prior.rvol.iloc[j] or 0) > 1.2
                   for j, p in enumerate(pri_ipi))
    ext200 = round((d1["close"] / d1["e200"] - 1) * 100, 0) if d1["e200"] else None
    return {"stage": stage, "kill": kill, "p2": p2, "p2_loose": p2_loose, "p3": p3,
            "p4": p4, "trap6": trap, "ext200_pct": ext200}


def rs_stock(frames, s, spy=None, days: int = 60) -> float | None:
    """Per-stock relative strength vs SPY over `days` daily bars (%). Used only by
    the -ez DIP gate; the default UIPT stage never touches it."""
    g = frames.get("1d", {}).get(s)
    spy = spy if spy is not None else frames.get("1d", {}).get("SPY")
    if g is None or spy is None or len(g) <= days or len(spy) <= days:
        return None
    return round(((g.Close.iloc[-1] / g.Close.iloc[-1 - days] - 1)
                  - (spy.Close.iloc[-1] / spy.Close.iloc[-1 - days] - 1)) * 100, 1)


def uipt_stage_ez(v: dict, frames, spy=None) -> dict:
    """-ez staging — an OPT-IN, looser SIBLING of uipt_stage(). It exists to catch
    the medium-horizon (2–6mo) setups the strict default kills, WITHOUT touching
    the default logic. It relaxes ONLY three stock-level gates and leaves every
    market-context gate (news×flow, ETF/indices/sector regime, ext, multi-TF) to
    the caller exactly as before:

      1) Kill Switch split — 1W Dist = HARD-KILL (unchanged). 1D Dist alone is a
         SOFT-KILL: it is FORGIVEN (tagged DIP) only when 1W is still Accum AND
         RS60 > 0 (a real leader on a daily dip). Otherwise it still KILLs.
      2) EARLY-REVERSAL track — a name with 1D Golden Cross but 1W EMA50 still
         BELOW EMA200 (weekly GC not yet formed), 1W CMF > 0, and RS60 > 0 =
         a fresh turn caught *before* the weekly cross (stage REVERSAL).
      3) RSI band widened 40–60 -> 40–68 so momentum leaders aren't kicked out.

    Returns the same shape as uipt_stage plus {"ez": True, "ez_reason": ...}.
    Stages are suffixed nothing new except DIP / REVERSAL so they read distinctly
    from the strict stages and are never mistaken for real UIPT passes."""
    d1, w1, h4, h1 = v.get("1d"), v.get("1w"), v.get("4h"), v.get("1h")
    if not d1 or not w1:
        return {"stage": "NO-DATA", "ez": True, "reason": "missing 1D/1W"}
    rs60 = rs_stock(frames, v["sym"], spy, 60)
    w_dist = w1["status"] == "Dist"
    d_dist = d1["status"] == "Dist"
    w_accum = w1["status"] == "Accum"

    # ---- Kill Switch (split) ----
    hard_kill = w_dist                                   # 1W Dist = always dead
    dip_forgiven = d_dist and (not w_dist) and w_accum and (rs60 or -1) > 0
    kill = hard_kill or (d_dist and not dip_forgiven)    # 1D Dist kills unless forgiven

    # ---- structure gates (widened RSI) ----
    near_ema = d1["close"] <= d1["e20"] * 1.02 or d1["close"] <= d1["e50"] * 1.02
    rsi_ok = (d1["rsi"] and 40 <= d1["rsi"] <= 68) or (h4 and h4["rsi"] and 40 <= h4["rsi"] <= 68)
    p3 = near_ema and d1["c_gt_e200"] and rsi_ok and (d1["cmf"] or 0) > 0

    p2 = d1["gc"] and w1["gc"] and (w1["cmf"] or 0) > 0 and w_accum and not kill
    p2_loose = d1["gc"] and w1["gc"] and (w1["cmf"] or 0) > 0 and not kill

    # ---- EARLY-REVERSAL: 1D GC formed, weekly GC NOT yet, weekly flow turning ----
    # ext cap: a "reversal" 80% above EMA200 isn't early — it already ran. The ext
    # gate is NOT relaxed in -ez (only the kill/GC/RSI stock gates are).
    d_ext = round((d1["close"] / d1["e200"] - 1) * 100, 0) if d1["e200"] else None
    not_extended = d_ext is not None and d_ext <= 40
    w_gc = w1["gc"]
    reversal = (not w_gc) and d1["gc"] and (w1["cmf"] or 0) > 0 and (rs60 or -1) > 0 \
        and d1["c_gt_e200"] and not_extended and not hard_kill

    p4 = False
    if h1:
        g = frames.get("1h", {}).get(v["sym"])
        obv_up = g is not None and len(g) >= 2 and (g.obv_slope.iloc[-1] or 0) > 0
        p4 = (h1["vwap"] and h1["close"] > h1["vwap"] and (h1["rvol"] or 0) > 1.5
              and obv_up and h1["status"] == "Accum")

    reason = None
    if kill:
        stage = "KILL"
    elif p2 and p3 and p4:
        stage = "TRIGGER"
    elif p2 and p3:
        stage = "SETUP"
    elif p2:
        stage = "MACRO-WATCH"
    elif reversal:
        stage = "REVERSAL"
        reason = f"1D GC + weekly GC pending + RS60 {rs60} + 1W CMF>0 (early turn)"
    elif p2_loose and p3:
        stage = "SETUP(loose)"
    elif p2_loose:
        stage = "WATCH(loose)"
    else:
        stage = "FAIL"
    if dip_forgiven and stage not in ("KILL", "FAIL"):
        reason = (reason + " | " if reason else "") + f"1D DIP forgiven (1W Accum + RS60 {rs60})"
    ext200 = round((d1["close"] / d1["e200"] - 1) * 100, 0) if d1["e200"] else None
    return {"stage": stage, "ez": True, "ez_reason": reason, "kill": kill,
            "hard_kill": hard_kill, "dip_forgiven": dip_forgiven, "reversal": reversal,
            "rs60": rs60, "p2": p2, "p2_loose": p2_loose, "p3": p3, "p4": p4,
            "ext200_pct": ext200}


def coil_view(frames, s) -> dict | None:
    # prefer the daily base; fall back to 4H when 1D is absent (short-only sets)
    dd = frames.get("1d", {}).get(s)
    if dd is None or len(dd) < 25:
        dd = frames.get("4h", {}).get(s)
    hd = frames.get("1h", {}).get(s)
    if dd is None or hd is None or len(dd) < 20:
        return None
    piv = float(dd.High.tail(15).max())
    px = float(hd.Close.iloc[-1])
    atr5 = float((dd.High - dd.Low).tail(5).mean())
    atr20 = float((dd.High - dd.Low).tail(20).mean())
    atr14 = float(dd.Atr14.iloc[-1]) if "Atr14" in dd and pd.notna(dd.Atr14.iloc[-1]) else atr20
    ign = bool(((hd.tail(15).rvol > 1.2) & (hd.tail(15).cmf20 > 0)).any())
    ext_atr = (px - piv) / atr14 if px > piv else 0
    tag = "EXTENDED" if ext_atr > 1.5 else ("NEAR-PIVOT" if piv * 0.98 <= px <= piv * 1.005 else "")
    if not tag and not (atr5 < atr20 and ign):
        return None
    return {"pivot15d": round(piv, 2), "dist_pct": round((px / piv - 1) * 100, 1),
            "contracting": atr5 < atr20, "ignition": ign, "tag": tag or "COILING"}


def levels_view(frames, s) -> dict | None:
    dd = frames.get("1d", {}).get(s)
    base_tf = "1d"
    if dd is None or not len(dd):
        dd = frames.get("4h", {}).get(s)  # short-only: use 4H for structure levels
        base_tf = "4h"
    hd = frames.get("1h", {}).get(s)
    if dd is None or not len(dd):
        return None
    r = dd.iloc[-1]
    out = {"base_tf": base_tf,
           "swing_hi15": round(float(dd.High.tail(15).max()), 2),
           "swing_hi60": round(float(dd.High.tail(60).max()), 2),
           "swing_lo10": round(float(dd.Low.tail(10).min()), 2),
           "e20d": round(float(r.EMA_20), 2), "e50d": round(float(r.EMA_50), 2),
           "e200d": round(float(r.EMA_200), 2),
           "atr14d": round(float(r.Atr14), 2) if "Atr14" in r and pd.notna(r.Atr14) else None}
    if hd is not None and len(hd):
        out["e20_1h"] = round(float(hd.EMA_20.iloc[-1]), 2)
        out["vwap_1h"] = round(float(hd.VWAP.iloc[-1]), 2) if pd.notna(hd.VWAP.iloc[-1]) else None
    return out


# ------------------------------------------------------- regime / sectors ----

def cur_price(tfs_raw: dict, s: str) -> float | None:
    """Unlabelled last print. Prefer `price_source()` — it tells you which timeframe
    the print came from, its bar stamp and whether that bar is still forming; this
    thin form is kept only for callers that genuinely need a bare number."""
    for tf in ("1h", "4h", "1d"):
        if tf in tfs_raw:
            g = tfs_raw[tf][tfs_raw[tf].Symbol == s]
            if len(g):
                return float(g.Close.iloc[-1])
    return None


def regime_view(views: dict, tfs_raw: dict, uni: dict) -> dict:
    out = {"metrics": {}, "breadth": {}, "tripwires": {}}
    # reuse the labelled per-symbol price already resolved in run_screen so the
    # regime table and the symbol tables can never disagree about "now"
    px = {s: (views.get(s, {}).get("px_now") or cur_price(tfs_raw, s)) for s in uni["all"]}
    for s in MACRO_ROW_ORDER:
        if s not in views:
            continue
        v = views[s]
        d1, w1 = v.get("1d"), v.get("1w")
        prev = d1["close"] if d1 else None
        out["metrics"][s] = {
            "px": round(px[s], 2) if px.get(s) else None,
            "chg_pct": round((px[s] / prev - 1) * 100, 2) if px.get(s) and prev else None,
            "gc_d": d1["gc"] if d1 else None, "gc_w": w1["gc"] if w1 else None,
            "rsi_d": d1["rsi"] if d1 else None,
            "cmf_d": d1.get("cmf") if d1 else None, "cmf20_d": d1.get("cmf20") if d1 else None,
            "ipi_d": d1.get("status") if d1 else None, "ipi_w": w1.get("status") if w1 else None,
            "above_e200d": d1["c_gt_e200"] if d1 else None,
        }
    scr = uni["stocks"] + uni["etfs"]
    n = len(scr) or 1
    # breadth base TF: daily if present, else 4H (short-only sets). The "kill"
    # count is only meaningful in full mode (weekly Kill Switch); in short mode
    # we surface how many failed the 4H structure gate instead of a macro kill.
    btf = "1d" if any(views.get(s, {}).get("1d") for s in scr) else "4h"
    gc_ct = sum(1 for s in scr if views.get(s, {}).get(btf, {}).get("gc"))
    cmf_pos = sum(1 for s in scr if (views.get(s, {}).get(btf, {}).get("cmf") or 0) > 0)
    cmf20_pos = sum(1 for s in scr if (views.get(s, {}).get(btf, {}).get("cmf20") or 0) > 0)
    if btf == "1d":
        flagged = [s for s in scr if views.get(s, {}).get("_stage", {}).get("kill")]
        kill_label = "kill"
    else:
        flagged = [s for s in scr if (views.get(s, {}).get("_stage", {}).get("stage") in ("FAIL-S", "KILL-S"))]
        kill_label = "4H-fail"
    out["breadth"] = {"n": n, "base_tf": btf, "gc_d_pct": round(gc_ct / n * 100),
                      "cmf50_pos_pct": round(cmf_pos / n * 100),
                      "cmf20_pos_pct": round(cmf20_pos / n * 100),
                      "kill_count": len(flagged), "kill_label": kill_label,
                      "kill_list": flagged}
    if px.get("US10Y"):
        out["tripwires"]["US10Y->4.55"] = f"{px['US10Y']:.2f} ({(px['US10Y']/TRIPWIRES['US10Y']-1)*100:+.1f}%)"
    if px.get("DXY"):
        out["tripwires"]["DXY->101.8/100.0"] = f"{px['DXY']:.2f} ({(px['DXY']/TRIPWIRES['DXY_BREAKOUT']-1)*100:+.1f}% / {(px['DXY']/TRIPWIRES['DXY_REJECT']-1)*100:+.1f}%)"
    if px.get("WTI"):
        out["tripwires"]["WTI->72"] = f"{px['WTI']:.2f} ({(px['WTI']/TRIPWIRES['WTI']-1)*100:+.1f}%)"
    if px.get("VIX") and px.get("VIX3M"):
        out["tripwires"]["VIX/VIX3M"] = f"{px['VIX']/px['VIX3M']:.2f} ({'backwardation!' if px['VIX']>px['VIX3M'] else 'contango'})"
    if px.get("VIX") and px.get("VIX9D"):
        out["tripwires"]["VIX9D/VIX"] = f"{px['VIX9D']/px['VIX']:.2f}"
    hyg = views.get("HYG", {}).get("1d")
    if hyg:
        out["tripwires"]["HYG_vs_E200D"] = f"{hyg['close']} vs {hyg['e200']} ({'BELOW!' if not hyg['c_gt_e200'] else 'above'})"
    # crude permission suggestion (Claude makes the final call in the report)
    near_trip = any(abs(px.get(k2, 0) / t - 1) < 0.01 for k2, t in
                    [("US10Y", TRIPWIRES["US10Y"]), ("DXY", TRIPWIRES["DXY_BREAKOUT"]), ("WTI", TRIPWIRES["WTI"])]
                    if px.get(k2))
    fired = (px.get("US10Y", 0) > TRIPWIRES["US10Y"] or px.get("WTI", 0) > TRIPWIRES["WTI"]
             or (px.get("VIX", 0) > px.get("VIX3M", 9e9)))
    hyg_below = bool(hyg and not hyg["c_gt_e200"])
    if fired:
        out["permission_hint"] = "RISK-OFF (tripwire fired)"
    elif near_trip or hyg_below:
        reasons = []
        if near_trip:
            reasons.append("within 1% of a tripwire")
        if hyg_below:
            reasons.append("HYG below EMA200D")
        out["permission_hint"] = f"TRANSITION ({' / '.join(reasons)})"
    elif out["breadth"]["cmf50_pos_pct"] < 50:
        out["permission_hint"] = "SELECTIVE (breadth <50%)"
    else:
        out["permission_hint"] = "RISK-ON candidate (verify manually)"
    return out


def sector_map(views: dict, frames: dict, uni: dict) -> list[dict]:
    spy = frames.get("1d", {}).get("SPY")
    rows = []
    for s in uni["etfs"] + (["HYG"] if "HYG" in views and "HYG" not in uni["etfs"] else []):
        v = views.get(s, {})
        row = {"sym": s}
        for tf in TFS:
            row[f"cmf20_{tf}"] = v.get(tf, {}).get("cmf20")
        d1 = v.get("1d", {})
        row.update({"ipi_d": d1.get("status"), "ipi_w": v.get("1w", {}).get("status"),
                    "gc_d": d1.get("gc"), "rsi_d": d1.get("rsi")})
        g = frames.get("1d", {}).get(s)
        if spy is not None and g is not None:
            for days, key in ((20, "rs20"), (60, "rs60")):
                if len(g) > days and len(spy) > days:
                    row[key] = round(((g.Close.iloc[-1] / g.Close.iloc[-1 - days] - 1)
                                      - (spy.Close.iloc[-1] / spy.Close.iloc[-1 - days] - 1)) * 100, 1)
        rows.append(row)
    rows.sort(key=lambda r: r.get("rs20") or -99, reverse=True)
    return rows


# --------------------------------------------------------------- portfolio ----

def _num(s: str) -> float | None:
    """Parse a money/quantity cell: strip $ , spaces. None if not numeric."""
    s = s.replace("*", "").replace(",", "")
    m = re.search(r"[-+]?\d*\.?\d+", s)
    if not m:
        return None
    try:
        return float(m.group(0))
    except ValueError:
        return None


def parse_port(path: str) -> list[dict]:
    """Parse my_port.md into [{sym, shares, cost, book}].

    PRIMARY format (preferred — human-readable + robust): a markdown table with a
    header naming the columns, one row per position, e.g.

        | book  | ticker | shares | avg_cost | name     |
        |-------|--------|--------|----------|----------|
        | main  | SNPS   | 29     | 470.76   | Synopsys |
        | swing | COHU   | 18     | 55.31    | Cohu     |

    Column order is read from the header (aliases below), so you can reorder/rename.
    `book` defaults to 'main' if the column is absent. Non-position lines (gold,
    cash, section titles) are ignored — put them under a "## Cash" heading.

    LEGACY formats still parse (backward-compatible) so an old my_port.md keeps
    working: `SYM (name) | ต้นทุนต่อหุ้น: $X | จำนวนหุ้น: Y`, `SYM N / $cost`,
    and `... SYM N $cost`."""
    if not os.path.exists(path):
        return []
    pos, seen = [], set()

    def add(sym, shares, cost, book):
        # MTS/gold is not a US-listed equity — never let it into portfolio marks
        if sym in ("USD", "THB", "OZ", "MTS", "GOLD", "XAU") or shares is None or cost is None:
            return
        key = (book, sym)
        if key in seen:
            return
        seen.add(key)
        pos.append({"sym": sym, "cost": cost, "shares": shares, "book": book})

    # column aliases for the table header
    ALIAS = {"book": "book", "port": "book", "พอร์ต": "book", "โบรก": "book",
             "บัญชี": "book", "บช.": "book",
             "ticker": "sym", "sym": "sym", "symbol": "sym", "หุ้น": "sym",
             "ตัว": "sym", "ตัวหุ้น": "sym", "ตัวย่อ": "sym",
             "shares": "shares", "qty": "shares", "จำนวน": "shares", "จำนวนหุ้น": "shares",
             "cost": "cost", "avg_cost": "cost", "avgcost": "cost", "ต้นทุน": "cost",
             "ทุน": "cost", "avg cost": "cost", "avg price": "cost",
             "avgprice": "cost", "ทุน/หุ้น": "cost", "ราคาทุน": "cost"}

    def _hdr(c: str) -> str:
        """Header cells carry markdown + parenthetical notes: `**Avg Price**`,
        `หุ้น *(คำนวณย้อน)*`, `%บัญชี (ตามภาพ)`. Strip them before alias lookup."""
        c = re.sub(r"[*_`~]", "", c)
        c = re.sub(r"\(.*?\)", "", c)
        return c.strip().lower()
    # In the locked 15-column ⑬ spec the header reads `| ตัว | หุ้น | ทุน |` where
    # ตัว=ticker and หุ้น=SHARES — but "หุ้น" is also the legacy alias for ticker.
    # When both appear, ตัว wins as the ticker and หุ้น demotes to shares.
    SYM_WINS = ("ticker", "sym", "symbol", "ตัว", "ตัวหุ้น", "ตัวย่อ")
    colmap = None  # header-driven column index -> field
    TICKER = re.compile(r"^[A-Z]{1,6}$")

    cur_book = "main"
    for raw in open(path, encoding="utf-8"):
        line = raw.strip()
        if not line:
            continue
        # per-broker tables carry the broker in their heading, not a column
        if line.startswith("#"):
            h = line.lower()
            if "webull" in h:
                cur_book = "webull"
            elif "dime" in h:
                cur_book = "dime!"
            continue

        # ---- table row? ----
        if "|" in line:
            cells = [c.strip() for c in line.strip("|").split("|")]
            if all(set(c) <= set("-: ") for c in cells):  # separator row
                continue
            low = [_hdr(c) for c in cells]
            # A portfolio document contains many later markdown tables.  Reset the
            # mapping at every recognisable header so rows such as `Webull` in the
            # target/allocation tables cannot inherit the prior position-table
            # columns and become fake holdings (WEBULL/HEDGE/MARKET).
            other_headers = {"ตัวแปร", "ก้อน", "เหตุการณ์", "เรื่อง", "ลำดับ",
                             "หัวข้อ", "เวลา", "ธีม", "ประเภทแถว", "ข้อ",
                             "จอ/แก๊ง", "ประเภท", "สินทรัพย์", "แหล่งเงิน"}
            if any(a in ALIAS for a in low) or any(a in other_headers for a in low):
                colmap = {i: ALIAS[c] for i, c in enumerate(low) if c in ALIAS}
                if any(c in SYM_WINS for c in low):
                    for i, c in enumerate(low):
                        if c == "หุ้น" and c not in SYM_WINS:
                            colmap[i] = "shares"
                continue
            if colmap is not None:  # data row mapped by the latest header
                rec = {}
                for i, c in enumerate(cells):
                    f = colmap.get(i)
                    if f == "sym":
                        # cells carry markdown/emoji decoration: `**MMSI** 🆕`
                        m2 = re.search(r"[A-Z][A-Z.]{0,5}", c.replace("*", "").upper())
                        rec["sym"] = m2.group(0) if m2 else c.upper()
                    elif f in ("shares", "cost"):
                        rec[f] = _num(c)
                    elif f == "book":
                        rec["book"] = c.lower() or "main"
                if rec.get("sym") and TICKER.match(rec["sym"]):
                    add(rec["sym"], rec.get("shares"), rec.get("cost"),
                        rec.get("book", cur_book))
                # A row under a recognised header is never a legacy/headerless
                # position row, even when that table has no ticker column.
                continue
            # headerless pipe table: find ticker + first two numbers
            tick = next((c.upper() for c in cells if TICKER.match(c.upper())
                         and c.upper() not in ("USD", "THB")), None)
            nums = [n for n in (_num(c) for c in cells) if n is not None]
            bk = next((c.lower() for c in cells if c.lower() in ("main", "swing")), cur_book)
            if tick and len(nums) >= 2:
                add(tick, nums[0], nums[1], bk)
                continue

        # ---- legacy line formats (backward-compatible) ----
        m = re.match(r"([A-Z]{1,6})\s*\(.*ต้นทุนต่อหุ้น:\s*\$([\d,.]+).*จำนวนหุ้น:\s*([\d.]+)", line)
        if m:
            add(m.group(1), float(m.group(3).replace(",", "")),
                float(m.group(2).replace(",", "")), "main")
            continue
        m = re.search(r"\b([A-Z]{2,6})\s+(\d+)\s*/\s*\$?([\d,.]+)\s*$", line)
        if m:
            add(m.group(1), float(m.group(2)), float(m.group(3).replace(",", "")), "swing")
            continue
        m = re.search(r"([A-Z]{2,6})\s+(\d+)\s+\$([\d,.]+)", line)
        if m:
            add(m.group(1), float(m.group(2)), float(m.group(3).replace(",", "")), "swing")
    return pos


def portfolio_marks(port: list[dict], tfs_raw: dict, views: dict) -> list[dict]:
    out = []
    for p in port:
        # same labelled price the rest of the screen uses — a mark must never come
        # from a different clock than the stage/levels printed beside it
        v = views.get(p["sym"], {})
        px = v.get("px_now")
        src = v.get("_px_src") or {}
        row = dict(p)
        if px:
            row.update({"px": round(px, 2), "pl_usd": round((px - p["cost"]) * p["shares"]),
                        "pl_pct": round((px / p["cost"] - 1) * 100, 1),
                        "px_src": src.get("src_tf"), "px_bar": src.get("bar_time"),
                        "px_forming": src.get("forming"),
                        "stage": v.get("_stage", {}).get("stage")})
        else:
            row["px"] = None
            row["note"] = "not in export"
        out.append(row)
    return out


# ------------------------------------------------------------------ digest ----

def fmt(x, spec=""):
    return "na" if x is None else format(x, spec)


def build_digest(state: dict) -> str:
    L = []
    A = L.append
    mode = state.get("screen_mode", "full")
    present = "+".join(state.get("tfs_present", []))
    A(f"# Radar digest — as-of {state['asof_et']} ET | fingerprint {state['fingerprint']}")
    A(f"market_state(header)={state['meta'].get('market_state','?')} | files={len(state['files'])} "
      f"(newest mtime {state.get('csv_newest_mtime','?')}) | universe={len(state['universe']['all'])}")
    A(f"**screen_mode: {mode.upper()}** — timeframes present: {present}")
    clock = state.get("bar_clock") or {}
    if clock:
        # the four exports are fetched on different clocks — print all four so no
        # reader ever assumes one as-of covers the whole snapshot
        A("\n## ⏱️ bar clock — each timeframe carries its OWN as-of "
          "(**US EQUITIES ONLY** — 24h macro series shown in the last column)")
        A("|tf|as-of (ET)|newest equity bar|newest CLOSED equity bar|forming?|behind newest leg|24h series newest|")
        A("|--|--|--|--|--|--|--|")
        for tf in [t for t in TFS if t in clock]:
            r = clock[tf]
            A(f"|{tf}|{r['asof_et'][:16]}|{(r['last_bar'] or '')[:16]}|"
              f"{(r['last_closed_bar'] or 'na')[:16]}|{'YES' if r['forming_bar_present'] else 'no'}|"
              f"{r['behind_newest_leg_min']}m|{(r.get('noneq_last_bar') or 'na')[:16]}|")
        d1 = clock.get("1d")
        if d1 is not None:
            hol = d1.get("market_holidays_skipped") or []
            if hol:
                A(f"\n🔴 **US MARKET HOLIDAY — no equity session on {', '.join(hol)}.** "
                  "The 24h column above may show a bar there; that is gold/oil/crypto/FX, "
                  "NOT an equity close. The newest equity daily close is "
                  f"**{str(d1.get('daily_close_due'))[:16]}** ⇒ `%today` spans the whole "
                  "gap (several calendar days), not one session.")
            ok = d1.get("can_judge_daily_close")
            A(f"\n**rule (v): daily-close verdicts {'ALLOWED' if ok else 'BLOCKED'}** — "
              f"1d fetched {d1['asof_et'][:16]}, close due {str(d1.get('daily_close_due'))[:16]}"
              + ("" if ok else " ⇒ do NOT judge 'held the close' or 'stop hit on the close' from this snapshot"))
        A("px_now below = last available print, taken per symbol from the freshest TF "
          "that has a bar; `_px_src` in full.json names the tf, the bar stamp and "
          "whether that bar is still forming.")
    if mode == "short":
        A("> SHORT mode (no 1D/1W): staging is **UIPT-S** — 4H is the structure gate "
          "(GC+flow) in place of the weekly Kill Switch, 1H is the trigger. Stages end in "
          "`-S`. This is NOT the full 4-phase UIPT; do not issue medium/position calls. "
          "Regime metrics that need 1D/1W show `na` — read the intraday flow instead.")
    A("\n## Data health")
    for n in state["sanity"]:
        A(f"- {n}")
    short = [(s, v) for s, v in state["views"].items() if v.get("_hist")]
    if short:
        # กฎ (ai): stage/ext ของตัวเหล่านี้ยังคำนวณตามปกติ (ไม่แก้) แต่ค่าที่พึ่ง indicator คาบยาวกว่าจำนวนแท่งห้ามใช้ตัดสิน
        A("\n## ⚠️ ประวัติสั้น (แท่งไม่ครบ · กฎ ai) — stage ด้านล่างคำนวณตามปกติ แต่ห้ามใช้ช่องที่ระบุตัดสิน")
        A("|sym|แท่งปิด/tf|indicator ที่อ่านไม่ได้|stage|1W gc|ext200(1D)%|ห้ามสรุป|")
        A("|--|--|--|--|--|--|--|")
        short.sort(key=lambda x: min(h["bars"] for h in x[1]["_hist"].values()))
        for s, v in short:
            h = v["_hist"]
            bars = " ".join(f"{tf}:{'~' if h[tf].get('est') else ''}{h[tf]['bars']}" for tf in TFS if tf in h)
            bad = " ".join(f"{tf}:{'/'.join(h[tf]['unreliable']) or '-'}" for tf in TFS if tf in h)
            dont = []
            hw, hd = h.get("1w", {}).get("unreliable", []), h.get("1d", {}).get("unreliable", [])
            if "EMA_200" in hw:
                dont.append("1W GC/stage ระยะยาว (EMA200≈ราคา IPO)")
            if "CMF50" in hw:
                dont.append("1W ไม่มี IPI ⇒ Kill 1W ยิงไม่ได้ ≠ ปลอดภัย")
            if "EMA_200" in hd:
                dont.append("ext200/ใต้-เหนือ EMA200 รายวัน (เทียบราคา IPO)")
            if "CMF50" in hd:
                dont.append("1D CMF/IPI/Kill")
            A(f"|{s}|{bars}|{bad}|{(v.get('_stage') or {}).get('stage')}|{v.get('1w', {}).get('gc')}|"
              f"{fmt((v.get('_stage') or {}).get('ext200_pct'))}|{' · '.join(dont) or '-'}|")
    A("\n## Layer-0 regime")
    A(f"permission_hint: **{state['regime']['permission_hint']}**")
    for k, v in state["regime"]["tripwires"].items():
        A(f"- {k}: {v}")
    b = state["regime"]["breadth"]
    btf = b.get("base_tf", "1d").upper()
    kl = b.get("kill_label", "kill")
    A(f"- breadth ({btf}): GC {b['gc_d_pct']}% | CMF50>0 {b['cmf50_pos_pct']}% | CMF20>0 {b['cmf20_pos_pct']}% | {kl} {b['kill_count']}/{b['n']}: {','.join(b['kill_list'][:40])}{'...' if len(b['kill_list'])>40 else ''}")
    A("\n|macro|px|chg%|GC d/w|RSI|CMF50/20|IPI d/w|")
    A("|--|--|--|--|--|--|--|")
    for s, m in state["regime"]["metrics"].items():
        A(f"|{s}|{fmt(m['px'])}|{fmt(m['chg_pct'])}|{int(bool(m['gc_d']))}/{int(bool(m['gc_w']))}|{fmt(m['rsi_d'])}|{fmt(m['cmf_d'])}/{fmt(m['cmf20_d'])}|{m['ipi_d']}/{m['ipi_w']}|")
    A("\n## Sector flow (sorted by RS20)")
    A("|etf|cmf20 1h/4h/1d/1w|IPI d/w|RS20|RS60|GCd|RSI|")
    A("|--|--|--|--|--|--|--|")
    for r in state["sectors"]:
        c = "/".join(fmt(r.get(f"cmf20_{tf}"), "+.2f") if r.get(f"cmf20_{tf}") is not None else "na" for tf in ["1h", "4h", "1d", "1w"])
        A(f"|{r['sym']}|{c}|{r.get('ipi_d')}/{r.get('ipi_w')}|{fmt(r.get('rs20'))}|{fmt(r.get('rs60'))}|{int(bool(r.get('gc_d')))}|{fmt(r.get('rsi_d'))}|")
    if mode == "short":
        A("\n## UIPT-S staging (stocks + ETFs) — 4H structure gate + 1H trigger")
        A("|sym|stage|px_now|4H close|4H gc|4H cmf/cmf20/IPI/RSI|1H cmf20/IPI/rvol|ext200(4H)%|coil|")
        A("|--|--|--|--|--|--|--|--|--|")
        # rank so actionable names float up: TRIGGER-S > SETUP-S > WATCH-S > rest
        order = {"TRIGGER-S": 0, "SETUP-S": 1, "WATCH-S": 2, "FAIL-S": 3, "KILL-S": 4, "NO-DATA": 5}
        names = state["universe"]["stocks"] + state["universe"]["etfs"]
        names.sort(key=lambda s: order.get((state["views"].get(s, {}).get("_stage") or {}).get("stage"), 9))
        for s in names:
            v = state["views"].get(s)
            if not v:
                continue
            st = v.get("_stage", {})
            h4, h1 = v.get("4h", {}), v.get("1h", {})
            coil = v.get("_coil")
            coil_s = f"{coil['tag']} piv={coil['pivot15d']} ({coil['dist_pct']:+.1f}%)" if coil else ""
            A(f"|{s}|{st.get('stage')}|{fmt(round(v['px_now'], 2) if v.get('px_now') else None)}|"
              f"{fmt(h4.get('close'))}|{'Y' if h4.get('gc') else ''}|"
              f"{fmt(h4.get('cmf'))}/{fmt(h4.get('cmf20'))}/{h4.get('status')}/{fmt(h4.get('rsi'))}|"
              f"{fmt(h1.get('cmf20'))}/{h1.get('status')}/{fmt(h1.get('rvol'))}|"
              f"{fmt(st.get('ext200_pct'))}|{coil_s}|")
    else:
        A("\n## UIPT staging (stocks + ETFs) — px_now = live print, close_d = last closed 1D")
        A("|sym|stage|px_now|close_d|1W cmf/IPI|1D cmf/cmf20/IPI/RSI|1H cmf20/IPI/rvol|ext200%|trap6|coil|")
        A("|--|--|--|--|--|--|--|--|--|--|")
        for s in state["universe"]["stocks"] + state["universe"]["etfs"]:
            v = state["views"].get(s)
            if not v:
                continue
            st = v.get("_stage", {})
            d1, w1, h1 = v.get("1d", {}), v.get("1w", {}), v.get("1h", {})
            coil = v.get("_coil")
            coil_s = f"{coil['tag']} piv={coil['pivot15d']} ({coil['dist_pct']:+.1f}%)" if coil else ""
            A(f"|{s}|{st.get('stage')}|{fmt(round(v['px_now'], 2) if v.get('px_now') else None)}|{fmt(d1.get('close'))}|{fmt(w1.get('cmf'))}/{w1.get('status')}|"
              f"{fmt(d1.get('cmf'))}/{fmt(d1.get('cmf20'))}/{d1.get('status')}/{fmt(d1.get('rsi'))}|"
              f"{fmt(h1.get('cmf20'))}/{h1.get('status')}/{fmt(h1.get('rvol'))}|{fmt(st.get('ext200_pct'))}|"
              f"{'Y' if st.get('trap6') else ''}|{coil_s}|")
    # ---- -ez extra staging (opt-in looser sibling; only names that DIFFER) ----
    ez_rows = []
    for s in state["universe"]["stocks"] + state["universe"]["etfs"]:
        v = state["views"].get(s, {})
        ez = v.get("_stage_ez")
        st = (v.get("_stage") or {}).get("stage")
        if not ez or ez.get("stage") == st:
            continue
        DEAD = {"KILL", "FAIL", "NO-DATA"}
        if ez.get("stage") in DEAD:      # only surface where -ez OPENS an opportunity
            continue
        ez_rows.append((s, st, ez))
    if ez_rows:
        A("\n## -ez extra (opt-in looser screen — names the strict default KILLed/FAILed "
          "but -ez keeps; default stages above are UNCHANGED)")
        A("|sym|default→ez|px_now|RS60|ext200%|1W cmf/IPI|1D cmf20/IPI|why (-ez)|")
        A("|--|--|--|--|--|--|--|--|")
        for s, st, ez in ez_rows:
            v = state["views"][s]
            d1, w1 = v.get("1d", {}), v.get("1w", {})
            A(f"|{s}|{st}→**{ez['stage']}**|{fmt(round(v['px_now'],2) if v.get('px_now') else None)}|"
              f"{fmt(ez.get('rs60'))}|{fmt(ez.get('ext200_pct'))}|"
              f"{fmt(w1.get('cmf'))}/{w1.get('status')}|{fmt(d1.get('cmf20'))}/{d1.get('status')}|"
              f"{ez.get('ez_reason') or ''}|")
        A("> -ez relaxes ONLY 3 stock gates (1D-Dist soft-kill if 1W Accum+RS60>0 · "
          "EARLY-REVERSAL before weekly GC · RSI 40→68). News×flow, ETF/indices/sector "
          "regime, ext, multi-TF are NOT relaxed. Treat -ez names as candidates to "
          "confirm against the regime, never auto-buys.")

    # ---- COILED SPRING (always emitted): cheap-before-it-runs, low-risk, 6–12M ----
    if mode == "full":
        spring = []
        for s in state["universe"]["stocks"] + state["universe"]["etfs"]:
            cs = coiled_spring(state["views"].get(s, {}))
            if cs and cs["risk_score"] <= 6.0:
                spring.append((s, cs))
        spring.sort(key=lambda x: (x[1]["risk_score"], -(x[1]["rs60"] or -99)))
        A("\n## 🌱 COILED SPRING (ถูกก่อนวิ่ง เสี่ยงต่ำสุด · 6–12M) — always-on screen")
        if not spring:
            A("_ไม่มีสปริงผ่านเกณฑ์ตอนนี้._")
        else:
            A("|#|sym|risk↓|ext%|RS60|1W|RSI|coil|upside%|entry_pull|stop|TP1|")
            A("|--|--|--|--|--|--|--|--|--|--|--|--|")
            for i, (s, cs) in enumerate(spring[:15], 1):
                cl = cs["coil_tag"] or (f"ATR{cs['atr_pct']}%" if cs.get("atr_pct") else "-")
                A(f"|{i}|{s}|**{cs['risk_score']}**|{fmt(cs['ext200'])}|{fmt(cs['rs60'])}|"
                  f"{cs['w1']}|{fmt(cs['rsi'])}|{cl}|{fmt(cs['upside_to_swinghi_pct'])}|"
                  f"{fmt(cs['entry_pullback'])}|{fmt(cs['stop'])}|{fmt(cs['tp1'])}|")
            A("> risk↓ ต่ำ=ปลอดภัย. ยังไม่ ext + 1W ไม่ Dist + สะสมเงียบ + จ่อดีด. ทยอยสะสมโซน pullback, ถือ 3–12M.")

    lvl_tf = "4H" if mode == "short" else "1D"
    A(f"\n## Levels (non-KILL, non-FAIL names) — structure EMAs from {lvl_tf}")
    A(f"|sym|px_now|1H e20|1H vwap|{lvl_tf} e20|{lvl_tf} e50|{lvl_tf} e200|ATR14|swingHi15|swingLo10|")
    A("|--|--|--|--|--|--|--|--|--|--|")
    _skip = {"KILL", "FAIL", "KILL-S", "FAIL-S", "NO-DATA", None}
    for s in state["universe"]["stocks"] + state["universe"]["etfs"]:
        v = state["views"].get(s, {})
        if v.get("_stage", {}).get("stage") in _skip:
            continue
        lv = v.get("_levels") or {}
        A(f"|{s}|{fmt(round(v['px_now'], 2) if v.get('px_now') else None)}|{fmt(lv.get('e20_1h'))}|{fmt(lv.get('vwap_1h'))}|"
          f"{fmt(lv.get('e20d'))}|{fmt(lv.get('e50d'))}|{fmt(lv.get('e200d'))}|{fmt(lv.get('atr14d'))}|"
          f"{fmt(lv.get('swing_hi15'))}|{fmt(lv.get('swing_lo10'))}|")
    if state.get("portfolio"):
        A("\n## Portfolio marks")
        A("|sym|book|shares|cost|px|P&L$|P&L%|stage|")
        A("|--|--|--|--|--|--|--|--|")
        for p in state["portfolio"]:
            A(f"|{p['sym']}|{p['book']}|{p['shares']:g}|{p['cost']}|{fmt(p.get('px'))}|"
              f"{fmt(p.get('pl_usd'))}|{fmt(p.get('pl_pct'))}|{p.get('stage') or p.get('note','')}|")
    if state.get("news"):
        A("\n## News (from formula file — tag horizon×flow in the report)")
        for n_ in state["news"][:25]:
            A(f"- {n_}")
    A("\n> Method: IPI recomputed on corrected-ET RTH closed bars (file IPI_Status ignored). "
      "RVOL: 1H/4H = exporter Rvol_Tod; 1D/1W = V/SMA20 per formula spec, latest week holiday-scaled x{:.2f}. "
      "CMF = file CMF(50) [in-bounds]; cmf20 = fast recomputed flow.".format(state.get("wscale", 1.0)))
    return "\n".join(L)


# ----------------------------------------------------------------- history ----

def run_screen(csv_dir: str, port_path: str | None = None) -> dict:
    tfs_raw, meta, files, metas = load_exports(csv_dir)
    if not tfs_raw:
        raise SystemExit(f"no ztrade_export_*.csv found in {csv_dir}")
    tfs_raw, off = normalize_et(tfs_raw)
    asofs = tf_asofs(tfs_raw, metas)        # each TF judged by its own header
    asof = max(asofs.values())              # newest leg — display / snapshot stamp
    clock = bar_clock(tfs_raw, asofs, metas)
    uni = classify_universe(tfs_raw)
    hist = short_history(tfs_raw, metas)    # กฎ (ai) — flag only, stages are NOT altered
    sanity = sanity_checks(tfs_raw, meta, off) + clock_notes(clock) + hist_notes(hist)
    frames = prep_frames(tfs_raw, uni, asofs)
    wk = None
    if "1w" in frames:
        for g in frames["1w"].values():
            if len(g):
                wk = g.Datetime.iloc[-1]
                break
    wscale = week_scale(tfs_raw, wk.normalize() - pd.Timedelta(days=wk.weekday()), uni) if wk is not None else 1.0
    # full = whole dataset has 1D+1W (real 4-phase UIPT); short = only 1H/4H
    screen_mode = "full" if ("1d" in tfs_raw and "1w" in tfs_raw) else "short"
    spy1d = frames.get("1d", {}).get("SPY")
    views = {}
    for s in uni["all"]:
        v = symbol_view(frames, s, wscale)
        src = price_source(tfs_raw, asofs, s)   # live last print (may be a forming bar)
        v["px_now"] = round(src["px"], 4) if src else None
        v["_px_src"] = src                      # tf / bar stamp / forming / age — label it in reports
        if s not in uni["noneq"]:
            v["_stage"] = uipt_stage(v, frames, screen_mode)
            # -ez is an opt-in sibling stage computed ALWAYS (cheap) so the default
            # digest can surface it as an extra column; it never overrides _stage.
            if screen_mode == "full":
                v["_stage_ez"] = uipt_stage_ez(v, frames, spy1d)
            v["_coil"] = coil_view(frames, s)
            v["_levels"] = levels_view(frames, s)
        sh = {tf: {"bars": h["short"][s], "unreliable": hist_unreliable(h["short"][s])}
              for tf, h in hist.items() if s in h["short"]}
        if "1w" in sh and "1d" not in sh and "1d" in tfs_raw:
            # 80 แถวรายวัน "ดูปกติ" แต่ประวัติจริง ≈ 5 วัน × สัปดาห์ที่มี (SPCX 1w:19 ⇒ ~95 วัน: EMA200 รายวันก็ ≈ ราคา IPO)
            est = 5 * sh["1w"]["bars"]          # วัด 22 ต.ค.: ค่าจริง (Yahoo) ต่ำกว่านี้ 3–9 วัน — IPO สัปดาห์แรกไม่เต็ม
            if est < 200:
                sh["1d"] = {"bars": est, "est": True, "unreliable": hist_unreliable(est)}
        if sh:
            v["_hist"] = sh                     # {tf: {bars, unreliable[]}} — กฎ (ai)
        views[s] = v
    regime = regime_view(views, tfs_raw, uni)
    sectors = sector_map(views, frames, uni)
    port = portfolio_marks(parse_port(port_path), tfs_raw, views) if port_path else []
    import datetime as _dt
    newest = max(os.path.getmtime(f) for f in files)
    state = {"asof_et": str(asof), "fingerprint": fingerprint(files),
             "asof_by_tf": {tf: str(t) for tf, t in asofs.items()},
             "bar_clock": clock,
             "can_judge_daily_close": bool(clock.get("1d", {}).get("can_judge_daily_close")),
             "csv_newest_mtime": _dt.datetime.fromtimestamp(newest).strftime("%Y-%m-%d %H:%M"),
             "files": [os.path.basename(f) for f in files], "meta": meta, "meta_by_tf": metas,
             "tz_shift_applied_h": off, "wscale": round(wscale, 3), "universe": uni,
             "tfs_present": sorted(tfs_raw.keys(), key=lambda t: TFS.index(t)),
             "screen_mode": screen_mode,
             "sanity": sanity, "views": views, "regime": regime, "sectors": sectors,
             "short_history": hist,
             "portfolio": port, "news": load_news(csv_dir)}
    state["digest"] = build_digest(state)
    return state


def history_dir(base: str, state: dict) -> str:
    stamp = re.sub(r"[: ]", "", state["asof_et"][:16].replace("-", ""))
    return os.path.join(base, f"{stamp}_{state['fingerprint'][:8]}")


def save_history(base: str, state: dict, report_md: str | None = None) -> str:
    d = history_dir(base, state)
    os.makedirs(d, exist_ok=True)
    slim = {k: v for k, v in state.items() if k != "digest"}
    with open(os.path.join(d, "full.json"), "w", encoding="utf-8") as f:
        json.dump(slim, f, ensure_ascii=False, default=str, indent=1)
    with open(os.path.join(d, "digest.md"), "w", encoding="utf-8") as f:
        f.write(state["digest"])
    if report_md:
        with open(os.path.join(d, "report.md"), "w", encoding="utf-8") as f:
            f.write(report_md)
    with open(os.path.join(base, "LATEST"), "w") as f:
        f.write(os.path.basename(d))
    return d


REPORTS_DIRNAME = "reports"


def reports_dir(base: str) -> str:
    d = os.path.join(base, REPORTS_DIRNAME)
    os.makedirs(d, exist_ok=True)
    return d


def save_report(base: str, report_md: str, state: dict | None = None) -> tuple[str, str]:
    """Write the report to TWO places:
      1) history/reports/report_latest.md   — always the newest (overwritten)
      2) history/reports/report_<YYYYMMDD_HHMM>[_<asof>].md — dated archive copy
    The reports/ dir is NEVER touched by clean-csv/clean-history/clean-all, so
    every analysis survives a clean-all. Also drops report.md into the matching
    snapshot dir if one exists (that copy is disposable)."""
    import datetime as _dt
    rd = reports_dir(base)
    latest = os.path.join(rd, "report_latest.md")
    with open(latest, "w", encoding="utf-8") as f:
        f.write(report_md)
    now = _dt.datetime.now().strftime("%Y%m%d_%H%M")
    asof = ""
    if state and state.get("asof_et"):
        asof = "_asof" + re.sub(r"[^0-9]", "", str(state["asof_et"])[:16])
    dated = os.path.join(rd, f"report_{now}{asof}.md")
    with open(dated, "w", encoding="utf-8") as f:
        f.write(report_md)
    # disposable copy inside the snapshot dir (gets cleaned with history)
    snap = None
    if state:
        snap = history_dir(base, state)
        if os.path.isdir(snap):
            with open(os.path.join(snap, "report.md"), "w", encoding="utf-8") as f:
                f.write(report_md)
    # wipe-proof copy: stamp the dated report into report_archive/ NOW, not only
    # at --clear-all time, so a history/ wipe can never lose an analysis
    try:
        import shutil as _sh
        arc = os.path.join(_archive_root(base, REPORT_ARCHIVE_DIRNAME),
                           archive_stamp(base, os.path.basename(snap) if snap else None))
        os.makedirs(arc, exist_ok=True)
        _sh.copy2(dated, os.path.join(arc, os.path.basename(dated)))
    except OSError:
        pass  # archiving must never block the save itself
    return latest, dated


def list_reports(base: str) -> list[str]:
    rd = os.path.join(base, REPORTS_DIRNAME)
    if not os.path.isdir(rd):
        return []
    return sorted(f for f in os.listdir(rd)
                  if f.startswith("report_") and f != "report_latest.md")


# ── Legacy archive ──────────────────────────────────────────────────────────
# clear-all is destructive on the WORKING dirs (csv/ + history/), but every set
# is first STAMPED into a permanent legacy archive that clear-all never touches.
# Layout (siblings of the project working dirs, so a history/ wipe can't hit them):
#   csv_archive/<stamp>/         ← copy of the csv set that produced the snapshot
#   report_archive/<stamp>/      ← digest.md + report.md + full.json (if present)
# <stamp> = <asof12>_<fp8> when available (matches the snapshot dir name), else
# the wall-clock time — so archived sets sort chronologically and never collide.
CSV_ARCHIVE_DIRNAME = "csv_archive"
REPORT_ARCHIVE_DIRNAME = "report_archive"


def _archive_root(base: str, dirname: str) -> str:
    # base is the history/ dir; archives live next to it under the project root.
    return os.path.join(os.path.dirname(os.path.abspath(base)) or ".", dirname)


def archive_stamp(base: str, snap: str | None = None) -> str:
    """A collision-free, chronologically-sortable stamp for one archived set.
    Prefer the snapshot dir name (<asof>_<fp>); else fall back to now()."""
    import datetime as _dt
    if snap and re.match(r"\d{12}", snap):
        return snap
    return _dt.datetime.now().strftime("%Y%m%d%H%M") + "_manual"


def archive_set(base: str, csv_dir: str, snap: str | None = None,
                report_md: str | None = None) -> dict:
    """STAMP the current working set into the permanent legacy archive.
    Copies (never moves) so the caller can still delete the originals after.
    Returns {stamp, csv_archive, report_archive, n_csv, kinds}."""
    import shutil
    if snap is None:
        snap = latest_snapshot(base)
        snap = os.path.basename(snap) if snap else None
    stamp = archive_stamp(base, snap)

    csv_arc = os.path.join(_archive_root(base, CSV_ARCHIVE_DIRNAME), stamp)
    rep_arc = os.path.join(_archive_root(base, REPORT_ARCHIVE_DIRNAME), stamp)
    os.makedirs(csv_arc, exist_ok=True)
    os.makedirs(rep_arc, exist_ok=True)

    n_csv = 0
    if os.path.isdir(csv_dir):
        for f in sorted(glob.glob(os.path.join(csv_dir, "*.csv"))):
            shutil.copy2(f, os.path.join(csv_arc, os.path.basename(f)))
            n_csv += 1

    kinds = []
    snap_dir = os.path.join(base, snap) if snap else None
    for fn in ("digest.md", "report.md", "full.json"):
        src = os.path.join(snap_dir, fn) if snap_dir else None
        if src and os.path.exists(src):
            shutil.copy2(src, os.path.join(rep_arc, fn))
            kinds.append(fn)
    # also fold in the newest dated report from reports/ if the snapshot lacked one
    if "report.md" not in kinds:
        reps = list_reports(base)
        if reps:
            shutil.copy2(os.path.join(base, REPORTS_DIRNAME, reps[-1]),
                         os.path.join(rep_arc, "report.md"))
            kinds.append("report.md(from reports/)")
    # a tiny manifest so the archive is self-describing when read back later
    with open(os.path.join(rep_arc, "MANIFEST.txt"), "w", encoding="utf-8") as f:
        f.write(f"stamp={stamp}\nfrom_snapshot={snap}\nn_csv={n_csv}\n"
                f"kinds={','.join(kinds)}\n")
    return {"stamp": stamp, "csv_archive": csv_arc, "report_archive": rep_arc,
            "n_csv": n_csv, "kinds": kinds}


def list_archives(base: str) -> list[dict]:
    """Every legacy set ever stamped, newest last. Reads report_archive/ as the
    index (it always exists once a set is archived). Never recomputes."""
    root = _archive_root(base, REPORT_ARCHIVE_DIRNAME)
    if not os.path.isdir(root):
        return []
    out = []
    for stamp in sorted(os.listdir(root)):
        d = os.path.join(root, stamp)
        if not os.path.isdir(d):
            continue
        csv_d = os.path.join(_archive_root(base, CSV_ARCHIVE_DIRNAME), stamp)
        n_csv = len(glob.glob(os.path.join(csv_d, "*.csv")))
        # raw csv dirs older than the hot window live in csv_archive_packed/<day>.tar.zst
        # (see references/archive-storage.md) — still restorable, just not on disk raw
        packed = os.path.exists(os.path.join(_archive_root(base, "csv_archive_packed"),
                                             f"{stamp[:8]}.tar.zst"))
        out.append({
            "stamp": stamp,
            "has_report": os.path.exists(os.path.join(d, "report.md")),
            "has_digest": os.path.exists(os.path.join(d, "digest.md")),
            "has_full": os.path.exists(os.path.join(d, "full.json")),
            "n_csv": n_csv,
            "csv_packed": packed and n_csv == 0,
            "report_dir": d,
            "csv_dir": csv_d,
        })
    return out


def read_archive_report(base: str, stamp: str | None = None) -> str:
    """Return an archived report.md (default: newest). For reading history back."""
    arcs = list_archives(base)
    if not arcs:
        return "(no legacy archives yet)"
    pick = next((a for a in arcs if a["stamp"] == stamp), None) if stamp else arcs[-1]
    if pick is None:
        return f"(no archive with stamp {stamp}; have: {[a['stamp'] for a in arcs]})"
    for fn in ("report.md", "digest.md"):
        p = os.path.join(pick["report_dir"], fn)
        if os.path.exists(p):
            return open(p, encoding="utf-8").read()
    return f"(archive {pick['stamp']} has no report.md/digest.md)"


def read_archive_digest(base: str, stamp: str | None = None) -> str:
    """Return an archived DIGEST (every computed number), default newest. The
    archived report_archive/<stamp>/ IS a full history snapshot — digest.md +
    full.json + report.md — so a cleared snapshot is still fully readable."""
    arcs = list_archives(base)
    if not arcs:
        return "(no legacy archives yet)"
    pick = next((a for a in arcs if a["stamp"] == stamp), None) if stamp else arcs[-1]
    if pick is None:
        return f"(no archive with stamp {stamp}; have: {[a['stamp'] for a in arcs]})"
    p = os.path.join(pick["report_dir"], "digest.md")
    if os.path.exists(p):
        return open(p, encoding="utf-8").read()
    # no saved digest (hand-recovered set) — rebuild from full.json if present
    fj = os.path.join(pick["report_dir"], "full.json")
    if os.path.exists(fj):
        return build_digest(json.load(open(fj, encoding="utf-8")))
    return (f"(archive {pick['stamp']} has neither digest.md nor full.json — "
            f"recompute from csv_archive/{pick['stamp']}/ with a fresh run)")


# ============================================================================
# Deterministic action helpers — the mechanical stuff the report used to
# recompute by hand every time. These are pure functions of the snapshot, so
# ANY caller (Claude, bash, Gemini) gets identical numbers. They compute; the
# NARRATIVE (regime call, news read, theme, the *reason* text) stays the model's
# job and must never be hard-coded here.
# ============================================================================

STAGE_GLOSS = {
    "TRIGGER": "ยิงแล้ว—ทะลุ pivot+วอลุ่ม เข้าได้ตามจุด",
    "SETUP": "ฟอร์มแน่น จ่อ pivot รอ trigger",
    "SETUP(loose)": "ฟอร์มหลวมๆ ยังไม่แน่น เฝ้า",
    "MACRO-WATCH": "โครงสร้างผ่าน macro filter รอฟอร์ม setup",
    "WATCH(loose)": "เข้าเกณฑ์เฝ้าแบบหลวม",
    "FAIL": "เคยฟอร์มแล้วพังกลางทาง ไม่เข้าใหม่",
    "KILL": "โดนตัด (Kill-Switch) ห้ามเล่น รอฟื้น",
    "NO-DATA": "ข้อมูลไม่พอ ข้าม",
    "TRIGGER-S": "ยิงแล้ว (สั้น)", "SETUP-S": "จ่อยิง (สั้น)",
    "WATCH-S": "เฝ้า (สั้น)", "FAIL-S": "พังกลางทาง (สั้น)", "KILL-S": "โดนตัด (สั้น)",
    "REVERSAL": "[-ez] เพิ่งกลับตัว—1D GC แล้ว weekly GC จ่อตาม RS ดี (early turn)",
}


def stage_gloss(stage: str | None) -> str:
    """stage label -> plain-Thai gloss. Pure lookup; '' if unknown."""
    return STAGE_GLOSS.get(stage or "", "")


def _pivot(v: dict):
    return (v.get("_coil") or {}).get("pivot15d") or (v.get("_levels") or {}).get("swing_hi15")


def _floor2(x: float) -> float:
    """Round a stop DOWN to the cent so rounding never pulls it inside 1.5 x ATR (BT-19)."""
    return math.floor(x * 100 + 1e-9) / 100


def trade_setup(v: dict) -> dict | None:
    """Deterministic entry/stop/TP from pivot + ATR + EMAs: breakout entry = pivot;
    pullback entry = 1H EMA20/VWAP (or E20d), never above px.
    BT-19 (core invariant): every stop sits >= 1.5 x ATR14 under the entry it protects.
    TP1 = entry-side pivot + 2 x ATR, capped at the nearest real structure above the
    pivot (swing_hi60) — same shape as the TURN lane (SL 1.5 / TP1 2 / TP2 3 ATR).
    (แก้ 15 ต.ค. 2026 — เดิม SL breakout = pivot −0.5×ATR · SL ย่อ = min(EMA20 1h, pivot −1×ATR)
    ซึ่งเท่ากับจุดเข้าแบบย่อพอดี · TP1/TP2 = +1/+2×ATR) · None if no levels."""
    lv = v.get("_levels") or {}
    px, atr, piv = v.get("px_now"), lv.get("atr14d"), _pivot(v)
    if not (px and atr and piv):
        return None
    e20h, vwap = lv.get("e20_1h"), lv.get("vwap_1h")
    pull = e20h or vwap or lv.get("e20d")
    base = min(x for x in (pull, px) if x)                                # pullback fill can't be above px
    stop = _floor2(base - 1.5 * atr)                                      # BT-19 for the pullback entry
    stop_tight = _floor2(piv - 1.5 * atr)                                 # BT-19 for the breakout entry
    tp1, tp2 = piv + 2 * atr, piv + 3 * atr
    hi60 = lv.get("swing_hi60")
    if hi60 and piv + 0.5 * atr < hi60 < tp1:                             # nearest real resistance caps TP1
        tp1 = hi60
    tp1, tp2 = round(tp1, 2), round(tp2, 2)
    rr1 = round((tp1 - base) / (base - stop), 2) if base > stop and tp1 > base else None
    # RR for the breakout plan (entry=pivot): the one that matters when buying strength
    rr_break = round((tp1 - piv) / (piv - stop_tight), 2) if piv > stop_tight else None
    return {"pivot": piv, "dist_to_pivot_pct": round((px / piv - 1) * 100, 1),
            "entry_breakout": piv, "entry_pullback": pull,
            "stop": stop, "stop_tight": stop_tight,
            "tp1": tp1, "tp2": tp2, "rr_to_tp1": rr1, "rr_breakout": rr_break,
            "atr": atr, "ext200_pct": (v.get("_stage") or {}).get("ext200_pct")}


def rank_short(views: dict, max_dist: float = 2.5) -> list[dict]:
    """UIPT-S readiness (deterministic): non-kill names sitting AT/just under their
    pivot (within +0.5% / -max_dist%) with positive 1H flow, scored by closeness +
    1H cmf + rvol, penalizing >50% extension. Model narrates the top few."""
    out = []
    for s, v in views.items():
        st = (v.get("_stage") or {}).get("stage") or ""
        if st.startswith("KILL") or st in ("FAIL", "FAIL-S", "NO-DATA"):
            continue
        ts = trade_setup(v)
        if not ts:
            continue
        d = ts["dist_to_pivot_pct"]
        if d is None or d > 0.5 or d < -max_dist:      # must be near the pivot
            continue
        h1 = v.get("1h") or {}
        cmf, rvol = (h1.get("cmf20") or 0), (h1.get("rvol") or 0)
        if cmf <= 0:                                    # 1H flow must confirm
            continue
        ext = ts.get("ext200_pct") or 0
        score = -abs(d) + cmf * 2 + min(rvol, 3) * 0.5 - max(0, ext - 50) / 50
        out.append({"sym": s, "stage": st, "gloss": stage_gloss(st), "dist_pct": d,
                    "cmf1h": cmf, "rvol1h": rvol, "ext200": ext, "score": round(score, 2),
                    "entry_breakout": ts["entry_breakout"], "entry_pullback": ts["entry_pullback"],
                    # UIPT-S enters on the breakout (entry=pivot, tight stop), so the
                    # breakout R:R is the relevant one — not the wide structural R:R.
                    "stop": ts["stop_tight"], "tp1": ts["tp1"], "tp2": ts["tp2"],
                    "rr_to_tp1": ts["rr_breakout"]})
    out.sort(key=lambda x: -x["score"])
    return out


def portfolio_analytics(marks: list[dict]) -> dict:
    """Weights, MV totals, stage-by-MV%, gains concentration — pure arithmetic."""
    rows = []
    for m in marks:
        mv = (m.get("shares") or 0) * (m.get("px") or 0)
        cb = (m.get("shares") or 0) * (m.get("cost") or 0)
        rows.append({**m, "mv": mv, "cb": cb, "pl": mv - cb})
    tmv = sum(r["mv"] for r in rows) or 1
    by_stage = {}
    for r in rows:
        by_stage[r.get("stage")] = by_stage.get(r.get("stage"), 0) + r["mv"]
    gains = sorted([r for r in rows if r["pl"] > 0], key=lambda x: -x["pl"])
    tg = sum(r["pl"] for r in gains) or 1
    return {"total_mv": round(tmv), "total_cost": round(sum(r["cb"] for r in rows)),
            "total_pl": round(sum(r["pl"] for r in rows)),
            "stage_by_mv_pct": {k: round(v / tmv * 100, 1)
                                for k, v in sorted(by_stage.items(), key=lambda x: -x[1])},
            "weights": sorted([{"sym": r["sym"], "book": r.get("book"),
                                "wt_pct": round(r["mv"] / tmv * 100, 1),
                                "pl_pct": r.get("pl_pct"), "stage": r.get("stage")}
                               for r in rows], key=lambda x: -x["wt_pct"]),
            "gains_concentration": [{"sym": r["sym"], "pl": round(r["pl"]),
                                     "pct_of_gains": round(r["pl"] / tg * 100, 1),
                                     "stage": r.get("stage")} for r in gains]}


def action_hint(mark: dict, view: dict) -> dict:
    """Rule-based SHORT verb+level & MEDIUM verb skeleton. This fixes only the
    MECHANICAL choice (which verb, which stop level) so it isn't hand-derived each
    time — the *reason narrative* is still the model's to write. Rules:
      SHORT: winner>40% & 1W Dist -> trim½ | underwater & below E200d -> cut(@E200d)
             | KILL & underwater -> stop@swingLo | else hold(@1H EMA20/swingLo)
      MED:   1W Accum -> hold-core | 1W Dist -> reduce | KILL & underwater -> exit
             | else hold-watch"""
    lv = view.get("_levels") or {}
    w1 = (view.get("1w") or {}).get("status")
    stage, pl = (mark.get("stage") or ""), (mark.get("pl_pct") or 0)
    px, e200, e20h, slo = mark.get("px"), lv.get("e200d"), lv.get("e20_1h"), lv.get("swing_lo10")
    if pl > 40 and w1 == "Dist":
        sv, sl = "trim ½", "ล็อกกำไร (1W Dist)"
    elif w1 == "Accum" and px and e200 and px < e200:
        # structurally healthy long-term (1W Accum) sitting under E200d = a dip,
        # not a cut — hold tight and watch the reclaim, don't knife it.
        sv, sl = "hold-tight", f"รอ reclaim E200d {e200}"
    elif px and e200 and px < e200 and pl < 0:
        sv, sl = "cut", f"หลุด E200d {e200}"
    elif "KILL" in stage and pl < 0:
        sv, sl = "stop วินัย", f"ใต้ swingLo {slo}"
    else:
        sv, sl = "hold", f"stop {e20h or slo}"
    if w1 == "Accum":
        mv = "ถือแกน / รอ reclaim"
    elif w1 == "Dist":
        mv = "reduce / ไม่เติม"
    elif "KILL" in stage and pl < 0:
        mv = "exit-the-name"
    else:
        mv = "ถือ เฝ้า flow"
    return {"short_verb": sv, "short_level": sl, "med_verb": mv}


def ez_horizon(ez: dict) -> str:
    """Deterministic holding-horizon label for an -ez name, from its stage/flags.
    Short = days, medium = weeks–months. The model may refine the reason, but the
    horizon MUST be stated (user rule: สั้น=วัน, กลาง=W/M)."""
    st = ez.get("stage")
    if st == "REVERSAL":
        return "กลาง 2–6M (early turn, thesis ยาว)"
    if ez.get("dip_forgiven"):
        # a leader on a daily dip: playable short as the bounce, medium if it holds
        return "สั้น 1–3D (เด้ง) / กลาง 2–4W (ถ้ายืน)"
    if st in ("SETUP", "SETUP(loose)"):
        return "กลาง 2–6W"
    if st in ("MACRO-WATCH", "WATCH(loose)"):
        return "กลาง 3–8W (รอฟอร์ม)"
    if st == "TRIGGER":
        return "สั้น 1–5D → กลาง"
    return "กลาง (ตาม flow)"


def ez_action(ez: dict, ts: dict | None) -> str:
    """Plain-Thai action line for an -ez name (verb + what to do + level). The
    model adds the *why*/theme, but the mechanical action+level is fixed here."""
    st = ez.get("stage")
    piv = ts["entry_breakout"] if ts else None
    stop = ts["stop"] if ts else None
    if st == "REVERSAL":
        return (f"รอ confirm—ยืนเหนือ {piv} (breakout จุดกลับตัว) ค่อยเข้าไม้กลาง, "
                f"stop {stop}" if piv else "รอ confirm breakout ก่อนเข้าไม้กลาง")
    if ez.get("dip_forgiven"):
        return (f"leader ย่อ—ถ้าเด้งเหนือ {piv} เล่นสั้น/ทยอยสะสมไม้กลาง, stop {stop} "
                f"(1W ยัง Accum จึงยังไม่ทิ้ง)" if piv
                else "leader ย่อชั่วคราว—ทยอยสะสม, 1W ยัง Accum")
    if st in ("SETUP", "SETUP(loose)"):
        return f"จ่อ pivot {piv}—ยืน+วอลุ่ม = เข้าไม้กลาง, stop {stop}" if piv else "จ่อ pivot รอ trigger"
    if st in ("MACRO-WATCH", "WATCH(loose)"):
        return "อยู่เรดาร์—ยังไม่ฟอร์ม setup, เฝ้ารอย่อ/ทะลุก่อน"
    return "เฝ้าตาม flow"


def ez_pack(state: dict) -> str:
    """Isolate the -ez opportunities: names the strict default kills but -ez keeps,
    ranked, each with horizon (สั้น=วัน / กลาง=W-M) + a plain-Thai action. For
    `run.sh --ez`."""
    views = state.get("views", {})
    DEAD = {"KILL", "FAIL", "NO-DATA"}
    rows = []
    for s, v in views.items():
        ez, st = v.get("_stage_ez"), (v.get("_stage") or {}).get("stage")
        if not ez or ez.get("stage") == st or ez.get("stage") in DEAD:
            continue
        ts = trade_setup(v)
        rows.append((s, st, ez, ts))
    L = ["# -ez looser screen (OPT-IN — confirm vs regime, never auto-buy)",
         f"as-of {state.get('asof_et')} | regime hint: "
         f"{(state.get('regime') or {}).get('permission_hint')}",
         f"\n{len(rows)} names the strict default KILLed/FAILed that -ez keeps "
         f"(default stages unchanged):", ""]
    if not rows:
        L.append("_none — the strict screen and -ez agree on the playable set right now._")
        return "\n".join(L)
    L.append("|sym|default→ez|px|RS60|ext%|horizon|stage (ภาษาคน)|action (ภาษาคน) + level|")
    L.append("|--|--|--|--|--|--|--|--|")
    rows.sort(key=lambda r: -(r[2].get("rs60") or -99))
    for s, st, ez, ts in rows:
        L.append(f"|{s}|{st}→**{ez['stage']}**|{fmt(views[s].get('px_now'))}|"
                 f"{fmt(ez.get('rs60'))}|{fmt(ez.get('ext200_pct'))}|{ez_horizon(ez)}|"
                 f"{ez['stage']} ({stage_gloss(ez['stage'])})|{ez_action(ez, ts)}|")
    L.append("\n> Relaxed ONLY: 1D-Dist soft-kill (1W Accum+RS60>0) · EARLY-REVERSAL "
             "(1D GC, weekly GC pending, ext≤40%) · RSI 40→68. NOT relaxed: news×flow, "
             "ETF/indices/sector regime, ext cap, multi-TF. Each name still needs the "
             "regime + news gate before it's a buy. horizon: สั้น=วัน, กลาง=สัปดาห์/เดือน.")
    return "\n".join(L)


def coiled_spring(v: dict) -> dict | None:
    """COILED SPRING screener — 6–12 month "cheap before it runs, low risk" setup.
    Finds names that are NOT yet extended but are structurally coiling with quiet
    smart-money accumulation, ranked so the LOWEST-RISK springs come first.

    Entry gates (all must hold):
      cheap    : ext200 in −20%..+12% (not blown up, not already extended)
      struct   : 1W not Distribution (long-term structure intact)
      accum    : 1W CMF>0 OR 1D cmf20>0 (smart money quietly building)
      coiled   : a coil tag (NEAR-PIVOT/COILING) OR a tight ATR% (vol contraction)
      rs_ok    : RS60 > −5 (not a market loser)
      not_hot  : 1D RSI < 65 (room left to run)

    risk_score 0–10 (LOWER = safer; rank ascending):
      + distance to stop as % of price (tight = safer)      up to 3
      + |ext200| (near EMA200 = less air underneath)        up to 3
      − 1W Accumulation bonus                                  −1.5
      − price above EMA200 bonus                              −1
      + thin-volume penalty (rvol<0.5 on 1D)                  +1
      + far-from-pivot penalty (needs a big move to trigger)  up to 1.5
    Returns None if it fails a gate."""
    d1, w1, h1 = v.get("1d"), v.get("1w"), v.get("1h")
    if not d1 or not w1:
        return None
    ext = (v.get("_stage") or {}).get("ext200_pct")
    if ext is None:
        return None
    lv = v.get("_levels") or {}
    px, atr = v.get("px_now"), lv.get("atr14d")
    coil = v.get("_coil")
    rs60 = (v.get("_stage_ez") or {}).get("rs60")

    # ATR% (volatility contraction proxy) — tight = coiled
    atr_pct = (atr / px * 100) if (atr and px) else None
    # upside room: distance to the 60-bar swing high (a real medium target, not
    # the 15-bar high which can be right overhead). Falls back to swing_hi15.
    swing_hi = lv.get("swing_hi60") or lv.get("swing_hi15")
    upside_pct = round((swing_hi / px - 1) * 100, 0) if (swing_hi and px) else None

    cheap = -20 <= ext <= 12
    struct = w1["status"] != "Dist"
    accum = (w1.get("cmf") or 0) > 0 or (d1.get("cmf20") or 0) > 0
    coiled = coil is not None or (atr_pct is not None and atr_pct <= 3.5)
    rs_ok = rs60 is not None and rs60 > -5
    not_hot = (d1.get("rsi") or 100) < 65
    has_room = upside_pct is not None and upside_pct >= 8   # must have somewhere to run
    if not (cheap and struct and accum and coiled and rs_ok and not_hot and has_room):
        return None

    # deterministic trade plan. A spring is ACCUMULATED on the pullback zone, so the
    # stop must sit BELOW that entry — not equal to it. Entry = 1H EMA20/VWAP (or
    # E20d); structural stop = one ATR under the entry, floored at E50d, never above px.
    ts = trade_setup(v)
    pivot = ts["pivot"] if ts else None
    entry = (ts or {}).get("entry_pullback") or lv.get("e20d") or px
    atr_stop = (entry - atr) if (entry and atr) else None
    stop = atr_stop if atr_stop is not None else lv.get("e50d")
    if stop is not None and lv.get("e50d"):
        stop = min(stop, lv["e50d"])          # don't sit above the 50d structure
    if stop is not None and px and stop >= px:
        stop = round(px - atr, 2) if atr else round(px * 0.94, 2)
    stop = round(stop, 2) if stop is not None else None
    # risk = how far the structural stop is under the current price (real downside if
    # wrong). Scored on the structural stop exactly as before so SPRING membership —
    # the set BT-35 measures — does not move because of the BT-19 floor below.
    stop_dist_pct = ((px - stop) / px * 100) if (px and stop and px > stop) else 8.0
    # BT-19 (core invariant): the PRINTED stop is never tighter than 1.5 x ATR14 under
    # the entry (แก้ 15 ต.ค. 2026 — เดิมพิมพ์ entry −1×ATR)
    if stop is not None and entry and atr:
        stop = _floor2(min(stop, entry - 1.5 * atr))

    risk = 0.0
    risk += min(3.0, stop_dist_pct / 3)          # tight stop = low risk
    risk += min(3.0, abs(ext) / 7)               # near EMA200 = low risk
    if w1["status"] == "Accum":
        risk -= 1.5
    if d1.get("c_gt_e200"):
        risk -= 1.0
    if (d1.get("rvol") or 1) < 0.5:
        risk += 1.0
    if coil and coil.get("dist_pct") is not None:
        risk += min(1.5, abs(coil["dist_pct"]) / 8)   # far pivot = needs a big move
    risk = max(0.0, min(10.0, round(risk, 1)))

    return {"ext200": ext, "rs60": rs60, "atr_pct": round(atr_pct, 1) if atr_pct else None,
            "coil_tag": (coil or {}).get("tag"), "w1": w1["status"],
            "d1_cmf20": d1.get("cmf20"), "rsi": d1.get("rsi"),
            "risk_score": risk, "upside_to_swinghi_pct": upside_pct,
            "pivot": pivot, "entry_pullback": (ts or {}).get("entry_pullback"),
            "stop": stop, "tp1": (ts or {}).get("tp1"), "tp2": (ts or {}).get("tp2")}


def coiled_spring_pack(state: dict, max_risk: float = 6.0) -> str:
    """COILED SPRING screen — cheap-before-it-runs, ranked LOWEST-RISK first.
    Emitted every screen. Medium-long horizon (6–12 months)."""
    views = state.get("views", {})
    rows = []
    for s, v in views.items():
        if s in (state.get("universe", {}).get("noneq") or []):
            continue
        cs = coiled_spring(v)
        if cs and cs["risk_score"] <= max_risk:
            rows.append({"sym": s, **cs})
    rows.sort(key=lambda r: (r["risk_score"], -(r["rs60"] or -99)))
    L = ["# 🌱 COILED SPRING — ถูกก่อนวิ่ง เสี่ยงต่ำสุด (6–12 เดือน)",
         f"as-of {state.get('asof_et')} | regime hint: "
         f"{(state.get('regime') or {}).get('permission_hint')}",
         "_ยังไม่ ext + โครงยาวไม่พัง + smart money สะสมเงียบ + บีบตัวจ่อดีด; เรียงเสี่ยงต่ำ→สูง._", ""]
    if not rows:
        L.append("_ไม่มีสปริงที่ผ่านเกณฑ์ตอนนี้ (ตลาดยังไม่มีของถูกที่จ่อดีดแบบเสี่ยงต่ำ)._")
        return "\n".join(L)
    L.append("|#|sym|risk↓|ext%|RS60|1W|RSI|coil|upside→hi|entry (pullback)|stop|TP1|")
    L.append("|--|--|--|--|--|--|--|--|--|--|--|--|")
    for i, r in enumerate(rows, 1):
        coil_lbl = r["coil_tag"] or (f"ATR{r['atr_pct']}%" if r.get("atr_pct") else "-")
        L.append(f"|{i}|{r['sym']}|**{r['risk_score']}**|{fmt(r['ext200'])}|{fmt(r['rs60'])}|"
                 f"{r['w1']}|{fmt(r['rsi'])}|{coil_lbl}|"
                 f"{fmt(r['upside_to_swinghi_pct'])}%|{fmt(r['entry_pullback'])}|{fmt(r['stop'])}|"
                 f"{fmt(r['tp1'])}|")
    L.append("\n> risk↓ = ยิ่งต่ำยิ่งปลอดภัย (stop แคบ + ext ใกล้ 0 + 1W Accum + เหนือ E200). "
             "COILED SPRING = ยังไม่พุ่งแต่จ่อดีด: เข้าไม้กลาง-ยาว (6–12M) ทยอยสะสมโซน pullback, "
             "SL ใต้โครงสร้าง. ยังต้อง gate regime+news. horizon: กลาง-ยาว 3–12M.")
    return "\n".join(L)


def conviction(v: dict, use_ez: bool = False) -> dict | None:
    """Deterministic conviction score 0–10 for one name, across BOTH the strict
    UIPT stage and (optionally) its -ez stage. High conviction = multi-TF flow
    aligned + right stage + near a clean pivot + not extended. Returns None for
    dead names. The model still gates on regime/news; this only ranks setups."""
    stg = (v.get("_stage_ez") if use_ez else v.get("_stage")) or {}
    st = stg.get("stage")
    if not st or st.startswith("KILL") or st in ("FAIL", "FAIL-S", "NO-DATA"):
        return None
    d1, w1, h1 = v.get("1d") or {}, v.get("1w") or {}, v.get("1h") or {}
    ts = trade_setup(v)
    sc = 0.0
    # stage weight
    sc += {"TRIGGER": 4, "SETUP": 3, "REVERSAL": 2.5, "MACRO-WATCH": 2,
           "SETUP(loose)": 1.5, "WATCH(loose)": 1}.get(st, 0)
    # multi-TF flow alignment
    if (w1.get("cmf") or 0) > 0: sc += 1.5
    if w1.get("status") == "Accum": sc += 1
    if (d1.get("cmf20") or 0) > 0: sc += 1
    if (h1.get("cmf20") or 0) > 0: sc += 0.5
    # near a clean pivot (deterministic entry exists and within reach)
    if ts and ts.get("dist_to_pivot_pct") is not None:
        dd = ts["dist_to_pivot_pct"]
        if -3 <= dd <= 0.5: sc += 1.5
        elif -6 <= dd < -3: sc += 0.5
    # RS leadership (if computed on the ez path)
    if (stg.get("rs60") or 0) > 20: sc += 1
    # penalties
    ext = stg.get("ext200_pct") or 0
    if ext > 50: sc -= 2
    elif ext > 40: sc -= 1
    if (h1.get("rvol") or 0) < 0.5: sc -= 0.5   # thin = unreliable trigger
    sc = max(0.0, min(10.0, round(sc, 1)))
    return {"score": sc, "stage": st, "ez": use_ez, "ts": ts,
            "rs60": stg.get("rs60"), "ext200": ext}


def conviction_horizon(stage: str, ez: bool, ext: float | None) -> str:
    """Deterministic holding horizon for a high-conviction setup, from stage + path.
    User rule: high-conviction MUST say short vs medium and how long. Days for the
    short trigger leg, weeks/months for the position thesis."""
    ex = ext or 0
    if stage == "TRIGGER":
        return "สั้น 1–5D (โมเมนตัม) → กลาง 4–8W ถ้ายืน"
    if stage == "REVERSAL":
        return "กลาง 4–12W→2–6M (early turn, ถือยาวได้)"
    if stage == "SETUP":
        # a breakout you can trade short and hold medium
        return "สั้น 2–5D (breakout) → กลาง 3–8W"
    if stage == "SETUP(loose)":
        return "สั้น 2–5D (ถ้า trigger) / กลาง 3–6W"
    if stage in ("MACRO-WATCH", "WATCH(loose)"):
        return "กลาง 3–8W (รอ trigger ก่อน; สั้นเฉพาะเด้ง 1–3D)"
    return "กลาง 3–8W"


def high_conviction_pack(state: dict, min_score: float = 6.0) -> str:
    """Names with conviction >= min_score across BOTH strict UIPT and -ez, each
    with a FULL trade plan (entry/stop/TP1/TP2/RR). User rule: any name we're
    genuinely confident in — strict or ez — must ship entry+TP+SL."""
    views = state.get("views", {})
    rows = []
    for s, v in views.items():
        best = None
        for use_ez in (False, True):
            c = conviction(v, use_ez)
            if c and (best is None or c["score"] > best["score"]):
                best = {**c, "sym": s, "v": v}
        if best and best["score"] >= min_score and best["ts"]:
            rows.append(best)
    rows.sort(key=lambda r: -r["score"])
    L = [f"# High-conviction setups (score ≥ {min_score}/10) — full entry/TP/SL",
         f"as-of {state.get('asof_et')} | regime hint: "
         f"{(state.get('regime') or {}).get('permission_hint')}",
         "_conviction is deterministic (flow alignment + stage + pivot proximity − "
         "extension); still gate on regime/news before acting._", ""]
    if not rows:
        L.append(f"_none ≥ {min_score} right now — no setup clean enough for a full plan._")
        return "\n".join(L)
    L.append("|sym|score|via|horizon (สั้น/กลาง)|stage (ภาษาคน)|แผน breakout (entry/SL/RR)|แผน pullback (entry/SL)|TP1|TP2|")
    L.append("|--|--|--|--|--|--|--|--|--|")
    for r in rows:
        ts, via = r["ts"], ("-ez" if r["ez"] else "UIPT")
        hz = conviction_horizon(r["stage"], r["ez"], r.get("ext200"))
        brk = f"เข้า>{ts['entry_breakout']} · SL {ts['stop_tight']} · RR {fmt(ts['rr_breakout'])}"
        pb = f"ย่อ {fmt(ts['entry_pullback'])} · SL {ts['stop']}"
        L.append(f"|{r['sym']}|**{r['score']}**|{via}|{hz}|{r['stage']} ({stage_gloss(r['stage'])})|"
                 f"{brk}|{pb}|{ts['tp1']}|{ts['tp2']}|")
    L.append("\n> **2 แผนต่อตัว:** breakout = ซื้อแรงทะลุ pivot, SL แคบ (pivot−0.5ATR), RR ดี "
             "· pullback = รอย่อเข้า 1H EMA20/VWAP, SL กว้าง (ใต้โครงสร้าง) ทุนถูกกว่าแต่ต้องรอ. "
             "TP1/TP2 = pivot +1/+2 ATR. via=UIPT (strict) หรือ -ez. ยังต้อง gate regime+news ก่อนเข้า.")
    return "\n".join(L)


def action_pack(state: dict) -> str:
    """Assemble the deterministic pieces into one markdown 'action pack' the model
    then narrates (adds reasons/theme). Reads a snapshot's `state` (full.json)."""
    views = state.get("views", {})
    L = ["# Action Pack (deterministic — narrate on top, don't recompute)",
         f"as-of {state.get('asof_et')}  | regime hint: "
         f"{(state.get('regime') or {}).get('permission_hint')}", ""]

    L.append("## Stage glossary")
    for k, g in STAGE_GLOSS.items():
        if not k.endswith("-S"):
            L.append(f"- `{k}` — {g}")

    L.append("\n## UIPT-S short-play ranking (ready, near pivot, 1H flow+)")
    sr = rank_short(views)
    if not sr:
        L.append("_ไม่มีตัวพร้อมเข้าสั้นตอนนี้ (ไม่มีตัว near-pivot + 1H flow บวก)_")
    else:
        L.append("|#|sym|stage (ภาษาคน)|dist%|1Hcmf|rvol|ext|entry>|stop|TP1|TP2|R:R|")
        L.append("|--|--|--|--|--|--|--|--|--|--|--|--|")
        for i, r in enumerate(sr[:8], 1):
            L.append(f"|{i}|{r['sym']}|{r['stage']} ({r['gloss']})|{r['dist_pct']}|"
                     f"{r['cmf1h']}|{r['rvol1h']}|{fmt(r['ext200'])}|{r['entry_breakout']}|"
                     f"{r['stop']}|{r['tp1']}|{r['tp2']}|{fmt(r['rr_to_tp1'])}|")

    L.append("\n## Trade levels — all non-KILL/FAIL names")
    L.append("|sym|stage (ภาษาคน)|px|pivot|dist%|entry_pull|stop|TP1|TP2|")
    L.append("|--|--|--|--|--|--|--|--|--|")
    for s, v in views.items():
        st = (v.get("_stage") or {}).get("stage") or ""
        if st.startswith("KILL") or st in ("FAIL", "FAIL-S", "NO-DATA"):
            continue
        ts = trade_setup(v)
        if not ts:
            continue
        L.append(f"|{s}|{st} ({stage_gloss(st)})|{fmt(v.get('px_now'))}|{ts['pivot']}|"
                 f"{ts['dist_to_pivot_pct']}|{fmt(ts['entry_pullback'])}|{ts['stop']}|"
                 f"{ts['tp1']}|{ts['tp2']}|")

    port = state.get("portfolio") or []
    if port:
        pa = portfolio_analytics(port)
        L.append("\n## Portfolio analytics")
        L.append(f"- MV=${pa['total_mv']:,} | cost=${pa['total_cost']:,} | "
                 f"unreal=${pa['total_pl']:,}")
        L.append("- stage by MV%: " + " | ".join(
            f"{k} {v}%" for k, v in pa["stage_by_mv_pct"].items()))
        gc = pa["gains_concentration"][:4]
        L.append("- gains concentration: " + " ".join(
            f"{g['sym']}=${g['pl']:,}({g['pct_of_gains']}%)" for g in gc))
        L.append("\n## Per-name action hints (verb+level fixed; ADD the reason)")
        L.append("|sym|book|wt%|P&L%|stage (ภาษาคน)|🔹สั้น verb@level|🔸กลาง verb|")
        L.append("|--|--|--|--|--|--|--|")
        wt = {w["sym"]: w["wt_pct"] for w in pa["weights"]}
        for m in port:
            v = views.get(m["sym"], {})
            h = action_hint(m, v)
            st = m.get("stage") or ""
            L.append(f"|{m['sym']}|{m.get('book')}|{fmt(wt.get(m['sym']))}|{fmt(m.get('pl_pct'))}|"
                     f"{st} ({stage_gloss(st)})|{h['short_verb']} @ {h['short_level']}|{h['med_verb']}|")
    return "\n".join(L)


def latest_snapshot(base: str) -> str | None:
    p = os.path.join(base, "LATEST")
    if not os.path.exists(p):
        return None
    d = os.path.join(base, open(p).read().strip())
    return d if os.path.isdir(d) else None


def list_snapshots(base: str) -> list[str]:
    if not os.path.isdir(base):
        return []
    return sorted(d for d in os.listdir(base)
                  if os.path.isdir(os.path.join(base, d)) and re.match(r"\d{12}", d))


def list_snapshots_all(base: str) -> list[str]:
    """Every snapshot resolvable for compare/read: working history/ UNION the
    legacy report_archive/ (which keeps full.json). De-duped, chronological.
    This is what lets --compare still reach a set that --clear-all archived."""
    stamps = set(list_snapshots(base))
    arc = _archive_root(base, REPORT_ARCHIVE_DIRNAME)
    if os.path.isdir(arc):
        for s in os.listdir(arc):
            if re.match(r"\d{12}", s) and os.path.exists(
                    os.path.join(arc, s, "full.json")):
                stamps.add(s)
    return sorted(stamps)


def _load_full(base: str, snap: str) -> dict:
    """Load a snapshot's full.json, trying working history/ first, then the
    permanent report_archive/ — so archived sets stay comparable/readable."""
    for p in (os.path.join(base, snap, "full.json"),
              os.path.join(_archive_root(base, REPORT_ARCHIVE_DIRNAME), snap, "full.json")):
        if os.path.exists(p):
            return json.load(open(p, encoding="utf-8"))
    raise FileNotFoundError(
        f"no full.json for snapshot {snap} in history/ or report_archive/ "
        f"(available: {list_snapshots_all(base)})")


def compare_snapshots(base: str, a: str | None = None, b: str | None = None) -> str:
    snaps = list_snapshots_all(base)  # working + archived, so clear-all can't break compare
    if len(snaps) < 2 and not (a and b):
        return "need >=2 snapshots to compare (checked history/ + report_archive/)"
    a = a or snaps[-2]
    b = b or snaps[-1]
    ja = _load_full(base, a)
    jb = _load_full(base, b)
    L = [f"# Compare {a} -> {b}", f"as-of {ja['asof_et']} -> {jb['asof_et']}"]
    pa = ja["regime"].get("permission_hint")
    pb = jb["regime"].get("permission_hint")
    L.append(f"permission: {pa} -> {pb}" + ("  **CHANGED**" if pa != pb else ""))
    ka = set(ja["regime"]["breadth"]["kill_list"])
    kb = set(jb["regime"]["breadth"]["kill_list"])
    if ka != kb:
        L.append(f"kill list: +{sorted(kb-ka)} -{sorted(ka-kb)}")
    L.append("\n|sym|stage|px chg%|1D cmf Δ|1D IPI|note|")
    L.append("|--|--|--|--|--|--|")
    for s in sorted(set(jb["views"]) | set(ja["views"])):
        va, vb = ja["views"].get(s, {}), jb["views"].get(s, {})
        sa = (va.get("_stage") or {}).get("stage")
        sb = (vb.get("_stage") or {}).get("stage")
        da, db_ = va.get("1d") or {}, vb.get("1d") or {}
        if not db_:
            continue
        chg = (db_["close"] / da["close"] - 1) * 100 if da.get("close") else None
        dcmf = (db_.get("cmf") or 0) - (da.get("cmf") or 0) if da else None
        note = f"stage {sa}->{sb}" if sa != sb else ""
        flip = da and (da.get("cmf") or 0) > 0 > (db_.get("cmf") or 0)
        if flip:
            note += " 1D-CMF FLIPPED NEG (exit rule)"
        if note or (chg is not None and abs(chg) > 3):
            L.append(f"|{s}|{sb}|{fmt(round(chg,1) if chg is not None else None)}|"
                     f"{fmt(round(dcmf,3) if dcmf is not None else None)}|{db_.get('status')}|{note}|")
    return "\n".join(L)
