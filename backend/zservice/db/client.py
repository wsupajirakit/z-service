"""MongoDB connection for z-service.

All persistence goes through this module so the rest of the app never touches
the database driver directly. Backed by MongoDB Atlas (survives redeploys —
unlike the old SQLite file on an ephemeral container volume).

Config: MONGO_URI, MONGO_DB (config.MongoSettings).

Collections mirror the old SQLite tables: history, watchlist, portfolio,
settings, stock_radar_history, earning_scan_history. Collections that had an
auto-increment primary key keep an integer `id` field, handed out by an atomic
counter in the `counters` collection so ids stay stable and monotonic.
"""

from pymongo import MongoClient

from . import config as db_config

_cfg = db_config.get_settings()
_MONGO_URI = _cfg.uri.get_secret_value() if _cfg.uri else None
_MONGO_DB = _cfg.db

if not _MONGO_URI:
    # Don't raise at import — that would take the whole app down (502 Bad
    # Gateway) instead of surfacing a clear error. Fail on first DB use instead.
    print("[store] WARNING: MONGO_URI is not set — DB calls will fail until configured")

# Fail fast (5s) on connect so a blocked/unreachable Atlas surfaces a quick
# 500 rather than hanging the request/UI. socketTimeoutMS is deliberately LONG:
# a throttled Atlas (free-tier data-transfer cap) can drop to ~100KB/s, and the
# export path streams many large result_json docs over one cursor — a 20s
# socket timeout killed every full-universe export while small queries still
# passed (incident 2026-08-03).
_client = (
    MongoClient(
        _MONGO_URI,
        serverSelectionTimeoutMS=5000,
        connectTimeoutMS=5000,
        socketTimeoutMS=180000,
        tz_aware=False,
    )
    if _MONGO_URI
    else None
)
_db = _client[_MONGO_DB] if _client is not None else None


def _next_id(name: str) -> int:
    """Atomically increment and return the counter for `name` (1-based)."""
    doc = _db.counters.find_one_and_update(
        {"_id": name},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=True,
    )
    return int(doc["seq"])


def ping():
    """Raise if the cluster is unreachable (used at startup)."""
    _client.admin.command("ping")


def ensure_indexes():
    """Create the indexes the query paths rely on. Idempotent — safe to call on
    every startup. Without these, exports full-scan the history collection on
    every request (slow enough under load + Atlas latency to trip gateway 502s).
    """
    if _db is None:
        return
    # history: interval filter + per-symbol grouping + id lookups ($in / detail)
    # + the upsert key. Partial/compound indexes cover the hot export path.
    _db.history.create_index([("interval", 1), ("symbol", 1)])
    _db.history.create_index([("id", 1)], unique=True)
    _db.history.create_index(
        [("symbol", 1), ("exchange", 1), ("interval", 1), ("extended_session", 1)]
    )
    # watchlist: dedup key + list lookups
    _db.watchlist.create_index([("list_name", 1), ("symbol", 1)], unique=True)
    # portfolio / settings lookups
    _db.portfolio.create_index([("port_name", 1)])
    _db.settings.create_index([("key", 1)], unique=True)
    # inbound events: one per sender + webhook id (retries dedupe); expire after the TTL
    _db.inbound_events.create_index([("sender", 1), ("webhook_id", 1)], unique=True)
    _db.inbound_events.create_index([("received_at", -1)])
    _db.inbound_events.create_index(
        [("expires_at", 1)], expireAfterSeconds=0, name="inbound_events_ttl"
    )
