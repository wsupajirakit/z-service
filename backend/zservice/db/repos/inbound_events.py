"""Inbound events from other systems (CloudEvents received over signed webhooks).
One document per (sender, webhook id): a retried delivery is stored once."""

from pymongo import DESCENDING
from pymongo.errors import DuplicateKeyError

from zservice.db.client import _db


def inbound_insert(doc: dict) -> bool:
    """Store one event; False when this sender already delivered this webhook id."""
    try:
        _db.inbound_events.insert_one(dict(doc))
    except DuplicateKeyError:
        return False
    return True


def inbound_list(limit: int, sender: str | None = None, event_type: str | None = None) -> list:
    query: dict = {}
    if sender:
        query["sender"] = sender
    if event_type:
        query["type"] = event_type
    cur = _db.inbound_events.find(query, {"_id": 0}).sort("received_at", DESCENDING).limit(limit)
    return list(cur)
