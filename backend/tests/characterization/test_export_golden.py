"""Byte-level pins for the CSV builders that stock-radar consumes (export, formula, news).

stock-radar parses these files directly, so a moved builder must produce the same bytes.
Inputs are fixed fixture rows; the network is blocked so live RSS never leaks in.
"""

import hashlib
import json
from datetime import datetime, timedelta

import pytest

from zservice.domains.exports import formula_csv, news_csv, stock_csv
from zservice.security import tokens as session_auth

from .golden import check

NEWEST = {
    "1w": datetime(2026, 10, 19),
    "1d": datetime(2026, 10, 21),
    "4h": datetime(2026, 10, 21, 13, 30),
    "1h": datetime(2026, 10, 21, 15, 30),
}
STEP = {
    "1w": timedelta(days=7),
    "1d": timedelta(days=1),
    "4h": timedelta(hours=4),
    "1h": timedelta(hours=1),
}


def _bars(n: int, newest: datetime, step: timedelta) -> list[dict]:
    out = []
    for i in range(n):
        px = 10.0 + i
        out.append(
            {
                "datetime": (newest - step * (n - 1 - i)).strftime("%Y-%m-%d %H:%M:%S"),
                "open": px,
                "high": px + 1,
                "low": px - 1,
                "close": px + 0.5,
                "volume": 1000 + i,
                "EMA_20": px,
                "EMA_50": px,
                "EMA_100": px,
                "EMA_200": px,
                "is_closed_bar": True,
            }
        )
    return out


def _rows(interval: str) -> list[dict]:
    # 6 full-history symbols (mode = 80 bars), 1 short-history listing, 1 broken row.
    names = ["AAA", "BBB", "CCC", "DDD", "EEE", "FFF"]
    rows = [_row(s, _bars(80, NEWEST[interval], STEP[interval])) for s in names]
    rows.append(_row("NEWIPO", _bars(23, NEWEST[interval], STEP[interval])))
    rows.append(_row("BROKEN", _bars(5, NEWEST[interval] - STEP[interval] * 60, STEP[interval])))
    return rows


def _row(symbol: str, records: list[dict]) -> dict:
    return {
        "symbol": symbol,
        "timestamp": "2026-10-22T07:04:49+07:00",
        "exchange": "NASDAQ",
        "result_json": json.dumps(records),
    }


def _digest(data: bytes) -> dict:
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


@pytest.mark.parametrize("interval", ["1w", "1d"])
def test_export_csv_bytes(offline, interval):
    rows = _rows(interval)
    result = {
        f"part{part}": _digest(stock_csv.build_export_csv_bytes(interval, part, rows=rows))
        for part in (1, 2)
    }
    check(f"export_{interval}", result)


def test_formula_csv_bytes(offline):
    check("formula", _digest(formula_csv.build_formula_csv_bytes()))


def test_news_csv_bytes(offline):
    check("news", _digest(news_csv.build_news_csv_bytes()))


def test_export_zip_members(offline, monkeypatch):
    """GET /api/export_zip?all=true is what stock-radar's load_all.sh downloads. Zip entry
    timestamps differ per build, so pin member names, order and per-member sha256."""
    import io
    import zipfile

    from fastapi.testclient import TestClient

    from zservice.db.repos import history as history_repo

    monkeypatch.setattr(
        history_repo, "history_latest_per_symbol", lambda interval, names=None: _rows(interval)
    )
    client = TestClient(offline.app)
    token = session_auth.create_token("golden")
    r = client.get("/api/export_zip?all=true", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
        members = [{"name": i.filename, **_digest(zf.read(i))} for i in zf.infolist()]
    check("export_zip_all", members)
