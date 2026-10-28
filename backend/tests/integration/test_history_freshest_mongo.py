"""Exports must read the FRESHEST stored row per symbol (incident 2026-08-12).

`history_upsert` keys rows on (symbol, exchange, interval, extended_session), so flipping
the extended flag creates a SECOND row for the same symbol+interval. Ids are handed out at
creation and never change; timestamps track every refresh. The export used to select
`$max: id` — "the row created last" — which pinned it to a row that had stopped being
updated: the History page showed 1D fetched minutes ago while every export served a
snapshot ~20 hours older, one daily bar behind.

Needs a real MongoDB for the aggregation pipeline: a LOCAL test server only, never
production. ZS_TEST_MONGO_URI=mongodb://127.0.0.1:27017 venv/bin/python -m pytest -m mongo
Each run uses its own throwaway database, dropped afterwards.
"""

import os
import uuid

import pytest

from zservice.db.repos import history

pytestmark = pytest.mark.mongo

FRESH = "2026-08-12T22:39:23+07:00"  # today's auto round
STALE = "2026-08-12T03:10:00+07:00"  # a run 20 h earlier that never repeated


def _row(id_, symbol, ext, ts, bar):
    return {"id": id_, "symbol": symbol, "exchange": "NYSE", "interval": "1d",
            "extended_session": ext, "timestamp": ts,
            "result_json": f'[{{"datetime": "{bar} 09:30:00"}}]'}  # fmt: skip


@pytest.fixture
def db(monkeypatch):
    from pymongo import MongoClient

    uri = os.environ["ZS_TEST_MONGO_URI"]
    assert uri.startswith(("mongodb://127.0.0.1", "mongodb://localhost")), "local server only"
    client = MongoClient(uri, serverSelectionTimeoutMS=3000)
    name = f"zs_test_{uuid.uuid4().hex[:12]}"
    test_db = client[name]
    monkeypatch.setattr(history, "_db", test_db)
    test_db.history.insert_many([
        # AX carries both rows: the fresh one was created FIRST (lower id).
        _row(10, "AX", False, FRESH, "2026-08-12"),
        _row(99, "AX", True, STALE, "2026-08-11"),
        # HG is the ordinary single-row case — must be unaffected.
        _row(20, "HG", False, FRESH, "2026-08-12"),
    ])  # fmt: skip
    yield test_db
    client.drop_database(name)
    client.close()


def test_export_reads_the_freshest_row(db):
    rows = {r["symbol"]: r for r in history.history_latest_per_symbol("1d")}
    assert len(rows) == 2, f"expected one row per symbol, got {len(rows)}"
    assert rows["AX"]["timestamp"] == FRESH, f"stale row picked: {rows['AX']['timestamp']}"
    assert "2026-08-12" in rows["AX"]["result_json"], "AX still carries yesterday's bar"
    assert rows["HG"]["timestamp"] == FRESH, "single-row symbol changed behaviour"


def test_tf_stats_report_duplicates_and_the_exported_freshness(db):
    st = history.history_tf_stats("1d")
    assert st["symbols_count"] == 2 and st["rows_total"] == 3, st
    assert st["duplicate_symbols"] == 1 and st["timestamps"][-1] == FRESH, st


def test_cleanup_never_deletes_the_row_exports_need(db):
    history.history_cleanup("2026-08-12T12:00:00+07:00")
    left = sorted(d["id"] for d in db.history.find({}, {"_id": 0, "id": 1}))
    assert 10 in left and 20 in left, f"cleanup deleted rows exports need (left {left})"
