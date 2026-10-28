"""Characterization of the TradingView self-test (/api/tv/test) before it is split.

The clock, the probe client, the auth state and the throttle are faked, so every branch
(auth mode, cooldown, probe outcome, verdict) is deterministic and offline.
"""

import base64
import concurrent.futures
import json
from datetime import UTC
from types import SimpleNamespace

import pandas as pd
import pytest

from zservice.domains.tradingview import service

from .golden import check

NOW = 1_800_000_000.0


class Clock:
    def __init__(self):
        self.t = NOW

    def time(self):
        return self.t

    def sleep(self, seconds):
        self.t += seconds


def _jwt(exp: float) -> str:
    body = base64.urlsafe_b64encode(json.dumps({"exp": exp}).encode()).decode().rstrip("=")
    return f"h.{body}.s"


def _probe_tv(clock, outcomes):
    """outcomes[symbol] = (seconds taken, 'ok' | 'empty' | 'raise' | 'timeout')."""

    class Tv:
        ws = SimpleNamespace(shutdown=lambda: None)

        def get_hist(self, symbol, exchange, interval, n_bars, extended_session):
            secs, kind = outcomes[symbol]
            clock.t += secs
            if kind == "timeout":
                raise concurrent.futures.TimeoutError()
            if kind == "raise":
                raise ConnectionError("socket closed")
            return pd.DataFrame({"close": [1.0] * n_bars}) if kind == "ok" else pd.DataFrame()

    return Tv


CASES = {
    "login_ok_fast": dict(
        env={"TV_USERNAME": "u1"}, active="LOGIN", state_tok="LOGIN", exp=NOW + 600,
        cooldown=0, outcomes={"AAPL": (1, "ok"), "XAUUSD": (2, "ok")},
    ),
    "login_failed_token_valid_slow": dict(
        env={"TV_USERNAME": "u1", "TV_AUTH_TOKEN": _jwt(NOW + 3600)}, active=_jwt(NOW + 3600),
        state_tok=None, exp=None, cooldown=0,
        outcomes={"AAPL": (6, "ok"), "XAUUSD": (1, "ok")},
    ),
    "token_expired_partial": dict(
        env={"TV_AUTH_TOKEN": _jwt(NOW - 120)}, active=_jwt(NOW - 120), state_tok=None,
        exp=None, cooldown=42, outcomes={"AAPL": (1, "ok"), "XAUUSD": (3, "empty")},
    ),
    "token_unreadable_all_fail": dict(
        env={"TV_AUTH_TOKEN": "not-a-jwt"}, active="not-a-jwt", state_tok=None, exp=None,
        cooldown=0, outcomes={"AAPL": (1, "raise"), "XAUUSD": (25, "timeout")},
    ),
    "anonymous_after_login_failed": dict(
        env={"TV_USERNAME": "u1"}, active=None, state_tok=None, exp=None, cooldown=0,
        outcomes={"AAPL": (1, "ok"), "XAUUSD": (1, "ok")},
    ),
    "anonymous": dict(
        env={}, active=None, state_tok=None, exp=None, cooldown=0,
        outcomes={"AAPL": (1, "ok"), "XAUUSD": (1, "ok")},
    ),
}  # fmt: skip


@pytest.mark.parametrize("case", sorted(CASES))
def test_connection_test(monkeypatch, env, case):
    c = CASES[case]
    clock = Clock()
    env(**{name: c["env"].get(name) for name in ("TV_USERNAME", "TV_AUTH_TOKEN")})
    put = {
        "time": clock,
        "current_tz": lambda: UTC,
        "make_tv": _probe_tv(clock, c["outcomes"]),
        "current_auth_token": lambda: c["active"],
        "STATE": SimpleNamespace(token=c["state_tok"], exp=c["exp"]),
        "THROTTLE": SimpleNamespace(cooldown_left=lambda: c["cooldown"]),
    }
    for name, value in put.items():
        monkeypatch.setitem(service.__dict__, name, value)
    result = service.connection_test()
    for entry in result["logs"]:
        assert len(entry.pop("time")) == 8  # HH:MM:SS wall clock
    check(f"tv_connection_test_{case}", result)
