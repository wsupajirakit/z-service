"""POST /api/data stores the fetched snapshot (default store=True).

Regression: the `store` parameter of process_symbol shadowed the `store` module, so with
store=True the call `history_repo.history_upsert(...)` ran on a bool and raised AttributeError —
every POST /api/data answered 500. The internal jobs pass store=False, so only the
single-symbol fetch was affected.
"""

import inspect
import json
import types
from datetime import UTC
from pathlib import Path

import pandas as pd

FIXTURES = Path(__file__).parents[1] / "characterization" / "fixtures"


def test_store_true_writes_history(monkeypatch):
    from zservice.domains.market_data.pipeline import process_symbol as fn

    g = inspect.getmodule(fn).__dict__
    frame = pd.read_csv(FIXTURES / "tv_spy_1d.csv.gz", index_col=0, parse_dates=True)
    calls = []
    fake_store = types.SimpleNamespace(history_upsert=lambda *a: calls.append(a))
    monkeypatch.setitem(g, "get_tv_data_with_retry", lambda *a, **k: frame.copy())
    monkeypatch.setitem(g, "resolve_tv_exchange", lambda symbol, exchange: exchange)
    monkeypatch.setitem(g, "history_repo", fake_store)
    monkeypatch.setitem(g, "current_tz", lambda: UTC)
    out = fn("SPY", "AMEX", "1d", rows=5)
    assert len(calls) == 1
    symbol, exchange, interval, extended, _stamp, payload = calls[0]
    assert (symbol, exchange, interval, extended) == ("SPY", "AMEX", "1d", False)
    assert json.loads(payload) == json.loads(json.dumps(out))


def test_stock_radar_telegram_text_is_html_safe():
    from zservice.domains.stock_radar.schemas import StockRadarRequest
    from zservice.domains.stock_radar.service import telegram_text

    req = StockRadarRequest(
        symbols=[{"symbol": "A&B", "exchange": "X"}], formulas=["<f>"], timeframes=["1d"], model="m"
    )
    text = telegram_text(req, "buy if price < 10 & rsi > 50")
    assert text.startswith("📡 <b>Stock Radar Scan Completed</b>")
    assert "A&amp;B" in text and "&lt;f&gt;" in text and "price &lt; 10 &amp; rsi" in text
    assert "<f>" not in text
