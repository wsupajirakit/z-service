"""Manual trade ledger (moved unchanged from store.py)."""

from pymongo import DESCENDING

from zservice.db.client import _db, _next_id


def portfolio_all():
    cur = _db.portfolio.find(
        {},
        {
            "_id": 0,
            "symbol": 1,
            "quantity": 1,
            "buy_price": 1,
            "timestamp": 1,
            "action": 1,
            "port_name": 1,
        },
    ).sort("timestamp", DESCENDING)
    return list(cur)


def portfolio_add(port_name, symbol, quantity, buy_price, timestamp, action):
    _db.portfolio.insert_one(
        {
            "id": _next_id("portfolio"),
            "port_name": port_name,
            "symbol": symbol,
            "quantity": quantity,
            "buy_price": buy_price,
            "timestamp": timestamp,
            "action": action,
        }
    )


def portfolio_remove(port_name, symbol):
    _db.portfolio.delete_one({"port_name": port_name, "symbol": symbol})


def portfolio_rename(old_name, new_name):
    _db.portfolio.update_many({"port_name": old_name}, {"$set": {"port_name": new_name}})
