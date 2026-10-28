"""Characterization of the standalone gold *mode* export (/api/gold/export, /api/gold/modes),
pinned before it moved out of the old backend/gold.py.

Deterministic OHLCV frames replace TradingView, fixed headlines replace RSS and the clock
is frozen, in whichever module defines the code. Pins every zip member (sha256), the
cache hit on a repeat call and the modes listing.
"""

import hashlib
import inspect
import io
import sys
import zipfile
from datetime import UTC, datetime

import pandas as pd
import pytest

from zservice.domains.gold_mode import export as gold_mode_export
from zservice.domains.gold_mode import routes as gold_mode_routes

from .golden import check

FROZEN = datetime(2026, 10, 23, 15, 0, tzinfo=UTC)


class _FrozenDatetime(datetime):
    @classmethod
    def now(cls, tz=None):
        return FROZEN.astimezone(tz) if tz else FROZEN.replace(tzinfo=None)


def _frame(symbol: str, tf: str, n_bars: int) -> pd.DataFrame:
    base = 2000.0 + 13 * len(symbol) + len(tf)
    step = {"1m": 1, "5m": 5, "15m": 15, "30m": 30, "1h": 60, "4h": 240, "1d": 1440}.get(tf, 60)
    rows = []
    for i in range(n_bars):
        px = base + (i % 37) * 0.7 - (i % 11) * 0.3
        rows.append(
            {
                "dt": pd.Timestamp("2026-10-23 15:00:00")
                - pd.Timedelta(minutes=step * (n_bars - i)),
                "open": px,
                "high": px + 1.5,
                "low": px - 1.2,
                "close": px + 0.4,
                "volume": 1000.0 + (i * 37) % 500,
            }
        )
    return pd.DataFrame(rows)


@pytest.fixture
def gold_mode(monkeypatch):
    """Fakes installed in every module of the gold_mode package; the zip cache emptied."""
    route = gold_mode_routes.gold_export
    fakes = {
        "_fetch_df": lambda symbol, exchange, tf, n_bars: _frame(symbol, tf, n_bars),
        "_fetch_news": lambda limit: [
            {"source": "S", "title": f"h{i}", "pubDate": "p", "link": "x"} for i in range(limit)
        ],
        "datetime": _FrozenDatetime,
    }
    # Every module of the gold_mode package, so fakes keep applying however it is split.
    modules = {inspect.getmodule(route), inspect.getmodule(gold_mode_export._formula_csv)}
    modules |= {m for n, m in sys.modules.items() if n.startswith("zservice.domains.gold_mode.")}
    for module in modules:
        for name, value in fakes.items():
            if name in module.__dict__:
                monkeypatch.setitem(module.__dict__, name, value)
    from zservice.domains.gold_mode import service

    service.CACHE.clear()


@pytest.mark.parametrize("mode", ["swing", "scalp"])
def test_gold_mode_zip_members(gold_mode, mode):
    resp = gold_mode_routes.gold_export(mode=mode, exchange="ICMARKETS")
    assert resp.headers["X-Gold-Cache"] == "miss"
    with zipfile.ZipFile(io.BytesIO(resp.body)) as zf:
        members = [
            {"name": i.filename, "sha256": hashlib.sha256(zf.read(i)).hexdigest()}
            for i in zf.infolist()
        ]
    check(f"gold_mode_{mode}", members)
    again = gold_mode_routes.gold_export(mode=mode, exchange="ICMARKETS")
    assert again.headers["X-Gold-Cache"] == "hit" and again.body == resp.body


def test_gold_modes_listing(gold_mode):
    check("gold_modes", gold_mode_routes.gold_modes())
