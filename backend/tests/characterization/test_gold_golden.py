"""Characterization of the Gemini gold analysis before it moves out of main.py.

process_symbol, Gemini and the news feed are faked with deterministic data in whichever
module defines the code under test. Pins the exact prompt sent to the model, the result
(minus its wall-clock stamp) and the gold CSV bytes.
"""

import hashlib
import inspect
import json
import sys
from pathlib import Path

import pytest

from zservice.domains.gold import analysis as gold_analysis
from zservice.domains.gold import export as gold_export_csv
from zservice.domains.gold import schemas as gold_schemas
from zservice.domains.gold import state as gold_state

from .golden import check

GOLD_PACKAGE = "zservice.domains.gold."
KEYS = json.loads((Path(__file__).parent / "golden" / "process_symbol_tv_spy_1h.json").read_text())[
    "keys"
]


def _bars(symbol: str, tf: str, rows: int) -> list[dict]:
    base = 2000.0 + 7 * len(symbol) + {"15m": 0, "1h": 1, "4h": 2, "1d": 3}.get(tf, 4)
    out = []
    for i in range(rows):
        row = {k: round(base + i * 0.5 + j * 0.01, 4) for j, k in enumerate(KEYS)}
        row.update(
            {
                "datetime": f"2026-10-23 {i % 24:02d}:00:00",
                "session": "RTH",
                "IPI_Status": "Neutral",
                "is_closed_bar": True,
                "symbol": symbol,
            }
        )
        out.append(row)
    return out


@pytest.fixture
def gold(main_module, monkeypatch, env):
    m = main_module
    env(GEMINI_API_KEY="test-key")
    sent = {}
    mods = [inspect.getmodule(gold_analysis._gold_analyze_core).__dict__]
    # Every module of the gold package, so fakes keep applying however the code is split.
    mods += [mod.__dict__ for name, mod in sys.modules.items() if name.startswith(GOLD_PACKAGE)]

    def put(name, value):
        for mod in mods:
            if name in mod:
                monkeypatch.setitem(mod, name, value)

    def fake_gemini(model, prompt):
        sent["prompt"] = prompt
        return f"analysis by {model}"

    fakes = {
        "process_symbol": lambda sym, ex, tf, extended_session=False, rows=40, store=False: _bars(
            sym, tf, rows
        ),
        "_call_gemini": fake_gemini,
        "fetch_all_news": lambda *a, **k: [
            {"source": "S", "title": f"headline {i}", "link": "x", "pubDate": "p"} for i in range(3)
        ],
    }
    for name, value in fakes.items():
        put(name, value)
    gold_state.gold_stop_event.clear()
    return m, sent, put


def test_gold_prompt_and_result(gold):
    _m, sent, _ = gold
    req = gold_schemas.GoldAnalyzeRequest(exchange="OANDA", model="gemini-test", rows=60)
    result = gold_analysis._gold_analyze_core(req)
    result.pop("generated_at")
    check(
        "gold_analysis",
        {
            "prompt_sha256": hashlib.sha256(sent["prompt"].encode()).hexdigest(),
            "prompt_chars": len(sent["prompt"]),
            "result_sha256": hashlib.sha256(
                json.dumps(result, sort_keys=True, default=str).encode()
            ).hexdigest(),
            "result_keys": sorted(result),
        },
    )


def test_gold_csv_bytes(gold, monkeypatch):
    _m, _, _ = gold
    req = gold_schemas.GoldAnalyzeRequest(exchange="OANDA", model="gemini-test", rows=60)
    result = gold_analysis._gold_analyze_core(req)
    result["generated_at"] = "2026-10-24T00:00:00+00:00"
    build = gold_export_csv._build_gold_csv_bytes
    g = inspect.getmodule(build).__dict__
    for name in ("_tz_suffix", "tz_suffix"):
        if name in g:
            monkeypatch.setitem(g, name, lambda: "UTC+7")
    data = build(result, "2026-10-24_07-00-00")
    check("gold_csv", {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()})


def _degraded_process(sym, ex, tf, extended_session=False, rows=40, store=False):
    """4h unavailable, 1d broken, VIX broken, silver empty, DXY too short for a 24h change."""
    from fastapi import HTTPException

    if tf == "4h" and sym == "XAUUSD":
        raise HTTPException(status_code=404, detail="no 4h bars")
    if tf == "1d" or sym == "VIX":
        raise ValueError(f"{sym} {tf} broken")
    if sym == "XAGUSD":
        return []
    bars = _bars(sym, tf, 10 if sym == "DXY" else rows)
    if sym == "US10Y":
        bars[-25]["close"] = 0  # a zero base must not divide
    return bars


@pytest.mark.parametrize("template", ["file", "missing"])
def test_gold_degraded_inputs(gold, template):
    _m, sent, put = gold
    put("process_symbol", _degraded_process)
    if template == "missing":
        put("_load_gold_prompt_template", lambda: "")
        put("load_gold_prompt_template", lambda: "")
    req = gold_schemas.GoldAnalyzeRequest(exchange="PEPPERSTONE", model="gemini-test", rows=30)
    result = gold_analysis._gold_analyze_core(req)
    result.pop("generated_at")
    check(
        f"gold_analysis_degraded_{template}",
        {
            "prompt_sha256": hashlib.sha256(sent["prompt"].encode()).hexdigest(),
            "prompt_tail": sent["prompt"][-600:],
            "result": json.loads(json.dumps(result, default=str)),
        },
    )


def test_gold_stop_and_bad_source(gold):
    from fastapi import HTTPException

    _m, sent, _ = gold
    with pytest.raises(HTTPException) as bad:
        gold_analysis._gold_analyze_core(
            gold_schemas.GoldAnalyzeRequest(exchange="NOPE", model="x", rows=30)
        )
    assert bad.value.status_code == 400 and "Unsupported source" in bad.value.detail
    gold_state.gold_stop_event.set()
    try:
        with pytest.raises(Exception, match="Stopped by user"):
            gold_analysis._gold_analyze_core(
                gold_schemas.GoldAnalyzeRequest(exchange="OANDA", model="x", rows=30)
            )
    finally:
        gold_state.gold_stop_event.clear()
    assert "prompt" not in sent
