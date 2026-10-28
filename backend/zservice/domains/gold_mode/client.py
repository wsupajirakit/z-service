"""Gold mode's TradingView fetch, on the shared client (plan B16): a fresh `make_tv()`
instance per request (central login / token / anonymous per tv_login_mode, no socket
shared across threads) and a slot from the global THROTTLE so gold exports and the
auto job never burst TradingView together.

Empty answers do not trip the shared cooldown: some companion symbols legitimately
return nothing, and a trip would pause the stock job for every user.
"""

import contextlib
import time

import pandas as pd

from zservice.integrations.tradingview.client import make_tv
from zservice.integrations.tradingview.throttle import THROTTLE

from .config import _INTERVALS

ATTEMPTS = 2  # TvDatafeed hiccups transiently on single fetches — one retry fixes most
RETRY_PAUSE_S = 1.2


def _fetch_df(symbol: str, exchange: str, tf: str, n_bars: int) -> pd.DataFrame:
    interval, _ = _INTERVALS[tf]
    df = None
    for attempt in range(1, ATTEMPTS + 1):
        df = _get_hist(symbol, exchange, interval, n_bars)
        if df is not None and not df.empty:
            break
        if attempt < ATTEMPTS:
            time.sleep(RETRY_PAUSE_S)
    if df is None or df.empty:
        raise RuntimeError(f"no data for {exchange}:{symbol} {tf}")
    df = df.reset_index().rename(columns={"datetime": "dt"})
    return df[["dt", "open", "high", "low", "close", "volume"]]


def _get_hist(symbol, exchange, interval, n_bars):
    THROTTLE.wait_turn()
    tv = make_tv()
    try:
        return tv.get_hist(symbol=symbol, exchange=exchange, interval=interval, n_bars=n_bars)
    finally:
        with contextlib.suppress(Exception):  # release the throwaway instance's socket
            if getattr(tv, "ws", None) is not None:
                tv.ws.shutdown()
