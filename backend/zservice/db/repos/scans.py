"""Stock radar + earnings scan history (moved unchanged from store.py)."""

from pymongo import DESCENDING

from zservice.db.client import _db, _next_id


def radar_add(timestamp, symbols, formulas, timeframes, extended_session, result_markdown):
    _db.stock_radar_history.insert_one(
        {
            "id": _next_id("stock_radar_history"),
            "timestamp": timestamp,
            "symbols": symbols,
            "formulas": formulas,
            "timeframes": timeframes,
            "extended_session": extended_session,
            "result_markdown": result_markdown,
        }
    )


def radar_list(limit: int):
    cur = (
        _db.stock_radar_history.find(
            {},
            {
                "_id": 0,
                "id": 1,
                "timestamp": 1,
                "symbols": 1,
                "formulas": 1,
                "timeframes": 1,
                "extended_session": 1,
                "result_markdown": 1,
            },
        )
        .sort("id", DESCENDING)
        .limit(limit)
    )
    return list(cur)


def earning_add(timestamp, symbols, result_json):
    _db.earning_scan_history.insert_one(
        {
            "id": _next_id("earning_scan_history"),
            "timestamp": timestamp,
            "symbols": symbols,
            "result_json": result_json,
        }
    )


def earning_list(limit: int):
    cur = (
        _db.earning_scan_history.find(
            {}, {"_id": 0, "id": 1, "timestamp": 1, "symbols": 1, "result_json": 1}
        )
        .sort("id", DESCENDING)
        .limit(limit)
    )
    return list(cur)
