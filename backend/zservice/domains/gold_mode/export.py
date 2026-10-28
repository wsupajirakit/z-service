"""Gold mode CSV builders: per-symbol data files, news and gold_formula.csv (moved
unchanged from backend/gold.py)."""

import concurrent.futures
import csv
import io
import json
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import feedparser
import pandas as pd

from .config import _INTERVALS, _NEWS_FEEDS, GOLD_MODES
from .indicators import _enrich


def _meta_lines(mode: str, exchange: str, symbol: str, tf: str, last_dt) -> list:
    now_utc = datetime.now(UTC)
    et = now_utc.astimezone(ZoneInfo("America/New_York"))
    bkk = now_utc.astimezone(ZoneInfo("Asia/Bangkok"))
    return [
        f"# gold_mode: {mode} | symbol: {symbol} | tf: {tf} | exchange: {exchange}",
        f"# generated_utc: {now_utc.strftime('%Y-%m-%dT%H:%M:%SZ')} | et: "
        f"{et.strftime('%Y-%m-%d %H:%M')} | bangkok: {bkk.strftime('%Y-%m-%d %H:%M')}",
        f"# last_bar_start: {last_dt}",
        "# volume_note: CFD/FX volume = TICK VOLUME (proxy) — CMF/OBV/RVOL อ่านเชิงเปรียบเทียบ "
        "ไม่ใช่เงินสถาบันแบบหุ้น",
        "# session_note: metals ~23h/day (ปิด 17:00-18:00 ET + สุดสัปดาห์) — "
        "แท่งสุดท้ายอาจยังไม่ปิด (ดูคอลัมน์ Is_Closed_Bar)",
    ]


COLUMNS = [
    "Symbol", "Datetime", "Open", "High", "Low", "Close", "Volume", "EMA_20", "EMA_50",
    "EMA_100", "EMA_200", "RSI", "OBV", "CMF_50", "CMF_20", "VWAP_20", "ATR_14", "RVOL_20",
    "Is_Closed_Bar",
]  # fmt: skip
# (enriched column, decimals) after Symbol/Datetime, in file order; None = int.
_VALUES = [
    ("open", 3), ("high", 3), ("low", 3), ("close", 3), ("volume", None), ("ema20", 3),
    ("ema50", 3), ("ema100", 3), ("ema200", 3), ("rsi", 1), ("obv", None), ("cmf50", 4),
    ("cmf20", 4), ("vwap20", 3), ("atr14", 3), ("rvol20", 2),
]  # fmt: skip


def _symbol_csv(mode: str, exchange: str, symbol: str, tf: str, df: pd.DataFrame) -> bytes:
    df = _enrich(df)
    _, dur = _INTERVALS[tf]
    now_utc = datetime.now(UTC).replace(tzinfo=None)
    buf = io.StringIO()
    for line in _meta_lines(mode, exchange, symbol, tf, df["dt"].iloc[-1]):
        buf.write(line + "\r\n")
    w = csv.writer(buf)
    w.writerow(COLUMNS)
    last_idx = len(df) - 1
    for i, r in df.iterrows():
        bar_start = pd.Timestamp(r["dt"]).to_pydatetime().replace(tzinfo=None)
        # Only the newest bar can still be forming.
        is_closed = not (i == last_idx and (now_utc - bar_start) < dur)
        values = [int(r[c]) if nd is None else round(r[c], nd) for c, nd in _VALUES]
        w.writerow([symbol, r["dt"], *values, is_closed])
    return buf.getvalue().encode("utf-8-sig")


def _fetch_news(limit: int) -> list:
    def one(feed):
        try:
            req = urllib.request.Request(  # noqa: S310 — fixed https feeds
                feed["url"], headers={"User-Agent": "Mozilla/5.0"}
            )
            with urllib.request.urlopen(req, timeout=3) as resp:  # noqa: S310
                d = feedparser.parse(resp.read())
            return [
                {
                    "source": feed["name"],
                    "title": e.get("title", ""),
                    "pubDate": e.get("published", e.get("updated", "")),
                    "link": e.get("link", ""),
                }
                for e in d.entries[:10]
            ]
        except Exception:
            return []

    items = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
        for chunk in ex.map(one, _NEWS_FEEDS):
            items.extend(chunk)
    return items[:limit]


# gold_formula.csv: instruction block for the analyst AI. The text is data
# (gold_formula.json, str.format templates); only the news rows are built per request.
_FORMULA = json.loads(Path(__file__).with_name("gold_formula.json").read_text(encoding="utf-8"))


def _formula_csv(mode: str, exchange: str) -> bytes:
    spec = GOLD_MODES[mode]
    fields = {**spec, "mode": mode, "exchange": exchange}
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(_FORMULA["header"])
    for key, template in _FORMULA["analysis_request"]:
        w.writerow(["ANALYSIS_REQUEST", "", key, template.format(**fields)])
    # entry playbook per mode — distilled from session/liquidity/trend-pullback
    # research on XAUUSD (see docs/gold-mode-design.md references)
    for i, play in enumerate(spec["playbook"], 1):
        w.writerow(["ENTRY_PLAYBOOK", "", f"{mode} #{i}", play])
    for key, val in _FORMULA["session_map"]:
        w.writerow(["SESSION_MAP", "", key, val.format(**fields)])
    for key, template in _FORMULA["reading_guide"]:
        w.writerow(["READING_GUIDE", "", key, template.format(**fields)])
    for n in _fetch_news(spec["news"]):
        value = f"{n['pubDate']}, {n['title']}, {n['link']}"
        w.writerow(["LATEST_FINANCIAL_NEWS", "", n["source"], value])
    return buf.getvalue().encode("utf-8-sig")
