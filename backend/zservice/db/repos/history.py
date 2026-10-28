"""Fetch-result cache, keyed by symbol+exchange+interval+extended_session (moved unchanged
from store.py)."""

from pymongo import DESCENDING

from zservice.db.client import _db, _next_id
from zservice.db.repos.watchlist import watchlist_symbols


def history_upsert(symbol, exchange, interval, extended_session, timestamp, result_json):
    """Insert or update the single row for this symbol/exchange/interval/ext."""
    key = {
        "symbol": symbol,
        "exchange": exchange,
        "interval": interval,
        "extended_session": extended_session,
    }
    existing = _db.history.find_one(key, {"_id": 1})
    if existing:
        _db.history.update_one(
            {"_id": existing["_id"]},
            {"$set": {"timestamp": timestamp, "result_json": result_json}},
        )
    else:
        doc = dict(key)
        doc.update(id=_next_id("history"), timestamp=timestamp, result_json=result_json)
        _db.history.insert_one(doc)


def history_list():
    """All rows (metadata only, no result_json), newest first."""
    cur = _db.history.find(
        {},
        {
            "_id": 0,
            "id": 1,
            "timestamp": 1,
            "symbol": 1,
            "exchange": 1,
            "interval": 1,
            "extended_session": 1,
        },
    ).sort("id", DESCENDING)
    return list(cur)


def history_get_result(history_id: int):
    d = _db.history.find_one({"id": history_id}, {"_id": 0, "result_json": 1})
    return d["result_json"] if d else None


def history_delete_all():
    _db.history.delete_many({})


def history_count() -> int:
    return _db.history.count_documents({})


def history_cleanup(cutoff_iso: str) -> int:
    """Delete rows with timestamp < cutoff, but always keep the newest row per
    (symbol, interval) so exports never lose a symbol. Returns deleted count.
    """
    # Ids to protect per (symbol, interval): the last-created row AND the
    # freshest one. They are only different when a symbol has several rows for
    # the interval (one per extended_session flag), and in that case the
    # freshest is the row exports actually read — deleting it would hand the
    # export back the stale copy.
    keep_ids = []
    for g in _db.history.aggregate(
        [
            {
                "$group": {
                    "_id": {"s": "$symbol", "i": "$interval"},
                    "max_id": {"$max": "$id"},
                    "newest": {"$max": {"ts": "$timestamp", "id": "$id"}},
                }
            },
        ]
    ):
        keep_ids.append(g["max_id"])
        keep_ids.append(g["newest"]["id"])
    res = _db.history.delete_many({"timestamp": {"$lt": cutoff_iso}, "id": {"$nin": keep_ids}})
    return res.deleted_count


def history_distinct_symbols(interval: str, list_names=None):
    """Distinct symbols present in history for an interval, optionally limited
    to symbols that belong to the given watchlist(s)."""
    q = {"interval": interval}
    if list_names:
        allowed = watchlist_symbols(list_names)
        q["symbol"] = {"$in": allowed}
    return _db.history.distinct("symbol", q)


def history_latest_per_symbol(interval: str, list_names=None):
    """For an interval, return the most-recent row per symbol as dicts with
    keys symbol, result_json, timestamp, exchange — sorted by symbol asc.
    Optionally restricted to symbols in the given watchlist(s).
    """
    match = {"interval": interval}
    if list_names is not None:
        allowed = watchlist_symbols(list_names)
        match["symbol"] = {"$in": allowed}
    # Two-step to avoid Mongo's 32MB in-memory aggregation-sort limit: the docs
    # carry a big `result_json`, so sorting the whole set blows the cap. First
    # find the newest row per symbol (tiny — only timestamp+id), then fetch just
    # those docs by id (id is globally unique). Sort the ~200 rows in Python.
    #
    # "Newest" means newest TIMESTAMP, not highest id. A symbol can hold more
    # than one row per interval — history_upsert keys on
    # (symbol, exchange, interval, extended_session), so changing the extended
    # flag creates a SECOND row — and ids are handed out at creation while
    # timestamps track every refresh. Selecting by id therefore pinned the
    # export to whichever row was created last even after it stopped being
    # updated: a stale 1D snapshot silently fed every export, the ZIP and
    # load_all.sh (incident 2026-08-12). $max over {ts,id} compares ts first and
    # falls back to id on a tie.
    groups = _db.history.aggregate(
        [
            {"$match": match},
            {"$group": {"_id": "$symbol", "newest": {"$max": {"ts": "$timestamp", "id": "$id"}}}},
        ]
    )
    max_ids = [g["newest"]["id"] for g in groups]
    if not max_ids:
        return []
    # Fetch in small chunks: one giant $in cursor streams for minutes when
    # Atlas is throttled, and a single mid-stream stall kills the whole export.
    # Chunking bounds each cursor's lifetime so partial progress always lands.
    rows = []
    CHUNK = 25
    for i in range(0, len(max_ids), CHUNK):
        docs = _db.history.find(
            {"id": {"$in": max_ids[i : i + CHUNK]}},
            {"_id": 0, "symbol": 1, "result_json": 1, "timestamp": 1, "exchange": 1},
        )
        rows.extend(
            {
                "symbol": d["symbol"],
                "result_json": d["result_json"],
                "timestamp": d["timestamp"],
                "exchange": d["exchange"],
            }
            for d in docs
        )
    rows.sort(key=lambda r: r["symbol"])
    return rows


def history_tf_stats(interval: str, list_names=None) -> dict:
    """Cheap per-interval freshness probe for the radar page: how many symbols
    are stored for this timeframe and when each was written — WITHOUT dragging
    the big result_json blobs over the wire (that is what makes /api/export
    slow). Returns {symbols_count, timestamps: [...]} , newest per symbol.
    """
    match = {"interval": interval}
    if list_names:
        match["symbol"] = {"$in": watchlist_symbols(list_names)}
    # Reports the freshness of the rows the EXPORT will actually read (same
    # selector as history_latest_per_symbol), plus how many symbols carry more
    # than one row for this interval — duplicates are what let a stale copy sit
    # in front of fresh data, so the page has to be able to name the problem.
    groups = list(
        _db.history.aggregate(
            [
                {"$match": match},
                {
                    "$group": {
                        "_id": "$symbol",
                        "n": {"$sum": 1},
                        "newest": {"$max": {"ts": "$timestamp", "id": "$id"}},
                    }
                },
            ]
        )
    )
    if not groups:
        return {"symbols_count": 0, "timestamps": [], "duplicate_symbols": 0, "rows_total": 0}
    return {
        "symbols_count": len(groups),
        "rows_total": sum(g["n"] for g in groups),
        "duplicate_symbols": sum(1 for g in groups if g["n"] > 1),
        "timestamps": sorted(g["newest"]["ts"] for g in groups if g["newest"].get("ts")),
    }


def history_newest_row(interval: str, list_names=None):
    """The most recently written row for an interval, WITH its result_json —
    one document, so the radar page can show the newest bar per timeframe
    without pulling the whole interval (which is the expensive export path).
    Symbols in an interval are fetched as one batch, so any row's last bar is
    representative of that batch."""
    q = {"interval": interval}
    if list_names:
        q["symbol"] = {"$in": watchlist_symbols(list_names)}
    return _db.history.find_one(
        q,
        {"_id": 0, "symbol": 1, "timestamp": 1, "result_json": 1},
        sort=[("id", DESCENDING)],
    )
