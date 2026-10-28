"""Global request spacing + rate-limit cooldown for every TradingView call (moved from
main.py; former globals _tv_next_request_at/_tv_cooldown_until/_tv_throttle_lock).

TradingView drops anonymous websocket connections that arrive in rapid bursts (~10
back-to-back trips the limit). Every get_hist across all threads and endpoints reserves a
slot here so requests stay spaced out globally.
"""

import logging
import threading
import time

from zservice.core.job_state import add_log, stop_event

from . import config as tv_config


class Throttle:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.next_request_at = 0.0
        self.cooldown_until = 0.0  # set when repeated empty responses signal a limit trip

    def wait_turn(self) -> None:
        """Reserve the next request slot and sleep until it arrives."""
        with self.lock:
            now = time.monotonic()
            start_at = max(now, self.next_request_at, self.cooldown_until)
            self.next_request_at = start_at + tv_config.get_settings().min_request_interval
        # stop_event stays set between jobs, so waiting on it directly would skip the
        # throttle for API calls. Sleep in chunks and only bail if stop is pressed
        # mid-wait (the job caller re-checks stop_event right after and raises).
        entered_stopped = stop_event.is_set()
        while True:
            remaining = start_at - time.monotonic()
            if remaining <= 0:
                return
            time.sleep(min(remaining, 1.0))
            if not entered_stopped and stop_event.is_set():
                return

    def trip_cooldown(self, symbol: str) -> None:
        seconds = tv_config.get_settings().cooldown_seconds
        with self.lock:
            self.cooldown_until = time.monotonic() + seconds
        add_log(
            f"[{symbol}] Repeated empty responses — cooling down TradingView requests "
            f"for {seconds}s",
            logging.WARNING,
        )

    def cooldown_left(self) -> float:
        return self.cooldown_until - time.monotonic()


THROTTLE = Throttle()
