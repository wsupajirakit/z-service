"""Key/value settings (moved unchanged from store.py)."""

from zservice.db.client import _db


def settings_get_many(keys) -> dict:
    cur = _db.settings.find({"key": {"$in": list(keys)}}, {"_id": 0, "key": 1, "value": 1})
    return {d["key"]: d["value"] for d in cur}


def settings_get(key: str):
    d = _db.settings.find_one({"key": key}, {"_id": 0, "value": 1})
    return d["value"] if d else None


def settings_set(key: str, value):
    _db.settings.update_one({"key": key}, {"$set": {"value": value}}, upsert=True)
