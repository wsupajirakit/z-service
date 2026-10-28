"""Step 1 of the pipeline: fetch raw bars from TradingView and put them on the ET clock."""

import contextlib

import pandas as pd
from dateutil import tz as dateutil_tz

from zservice.core.errors import ApiError
from zservice.integrations.tradingview.exchanges import resolve_tv_exchange
from zservice.integrations.tradingview.fetch import get_tv_data_with_retry
from zservice.integrations.tradingview.intervals import INTERVAL_MAP
from zservice.market.sessions import US_STOCK_EXCHANGES

from .schemas import DataRequest

MIN_FETCH_BARS = 300
EXTRA_FETCH_BARS = 200  # warm-up bars so long EMAs settle before the rows returned


def fetch_frame(req: DataRequest) -> pd.DataFrame:
    """Raw OHLCV for the request (1h bars for a 4h request), index in America/New_York."""
    if req.interval not in INTERVAL_MAP:
        raise ApiError(
            400,
            "market.invalid_interval",
            "Invalid interval. Use 15m, 1h, 1d, or 1w.",
            params={"allowed": "15m, 1h, 1d, 1w"},
        )
    is_4h = req.interval == "4h"
    query_interval_enum = INTERVAL_MAP["1h"] if is_4h else INTERVAL_MAP[req.interval]

    # tvDatafeed expects 'AMEX' or 'NYSE' instead of 'NYSE Arca' for Arca-listed ETFs
    query_exchange = req.exchange
    if query_exchange.upper() == "NYSE ARCA":
        query_exchange = "AMEX"
    # US stocks only: verify the pair before fetching so a wrong exchange can
    # never stall the job. Non-stock namespaces (TVC, OANDA, BINANCE...) pass through.
    if query_exchange.upper() in ("NASDAQ", "NYSE", "AMEX"):
        query_exchange = resolve_tv_exchange(req.symbol, query_exchange.upper())

    try:
        bars = max(MIN_FETCH_BARS, req.rows + EXTRA_FETCH_BARS)
        fetch_bars = bars * 4 if is_4h else bars
        df = get_tv_data_with_retry(
            req.symbol,
            query_exchange,
            query_interval_enum,
            fetch_bars,
            req.extended_session,
            max_retries=1,
        )
    except Exception as e:
        raise ApiError(
            500,
            "market.fetch_failed",
            f"Error fetching data from TradingView: {e!s}",
            params={"reason": str(e)},
        ) from e

    if df is None or df.empty:
        raise ApiError(
            404,
            "market.no_data",
            "No data returned from TradingView. Please check the symbol and exchange.",
        )
    return _to_eastern(df)


def _to_eastern(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure a DatetimeIndex in America/New_York."""
    if not isinstance(df.index, pd.DatetimeIndex):
        with contextlib.suppress(Exception):
            df.index = pd.to_datetime(df.index)

    if isinstance(df.index, pd.DatetimeIndex):
        if df.index.tz is None:
            # tvDatafeed builds timestamps with datetime.fromtimestamp() -> naive
            # wall time in the *server's* system timezone (UTC inside the Coolify
            # container, UTC+7 on the dev Mac). Localize with the real system zone
            # via dateutil tzlocal — NOT current_tz(), which is only the display
            # setting and shifted every bar by 7h when the server ran on UTC
            # (sessions/IPI were then computed on the wrong clock).
            df.index = df.index.tz_localize(dateutil_tz.tzlocal()).tz_convert("America/New_York")
        else:
            df.index = df.index.tz_convert("America/New_York")
    return df


def is_us_stock(exchange: str) -> bool:
    return exchange.upper() in US_STOCK_EXCHANGES
