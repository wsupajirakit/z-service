"""US-stock exchange check via TradingView symbol search, cached per symbol (moved
unchanged from main.py)."""

import json
import logging
import threading
import urllib.parse
import urllib.request

from zservice.core.job_state import add_log
from zservice.core.logging import logger

_EXCHANGE_CACHE: dict[str, str | None] = {}
_EXCHANGE_LOCK = threading.Lock()


def resolve_tv_exchange(symbol, exchange):
    """Validate/correct a US stock's exchange via TradingView's symbol search.

    A wrong EXCHANGE:SYMBOL pair (e.g. NYSE:ITRN for a NASDAQ stock) never gets
    a series response — heartbeats keep the websocket alive so the fetch idles
    until the 35s timeout, and every retry repeats it (~4 min burned per bad
    symbol). One cached HTTP lookup prevents that and auto-heals stale exchange
    data coming from the UI's symbol list or watchlists."""
    key = symbol.upper().strip()
    with _EXCHANGE_LOCK:
        if key in _EXCHANGE_CACHE:
            resolved = _EXCHANGE_CACHE[key]
            return resolved if resolved and resolved != exchange else exchange
    try:
        url = (
            "https://symbol-search.tradingview.com/symbol_search/"
            f"?text={urllib.parse.quote(key)}&hl=0&lang=en&domain=production"
        )
        http_req = urllib.request.Request(  # noqa: S310 — fixed https search URL
            url,
            headers={
                "Origin": "https://www.tradingview.com",
                "Referer": "https://www.tradingview.com/",
                "User-Agent": "Mozilla/5.0",
            },
        )
        with urllib.request.urlopen(http_req, timeout=8) as resp:  # noqa: S310
            data = json.loads(resp.read())
        matches = [
            d
            for d in data
            if d.get("symbol") == key
            and d.get("country") == "US"
            and d.get("exchange") in ("NASDAQ", "NYSE", "AMEX")
        ]
        matches.sort(key=lambda d: not d.get("is_primary_listing", False))
        resolved = matches[0]["exchange"] if matches else None
    except Exception as e:
        # Search being down must never block fetching — use the exchange as-is
        # and don't cache, so the next call retries the lookup.
        logger.warning(f"[{key}] exchange lookup failed ({e}) — using '{exchange}' as-is")
        return exchange
    with _EXCHANGE_LOCK:
        _EXCHANGE_CACHE[key] = resolved
    if resolved and resolved != exchange:
        add_log(
            f"[{key}] exchange '{exchange}' is not the listing exchange — using '{resolved}'"
            " (auto-corrected)",
            logging.WARNING,
        )
        return resolved
    return exchange
