"""Market inputs of the gold analysis: XAUUSD on every timeframe + cross-market closes.

Everything is fetched with store=False so an analysis never writes to the history store.
A failing timeframe or symbol degrades to an "unavailable"/"N/A" slot, never an error.
"""

from fastapi import HTTPException

from zservice.domains.market_data.pipeline import process_symbol
from zservice.domains.market_data.summary import summarize_bars as _summarize_bars

from .config import GOLD_CROSS_MARKET, GOLD_TIMEFRAMES
from .state import gold_stop_event

BARS_24H = 25  # hourly bars spanning 24h: the latest close and the one 24 bars earlier
CROSS_ROWS = 30  # enough 1h bars for the 24h change


def fetch_timeframes(exchange: str, rows: int):
    """(text block per timeframe, bars per timeframe, latest close or None)."""
    tf_blocks, tf_data, latest_price = [], {}, None
    for tf in GOLD_TIMEFRAMES:
        if gold_stop_event.is_set():
            raise Exception("Stopped by user")
        try:
            data = process_symbol(
                "XAUUSD", exchange, tf, extended_session=False, rows=rows, store=False
            )
            tf_data[tf] = data or []
            if data:
                latest_price = data[-1].get("close")
            tf_blocks.append(_summarize_bars(data, tf))
        except HTTPException as e:
            tf_blocks.append(f"[{tf}] (unavailable: {e.detail})")
        except Exception as e:
            tf_blocks.append(f"[{tf}] (error: {e})")
    return tf_blocks, tf_data, latest_price


def fetch_cross_market() -> dict:
    """Latest 1h close and 24h change of DXY, US10Y, VIX and silver (`<key>_change`)."""
    cross = {}
    for cm in GOLD_CROSS_MARKET:
        key = cm["key"]
        try:
            bars = process_symbol(
                cm["symbol"], cm["exchange"], "1h", extended_session=False, rows=CROSS_ROWS,
                store=False,
            )  # fmt: skip
            cross[key] = bars[-1].get("close") if bars else "N/A"
            cross[key + "_change"] = change_24h(bars)
        except Exception as e:
            print(f"[gold] cross-market {cm['symbol']} failed: {e}")
            cross[key] = "N/A"
            cross[key + "_change"] = "N/A"
    return cross


def change_24h(bars) -> str:
    """'+1.23 (+0.45%)' between the latest 1h close and the one 24 bars before (or the
    first bar when there are fewer); 'N/A' without data or a zero base."""
    if not bars:
        return "N/A"
    curr = bars[-1].get("close")
    prev = bars[-BARS_24H].get("close") if len(bars) >= BARS_24H else bars[0].get("close")
    if curr is None or prev is None or prev == 0:
        return "N/A"
    change = curr - prev
    return f"{change:+.2f} ({change / prev * 100:+.2f}%)"
