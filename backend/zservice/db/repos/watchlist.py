"""Named symbol lists (moved unchanged from store.py)."""

from pymongo import DESCENDING

from zservice.db.client import _db


def watchlist_all():
    """All rows newest first: symbol, name, timestamp, list_name."""
    cur = _db.watchlist.find(
        {}, {"_id": 0, "symbol": 1, "name": 1, "timestamp": 1, "list_name": 1, "exchange": 1}
    ).sort("timestamp", DESCENDING)
    return list(cur)


def watchlist_add(list_name, symbol, name, timestamp, exchange=None):
    """Insert-or-ignore on (list_name, symbol). `exchange` (NASDAQ/NYSE/AMEX/...) is stored so the
    server can build the fetch list itself (/api/symbols) without a frontend rebuild."""
    update = {"$setOnInsert": {"name": name, "timestamp": timestamp}}
    if exchange:
        update["$set"] = {"exchange": exchange}
    _db.watchlist.update_one({"list_name": list_name, "symbol": symbol}, update, upsert=True)


def watchlist_remove(list_name, symbol):
    _db.watchlist.delete_one({"list_name": list_name, "symbol": symbol})


def watchlist_rename(old_name, new_name):
    _db.watchlist.update_many({"list_name": old_name}, {"$set": {"list_name": new_name}})


def watchlist_symbols(list_names):
    """Distinct symbols across the given watchlist name(s)."""
    if isinstance(list_names, str):
        list_names = [list_names]
    return _db.watchlist.distinct("symbol", {"list_name": {"$in": list(list_names)}})
