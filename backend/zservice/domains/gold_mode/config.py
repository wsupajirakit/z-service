"""Gold mode configuration: intervals, sources, companion symbols, modes, news feeds
(moved unchanged from backend/gold.py)."""

import json
from datetime import timedelta
from pathlib import Path

from tvDatafeed import Interval

# --------------------------------------------------------------------------
# intervals (own map — includes 5m which the stock flow doesn't use)
# --------------------------------------------------------------------------
_INTERVALS = {
    "5m": (Interval.in_5_minute, timedelta(minutes=5)),
    "15m": (Interval.in_15_minute, timedelta(minutes=15)),
    "30m": (Interval.in_30_minute, timedelta(minutes=30)),
    "1h": (Interval.in_1_hour, timedelta(hours=1)),
    "4h": (Interval.in_4_hour, timedelta(hours=4)),
    "1d": (Interval.in_daily, timedelta(days=1)),
    "1w": (Interval.in_weekly, timedelta(weeks=1)),
}


_XAU_EXCHANGES = ["ICMARKETS", "OANDA", "FOREXCOM"]  # whitelist; first = default


# companions: fixed exchanges (same sources as the dash symbol list)
_COMP_EXCH = {
    "DXY": "TVC",
    "US10Y": "TVC",
    "VIX": "TVC",
    "SPY": "AMEX",
    "WTI": "BLACKBULL",
    "BTCUSDT": "BINANCE",
    "USDJPY": "OANDA",
    "XAGUSD": "OANDA",
    "GDX": "AMEX",
}


# mode -> ttl seconds, news item limit, min R:R, sets of (symbol, tf, n_bars), plus the
# analyst instructions. The definitions are data (gold_modes.json), not code.
GOLD_MODES: dict = json.loads(
    Path(__file__).with_name("gold_modes.json").read_text(encoding="utf-8")
)["modes"]


# --------------------------------------------------------------------------
# news (own fetch — same public feeds as the stock flow, no import from main)
# --------------------------------------------------------------------------
_NEWS_FEEDS = [
    {
        "name": "CNBC (World)",
        "url": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100727362",
    },
    {"name": "Investing.com", "url": "https://www.investing.com/rss/news_14.rss"},
    {
        "name": "MarketWatch Top",
        "url": "https://feeds.content.dowjones.io/public/rss/mw_topstories",
    },
    {
        "name": "NYT Business (US)",
        "url": "https://rss.nytimes.com/services/xml/rss/nyt/Business.xml",
    },
]
