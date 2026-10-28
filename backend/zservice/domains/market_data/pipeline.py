"""process_symbol: fetch -> ET clock -> session filters -> indicators -> open bar -> records
-> optional store. Each step lives in its own module of this package; this file only
orders them (tests/characterization pins the output on recorded TradingView bars).
"""

import json
from datetime import datetime

from zservice.core.clock import current_tz
from zservice.db.repos import history as history_repo
from zservice.market.bars import resample_to_4h

from .fetch import fetch_frame, is_us_stock
from .indicators import add_indicators
from .open_bar import append_open_bar
from .output import to_records
from .schemas import DataRequest
from .sessions_tag import (
    drop_non_session_bars,
    session_minutes,
    split_open_bar,
    tag_sessions,
    us_schedule,
)


def process_symbol(
    symbol: str,
    exchange: str,
    interval: str,
    extended_session: bool = False,
    rows: int = 40,
    store: bool = True,
):
    """Fetch one symbol, compute indicators, optionally store it in history, return the
    last `rows` bars. Shared by POST /api/data and the fetch jobs; pass store=False (gold
    analysis, the jobs' batch save) to skip writing to the history table."""
    req = DataRequest(
        symbol=symbol,
        exchange=exchange,
        interval=interval,
        extended_session=extended_session,
        rows=rows,
    )
    df = fetch_frame(req)
    us_stock = is_us_stock(req.exchange)
    sched = us_schedule(df, us_stock)
    if req.interval == "4h" and not df.empty:
        df = resample_to_4h(df, sched, us_stock)
    df, open_bar_row = split_open_bar(df, req.symbol, req.interval, req.exchange, sched)
    df = drop_non_session_bars(df, req.interval, us_stock, sched)
    tag_sessions(df, req.interval, us_stock, sched)
    add_indicators(df, req.interval)
    if not df.empty:
        df["is_closed_bar"] = True
    df = append_open_bar(df, open_bar_row, req.interval, us_stock, sched)
    session_minutes(df, req.interval, us_stock, sched)
    result_list = to_records(df, req.rows)
    if store:
        _store_snapshot(req, result_list)
    return result_list


def _store_snapshot(req: DataRequest, result_list: list[dict]) -> None:
    """Upsert on symbol + exchange + interval + extended_session."""
    history_repo.history_upsert(
        req.symbol,
        req.exchange,
        req.interval,
        req.extended_session,
        datetime.now(current_tz()).isoformat(),
        json.dumps(result_list),
    )
