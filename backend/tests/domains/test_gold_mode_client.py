"""Gold mode fetches go through the shared TradingView client and throttle (plan B16)."""

from types import SimpleNamespace

import pandas as pd
import pytest

from zservice.domains.gold_mode import client


@pytest.fixture
def world(monkeypatch):
    w = SimpleNamespace(answers=[], events=[])

    def make_tv():
        def get_hist(symbol, exchange, interval, n_bars):
            w.events.append(f"get_hist {exchange}:{symbol} {n_bars}")
            return w.answers.pop(0)

        ws = SimpleNamespace(shutdown=lambda: w.events.append("ws closed"))
        return SimpleNamespace(get_hist=get_hist, ws=ws)

    throttle = SimpleNamespace(
        wait_turn=lambda: w.events.append("slot"),
        trip_cooldown=lambda s: w.events.append("TRIP"),
    )
    monkeypatch.setattr(client, "make_tv", make_tv)
    monkeypatch.setattr(client, "THROTTLE", throttle)
    monkeypatch.setattr(client.time, "sleep", lambda s: w.events.append(f"sleep {s}"))
    return w


def _frame():
    idx = pd.DatetimeIndex(["2026-10-23 10:00", "2026-10-23 11:00"], name="datetime")
    cols = {k: [1.0, 2.0] for k in ("open", "high", "low", "close", "volume")}
    return pd.DataFrame({"symbol": ["X", "X"], **cols}, index=idx)


def test_each_attempt_takes_a_throttle_slot_and_a_fresh_instance(world):
    world.answers = [pd.DataFrame(), _frame()]
    df = client._fetch_df("XAUUSD", "OANDA", "1h", 50)
    assert list(df.columns) == ["dt", "open", "high", "low", "close", "volume"]
    assert world.events == [
        "slot", "get_hist OANDA:XAUUSD 50", "ws closed", "sleep 1.2",
        "slot", "get_hist OANDA:XAUUSD 50", "ws closed",
    ]  # fmt: skip


def test_empty_twice_raises_without_tripping_the_shared_cooldown(world):
    world.answers = [None, pd.DataFrame()]
    with pytest.raises(RuntimeError, match=r"no data for TVC:DXY 15m"):
        client._fetch_df("DXY", "TVC", "15m", 30)
    assert "TRIP" not in world.events and world.events.count("ws closed") == 2
