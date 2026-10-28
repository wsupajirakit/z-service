"""Offline pin of process_symbol (indicators, sessions, closed-bar flags) on recorded bars.

Fixtures are raw tvDatafeed frames recorded once from TradingView (SPY 1h/4h/1d/1w,
BTCUSDT 1h) — see fixtures/tv_cases.json. The test swaps the network calls and the clock
in whichever module defines process_symbol, so it keeps working while the function moves
out of main.py. Runs with TZ=UTC like the Coolify container.
"""

import hashlib
import inspect
import json
import os
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import pytest

from zservice.domains.market_data import pipeline

from .golden import check

FIXTURES = Path(__file__).parent / "fixtures"
CASES = json.loads((FIXTURES / "tv_cases.json").read_text(encoding="utf-8"))
FROZEN = datetime.fromisoformat(CASES["frozen_now_et"])


class _FrozenDatetime(datetime):
    @classmethod
    def now(cls, tz=None):
        return FROZEN.astimezone(tz) if tz else FROZEN.replace(tzinfo=None)


@pytest.fixture(scope="module", autouse=True)
def utc_process():
    old = os.environ.get("TZ")
    os.environ["TZ"] = "UTC"
    time.tzset()
    yield
    if old is None:
        os.environ.pop("TZ", None)
    else:
        os.environ["TZ"] = old
    time.tzset()


def _package_modules(fn):
    import importlib
    import pkgutil

    package = importlib.import_module(inspect.getmodule(fn).__name__.rsplit(".", 1)[0])
    mods = [inspect.getmodule(fn)]
    if hasattr(package, "__path__"):
        for info in pkgutil.iter_modules(package.__path__):
            mods.append(importlib.import_module(f"{package.__name__}.{info.name}"))
    return mods


def _load(name: str) -> pd.DataFrame:
    return pd.read_csv(FIXTURES / f"{name}.csv.gz", index_col=0, parse_dates=True)


@pytest.mark.parametrize("case", CASES["cases"], ids=lambda c: c["name"])
def test_process_symbol_output(main_module, monkeypatch, case):
    fn = pipeline.process_symbol
    frame = _load(case["name"])
    fakes = {
        "get_tv_data_with_retry": lambda *a, **k: frame.copy(),
        "resolve_tv_exchange": lambda symbol, exchange: exchange,
        "datetime": _FrozenDatetime,
    }
    # Install the fakes in every module of the pipeline's package that uses the name, so
    # the test keeps working when the pipeline is split into several modules.
    for module in _package_modules(fn):
        for name, value in fakes.items():
            if name in module.__dict__:
                monkeypatch.setitem(module.__dict__, name, value)
    out = fn(
        case["symbol"],
        case["exchange"],
        case["interval"],
        extended_session=case["extended"],
        rows=case["rows"],
        store=False,
    )
    rendered = json.dumps(out, sort_keys=True, default=str).encode()
    check(
        f"process_symbol_{case['name']}",
        {
            "rows": len(out),
            "first": out[0]["datetime"],
            "last": out[-1]["datetime"],
            "keys": sorted(out[-1]),
            "sha256": hashlib.sha256(rendered).hexdigest(),
        },
    )
