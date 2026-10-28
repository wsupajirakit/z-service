"""The single dashboard user (moved unchanged from store.py)."""

from zservice.db.client import _db


def user_exists() -> bool:
    return _db.app_user.count_documents({}) > 0


def user_get(username: str):
    return _db.app_user.find_one({"username": username}, {"_id": 0})


def user_create(username: str, password_hash: str, created_at: str):
    """Create the one and only user. Returns False if one already exists.

    One upsert with an empty filter: it matches any existing user, so the insert happens
    only into an empty collection (no separate count-then-insert window)."""
    res = _db.app_user.update_one(
        {},
        {
            "$setOnInsert": {
                "username": username,
                "password_hash": password_hash,
                "created_at": created_at,
            }
        },
        upsert=True,
    )
    return res.upserted_id is not None


def user_set_password(username: str, password_hash: str, updated_at: str) -> bool:
    res = _db.app_user.update_one(
        {"username": username},
        {"$set": {"password_hash": password_hash, "password_updated_at": updated_at}},
    )
    return res.matched_count == 1
