"""get_hist with retries, a fresh instance per attempt, socket cleanup and the
extended -> regular session fallback."""

import concurrent.futures
import contextlib
import logging

from zservice.core.job_state import add_log, stop_event
from zservice.core.logging import logger

from .client import make_tv
from .throttle import THROTTLE

GET_HIST_TIMEOUT_S = 5
BACKOFF_STEP_S = 2  # attempt n (1-based) waits n * BACKOFF_STEP_S seconds afterwards
EMPTY_DATA = "Empty data returned (possible rate limit or connection drop)"


def get_tv_data_with_retry(
    symbol, exchange, interval_enum, n_bars, extended_session, max_retries=1
):
    last_err = None
    for attempt in range(max_retries + 1):
        _raise_if_stopped()
        THROTTLE.wait_turn()  # global spacing + honor rate-limit cooldown
        _raise_if_stopped()
        df, last_err = _attempt(symbol, exchange, interval_enum, n_bars, extended_session, attempt)
        if df is not None:
            return df
        _raise_if_stopped()
        backoff = BACKOFF_STEP_S * (attempt + 1)  # let a TradingView rate limit cool down
        add_log(f"[{symbol}] Waiting {backoff}s before next retry...", logging.INFO)
        stop_event.wait(backoff)

    # Every attempt came back empty — assume TradingView tripped its rate limit and
    # pause all requests so the next symbols don't burn their retries during the block.
    if last_err and "Empty data" in str(last_err):
        THROTTLE.trip_cooldown(symbol)

    if extended_session:  # retries exhausted with extended hours: one regular-session try
        add_log(
            f"[{symbol}] Exhausted retries with extended=True, trying extended=False",
            logging.WARNING,
        )
        try:
            return get_tv_data_with_retry(
                symbol, exchange, interval_enum, n_bars, False, max_retries=0
            )
        except Exception as e:
            last_err = str(e)
            logger.error(f"[{symbol}] TV fallback with extended=False failed: {e}")

    raise Exception(f"Failed after {max_retries} retries. Last error: {last_err}")


def _raise_if_stopped() -> None:
    if stop_event.is_set():
        raise Exception("Job stopped by user")


def _attempt(symbol, exchange, interval_enum, n_bars, extended_session, attempt):
    """One get_hist on its own instance: (frame, None) or (None, error text).

    Own instance per attempt — see make_tv(): a shared instance gets its socket clobbered
    whenever another endpoint fetches in parallel.
    """
    executor = None
    current_tv = None
    try:
        current_tv = make_tv()
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        df = executor.submit(
            current_tv.get_hist,
            symbol=symbol,
            exchange=exchange,
            interval=interval_enum,
            n_bars=n_bars,
            extended_session=extended_session,
        ).result(timeout=GET_HIST_TIMEOUT_S)
        if df is not None and not df.empty:
            return df, None
        # None/empty: TradingView either dropped the connection or rate-limited us.
        add_log(
            f"[{symbol}] Attempt {attempt + 1} returned empty data. Resetting connection...",
            logging.INFO,
        )
        return None, EMPTY_DATA
    except concurrent.futures.TimeoutError:
        add_log(f"[{symbol}] Timeout on attempt {attempt + 1}", logging.WARNING)
        return None, "Timeout"
    except Exception as e:
        add_log(f"[{symbol}] Error on attempt {attempt + 1}: {e}", logging.ERROR)
        return None, str(e)
    finally:
        if executor:
            executor.shutdown(wait=False, cancel_futures=True)
        # Always release the throwaway instance's socket. A timed-out get_hist keeps
        # running in its abandoned executor thread and holds its websocket open for a
        # minute or more; TradingView counts those zombies against the connection limit,
        # so each stall makes the next request likelier to be dropped. Killing the socket
        # makes the zombie thread error out at once and frees the slot.
        with contextlib.suppress(Exception):
            if current_tv is not None and getattr(current_tv, "ws", None) is not None:
                current_tv.ws.shutdown()
