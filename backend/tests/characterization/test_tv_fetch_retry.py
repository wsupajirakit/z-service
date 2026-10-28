"""Characterization of get_tv_data_with_retry before it is split.

The client, throttle, stop event and job log are faked: each case scripts what every
get_hist call returns and pins the result, the job log, retries/backoffs, cooldown trips
and socket cleanup.
"""

import concurrent.futures
from types import SimpleNamespace

import pandas as pd
import pytest

from zservice.integrations.tradingview import fetch

from .golden import check


class World:
    def __init__(self, script, stop_at=None):
        self.script, self.stop_at = list(script), stop_at
        self.events, self.checks = [], 0

    # stop_event
    def is_set(self):
        self.checks += 1
        return self.checks == self.stop_at

    def wait(self, seconds):
        self.events.append(f"backoff {seconds}")

    # throttle
    def wait_turn(self):
        self.events.append("wait_turn")

    def trip_cooldown(self, symbol):
        self.events.append(f"trip {symbol}")

    def make_tv(self):
        world = self

        class Tv:
            ws = SimpleNamespace(shutdown=lambda: world.events.append("ws closed"))

            def get_hist(self, symbol, exchange, interval, n_bars, extended_session):
                kind = world.script.pop(0)
                world.events.append(f"get_hist ext={extended_session} -> {kind}")
                if kind == "timeout":
                    raise concurrent.futures.TimeoutError()
                if kind == "raise":
                    raise ConnectionError("boom")
                if kind == "none":
                    return None
                return pd.DataFrame({"close": [1.0, 2.0]}) if kind == "ok" else pd.DataFrame()

        return Tv()


CASES = {
    "ok_first_try": (["ok"], False, None),
    "empty_then_ok": (["empty", "ok"], False, None),
    "none_none_fallback_ok": (["none", "empty", "ok"], True, None),
    "timeout_then_error": (["timeout", "raise"], False, None),
    "empty_everywhere_with_fallback": (["empty", "empty", "empty"], True, None),
    "stopped_before_first_try": (["ok"], False, 1),
    "stopped_after_throttle_wait": (["ok"], False, 2),
    "stopped_after_failed_try": (["empty"], False, 3),
}


@pytest.mark.parametrize("case", sorted(CASES))
def test_get_tv_data_with_retry(monkeypatch, case):
    script, extended, stop_at = CASES[case]
    world = World(script, stop_at)
    logs = []
    fakes = {
        "stop_event": world,
        "THROTTLE": world,
        "make_tv": world.make_tv,
        "add_log": lambda msg, level: logs.append([level, msg]),
        "logger": SimpleNamespace(error=lambda msg: logs.append(["logger.error", msg])),
    }
    for name, value in fakes.items():
        monkeypatch.setitem(fetch.__dict__, name, value)
    try:
        df = fetch.get_tv_data_with_retry("SYM", "NASDAQ", "1h", 2, extended, max_retries=1)
        outcome = {"rows": len(df)}
    except Exception as e:
        outcome = {"error": str(e)}
    check(
        f"tv_fetch_retry_{case}",
        {"outcome": outcome, "events": world.events, "logs": logs, "unused": world.script},
    )
