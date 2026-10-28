"""Stock radar scan: technical blocks per symbol x timeframe, optional macro headlines, then
either a Gemini ranking ("ai") or the raw blocks ("logic"); saved to history and sent to
Telegram when enabled. Rewritten from main.py into small functions with byte-identical
prompt / output / Telegram text (pinned by tests/characterization/test_scans_golden.py).

The Telegram text is HTML-escaped (plan item B15, fixed).
"""

import concurrent.futures
import html
import json
import logging
import urllib.request
from datetime import datetime

import feedparser

from zservice.core.clock import current_tz
from zservice.core.errors import ApiError
from zservice.db.repos import scans as scans_repo
from zservice.domains.market_data.pipeline import process_symbol
from zservice.domains.market_data.summary import summarize_bars as _summarize_bars
from zservice.domains.settings.service import get_dest_setting
from zservice.integrations.gemini import call_gemini as _call_gemini
from zservice.integrations.telegram import send_telegram_message
from zservice.integrations.tradingview.intervals import INTERVAL_MAP

from .schemas import StockRadarRequest

log = logging.getLogger("zs.stock_radar")

BARS_PER_TIMEFRAME = 40
TELEGRAM_ANALYSIS_LIMIT = 3000
TELEGRAM_MAX_CHARS = 4000  # Telegram's hard limit is 4096
_NEWS_TRIGGERS = ("CORE_RADAR", "Macro", "Core Radar")
_NEWS_PER_FEED = 3
# This scan's own short headline list (different feeds/format from integrations/news.py).
_NEWS_FEEDS = [
    {
        "name": "CNBC",
        "url": "https://search.cnbc.com/rs/search/combinedcms/view.xml"
        "?partnerId=wrss01&id=100727362",
    },
    {"name": "MarketWatch", "url": "https://feeds.content.dowjones.io/public/rss/mw_topstories"},
    {"name": "Investing", "url": "https://www.investing.com/rss/news_14.rss"},
]
_PROMPT_ROLE = "You are a professional stock analyst (Stock Radar).\n"
_PROMPT_TASK = "Your task is to analyse and rank these stocks: "
_PROMPT_FORMULAS = "using these scan formulas:\n"
_PROMPT_NEWS = "## Latest news (Macro/Core Radar)\n"
_PROMPT_DATA = "## Technical data\n"
_PROMPT_ASK = (
    "\n\nSummarise and rank each stock by how attractive it is, based on the data and the "
    "selected formulas. Format the result as easy-to-read Markdown. Answer in English."
)
_LOGIC_HEADER = "## Logic Match (Raw Technical Data Bypass)\n\n"
_LOGIC_NOTE = (
    "\n\n*Note: Logic matching algorithms are currently not hardcoded. "
    "This mode bypasses the AI and returns the raw computed indicators.*"
)


def run_scan(req: StockRadarRequest) -> dict:
    news_lines = scan_news(req.formulas)
    data_blocks = [b for b in (symbol_block(s, req) for s in req.symbols) if b is not None]
    if req.analysis_mode == "logic":
        analysis = logic_report(news_lines, data_blocks)
    else:
        prompt = build_prompt(req, news_lines, data_blocks)
        try:
            analysis = _call_gemini(req.model, prompt)
        except Exception as e:
            raise ApiError(
                500, "ai.failed", f"Gemini AI error: {e}", params={"reason": str(e)}
            ) from e
    stamp = datetime.now(current_tz()).isoformat()
    _save(req, stamp, analysis)
    _notify(req, analysis)
    return {"analysis": analysis, "timestamp": stamp}


def scan_news(formulas: list[str]) -> list[str]:
    """Headlines only when a macro / Core Radar formula is selected."""
    if not any(t in f for f in formulas for t in _NEWS_TRIGGERS):
        return []
    lines: list[str] = []
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            for res in executor.map(_feed_headlines, _NEWS_FEEDS):
                lines.extend(res)
    except Exception as e:
        lines.append(f"Error fetching news: {e}")
    return lines


def _feed_headlines(feed: dict) -> list[str]:
    try:
        req = urllib.request.Request(feed["url"], headers={"User-Agent": "Mozilla/5.0"})  # noqa: S310
        with urllib.request.urlopen(req, timeout=3) as resp:  # noqa: S310 — fixed https feeds
            parsed = feedparser.parse(resp.read())
    except Exception:
        return []  # one dead feed must not drop the others
    return [
        f"{feed['name']}: {e.get('title', '')} ({e.get('published', '')})"
        for e in parsed.entries[:_NEWS_PER_FEED]
    ]


def symbol_block(sym_obj: dict, req: StockRadarRequest) -> str | None:
    sym, exc = sym_obj.get("symbol"), sym_obj.get("exchange")
    if not sym or not exc:
        return None
    lines = [f"### Data for {sym} ({exc})"]
    for tf in req.timeframes:
        if tf.lower() not in INTERVAL_MAP:
            continue
        try:
            bars = process_symbol(
                sym, exc, tf.lower(), req.extended_session, BARS_PER_TIMEFRAME, store=False
            )
            lines.append(f"**{tf.upper()} Timeframe:**\n{_summarize_bars(bars, tf.lower())}")
        except Exception as e:
            lines.append(
                f"**{tf.upper()} Timeframe:** Error fetching data ({type(e).__name__}: {e!s})"
            )
    return "\n".join(lines)


def _symbols(req: StockRadarRequest) -> str:
    return ", ".join([s.get("symbol", "") for s in req.symbols])


def build_prompt(req: StockRadarRequest, news_lines: list[str], data_blocks: list[str]) -> str:
    prompt = _PROMPT_ROLE + f"{_PROMPT_TASK}{_symbols(req)}\n"
    prompt += _PROMPT_FORMULAS + "\n".join(["- " + f for f in req.formulas]) + "\n\n"
    if news_lines:
        prompt += _PROMPT_NEWS + "\n".join(news_lines) + "\n\n"
    prompt += _PROMPT_DATA + "\n\n".join(data_blocks)
    return prompt + _PROMPT_ASK


def logic_report(news_lines: list[str], data_blocks: list[str]) -> str:
    """Raw technical blocks without the AI."""
    report = _LOGIC_HEADER
    if news_lines:
        report += "### Recent News\n" + "\n".join(news_lines) + "\n\n"
    return report + "\n\n".join(data_blocks) + _LOGIC_NOTE


def _save(req: StockRadarRequest, stamp: str, analysis: str) -> None:
    try:
        scans_repo.radar_add(
            stamp,
            json.dumps(req.symbols),
            json.dumps(req.formulas),
            json.dumps(req.timeframes),
            req.extended_session,
            analysis,
        )
    except Exception as e:
        log.error("Error saving to stock_radar_history: %s", e)


def _notify(req: StockRadarRequest, analysis: str) -> None:
    if not get_dest_setting().get("dest_stock_telegram", False):
        return
    try:
        send_telegram_message(telegram_text(req, analysis))
    except Exception as e:
        log.error("Telegram error: %s", e)


def telegram_text(req: StockRadarRequest, analysis: str) -> str:
    """HTML-mode Telegram text (send_telegram_message uses parse_mode=HTML): every dynamic
    part is escaped, so AI output with '<' or '&' can no longer make Telegram reject the
    message (plan B15). The analysis is cut before escaping so no entity is split."""

    def esc(text: str) -> str:
        return html.escape(text, quote=False)

    head = (
        "📡 <b>Stock Radar Scan Completed</b>\n"
        f"Symbols: {esc(_symbols(req))}\n"
        f"Formulas: {esc(', '.join(req.formulas))}\n"
        f"Timeframes: {esc(', '.join(req.timeframes))}\n\n"
    )
    body = esc(analysis[:TELEGRAM_ANALYSIS_LIMIT])
    if len(head) + len(body) > TELEGRAM_MAX_CHARS:  # many '&' / '<' expand when escaped
        body = esc(analysis[: TELEGRAM_ANALYSIS_LIMIT // 2])
    return head + body


def history(limit: int) -> list[dict]:
    def loads(r: dict, key: str) -> list:
        return json.loads(r[key]) if r.get(key) else []

    return [
        {
            "id": r["id"],
            "timestamp": r["timestamp"],
            "symbols": loads(r, "symbols"),
            "formulas": loads(r, "formulas"),
            "timeframes": loads(r, "timeframes"),
            "extended_session": bool(r.get("extended_session")),
            "result_markdown": r.get("result_markdown"),
        }
        for r in scans_repo.radar_list(limit)
    ]
