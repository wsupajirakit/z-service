"""Characterization of the stock radar scan and the earnings scan before they move.

All outside calls are faked in the defining module: process_symbol, Gemini, RSS (urlopen +
feedparser), the store, Telegram, the earnings HTTP helper. Pins the exact prompt, the
logic-mode output and each earnings provider's parsed result.
"""

import hashlib
import inspect
import json
import types
import urllib.request

import feedparser
import pytest

from zservice.domains.earning_scan import providers
from zservice.domains.stock_radar import schemas as radar_schemas
from zservice.domains.stock_radar import service as radar_service

from .golden import check


class _Resp:
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self):
        return b"<rss/>"


def _bars(sym, tf):
    return [
        {
            "datetime": f"2026-10-23 1{i}:00:00",
            "open": 10 + i,
            "high": 11 + i,
            "low": 9 + i,
            "close": 10.5 + i,
            "volume": 1000 * (i + 1),
            "EMA_20": 10,
            "EMA_50": 9,
            "EMA_200": 8,
            "RSI": 55.5,
            "CMF": 0.123,
            "IPI": 12.3,
            "IPI_Status": "Neutral",
            "FVG": None,
        }
        for i in range(3)
    ]


@pytest.fixture
def scan(main_module, monkeypatch):
    m = main_module
    sent = {"telegram": [], "saved": []}
    g = inspect.getmodule(radar_service.run_scan).__dict__

    def gemini(model, prompt):
        sent["prompt"] = prompt
        return "ranked"

    for name, value in {
        "process_symbol": lambda sym, exc, tf, ext, rows, store=False: _bars(sym, tf),
        "_call_gemini": gemini,
        "send_telegram_message": lambda text: sent["telegram"].append(text),
        "get_dest_setting": lambda: {"dest_stock_telegram": True},
        "current_tz": lambda: __import__("datetime").UTC,
    }.items():
        if name in g:
            monkeypatch.setitem(g, name, value)
    from zservice.db.repos import scans as scans_repo

    monkeypatch.setattr(scans_repo, "radar_add", lambda *a: sent["saved"].append(a))
    monkeypatch.setattr(urllib.request, "urlopen", lambda req, timeout=3: _Resp())
    entries = [{"title": f"t{i}", "published": f"p{i}"} for i in range(5)]
    monkeypatch.setattr(feedparser, "parse", lambda c: types.SimpleNamespace(entries=entries))
    return m, sent


def test_stock_radar_ai_prompt(scan):
    _m, sent = scan
    req = radar_schemas.StockRadarRequest(
        symbols=[{"symbol": "AAA", "exchange": "NASDAQ"}, {"symbol": "BBB", "exchange": "NYSE"}],
        formulas=["CORE_RADAR v2", "UIPT"],
        timeframes=["1D", "1h", "bogus"],
        model="m",
    )
    out = radar_service.run_scan(req)
    assert out["analysis"] == "ranked" and len(sent["saved"]) == 1
    check(
        "stock_radar_ai",
        {
            "prompt_sha256": hashlib.sha256(sent["prompt"].encode()).hexdigest(),
            "prompt_chars": len(sent["prompt"]),
            "telegram_sha256": hashlib.sha256(sent["telegram"][0].encode()).hexdigest(),
        },
    )


def test_stock_radar_logic_mode(scan):
    _m, sent = scan
    req = radar_schemas.StockRadarRequest(
        symbols=[{"symbol": "AAA", "exchange": "NASDAQ"}],
        formulas=["UIPT"],
        timeframes=["1d"],
        analysis_mode="logic",
    )
    out = radar_service.run_scan(req)
    assert "prompt" not in sent
    check("stock_radar_logic", {"sha256": hashlib.sha256(out["analysis"].encode()).hexdigest()})


PROVIDER_PAYLOADS = {
    "finnhub": [
        [{"period": "2026-06-30", "actual": 1.2, "estimate": 1.1, "surprisePercent": 9.1}] * 5,
        {"earningsCalendar": [{"date": "2026-11-05"}, {"date": "2026-11-01"}]},
    ],
}


def test_earnings_provider_chain(main_module, monkeypatch, env):
    fins = inspect.getmodule(providers._fetch_earnings_finnhub).__dict__
    calls = iter(PROVIDER_PAYLOADS["finnhub"])
    monkeypatch.setitem(fins, "_http_get_json", lambda url, timeout=10, headers=None: next(calls))
    # Only Finnhub has a key: the chain never reaches a real FMP / Alpha Vantage.
    env(FINNHUB_API_KEY="k", FMP_API_KEY=None, ALPHA_VANTAGE_API_KEY=None)
    monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: (_ for _ in ()).throw(OSError()))
    result = providers._fetch_earnings_for_symbol("AAA")
    check("earnings_finnhub", json.loads(json.dumps(result, default=str)))
    env(FINNHUB_API_KEY=None)
    empty = providers._fetch_earnings_for_symbol("AAA")
    assert empty["provider"] is None and len(empty["attempted"]) == 3
