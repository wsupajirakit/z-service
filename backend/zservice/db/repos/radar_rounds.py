"""Frozen radar-screen rounds (moved from store.py; the lazy-index flag is a dict, not a
global)."""

from pymongo import DESCENDING

from zservice.db.client import _db, _next_id

# radar_rounds  (frozen radar-screen results — one document per computed round)
#
# Why a new collection instead of reusing `history`: history keeps only the
# LATEST row per symbol/interval and /api/history/cleanup prunes it constantly,
# so it can never answer "show me the screen as it looked at 08:23". A round
# freezes one complete screen (digest + full state) under an immutable stamp,
# and nothing else in the app reads or writes it.
#
# Indexes are created lazily on first use (one build per process) so this block
# is purely additive — ensure_indexes() above is untouched.
# ---------------------------------------------------------------------------
_INDEXES = {"ready": False}  # one index build per process


_ROUND_META_PROJECTION = {
    "_id": 0,
    "id": 1,
    "stamp": 1,
    "fingerprint": 1,
    "created_at": 1,
    "asof_et": 1,
    "asof_et_iso": 1,
    "data_age_hours": 1,
    "timeframes": 1,
    "tf_meta": 1,
    "screen_mode": 1,
    "partial": 1,
    "list_name": 1,
    "universe": 1,
    "kill_pct": 1,
    "kill_count": 1,
    "kill_label": 1,
    "breadth_n": 1,
    "regime_hint": 1,
    "warnings": 1,
}


def _rounds():
    """The radar_rounds collection, with its indexes ensured once per process."""
    if not _INDEXES["ready"]:
        _db.radar_rounds.create_index([("stamp", 1)], unique=True)
        _db.radar_rounds.create_index([("id", DESCENDING)])
        _db.radar_rounds.create_index([("fingerprint", 1)])
        _INDEXES["ready"] = True
    return _db.radar_rounds


def radar_round_add(doc: dict) -> str:
    """Insert one round. `doc` must carry a unique `stamp`. Returns the stamp."""
    d = dict(doc)
    d["id"] = _next_id("radar_rounds")
    _rounds().insert_one(d)
    return d["stamp"]


def radar_round_list(limit: int = 50) -> list:
    """Round metadata, newest first — no digest/full_json payloads.

    Ordered by the monotonic `id`, never by `created_at`: that field is an ISO
    string whose offset follows a user-changeable timezone setting, so string
    order stops being chronological the moment the setting changes.
    """
    cur = _rounds().find({}, _ROUND_META_PROJECTION).sort("id", DESCENDING).limit(limit)
    return list(cur)


def radar_round_get(stamp: str):
    return _rounds().find_one({"stamp": stamp}, {"_id": 0})


def radar_round_find_fingerprint(fingerprint: str):
    """The existing round for this exact CSV content, if any (idempotency:
    re-running on unchanged data reuses the round instead of duplicating it)."""
    return _rounds().find_one({"fingerprint": fingerprint}, _ROUND_META_PROJECTION)


def radar_round_update_packs(stamp: str, packs_json: str) -> bool:
    """Replace only the derived `packs_json` of an existing round.

    Used to backfill rankings added after a round was stored. The frozen inputs
    (digest_md, full_json, fingerprint, stamp) are never touched, so a round
    stays reproducible and comparable to the stock-radar snapshot it mirrors.
    """
    return (
        _rounds().update_one({"stamp": stamp}, {"$set": {"packs_json": packs_json}}).matched_count
        > 0
    )


def radar_round_update_meta(stamp: str, fields: dict) -> bool:
    """Overwrite a few derived metadata fields of a stored round.

    Only for values that are pure functions of the frozen `full_json` (kill
    counts, breadth). The frozen inputs — digest_md, full_json, fingerprint,
    stamp — are never touched, so a repaired round still reproduces exactly.
    """
    allowed = {"breadth_n", "kill_pct", "kill_count", "kill_label"}
    upd = {k: v for k, v in fields.items() if k in allowed}
    if not upd:
        return False
    return _rounds().update_one({"stamp": stamp}, {"$set": upd}).matched_count > 0


def radar_round_delete(stamp: str) -> bool:
    return _rounds().delete_one({"stamp": stamp}).deleted_count > 0


def radar_round_prune(keep: int) -> list:
    """Drop all but the newest `keep` rounds. Returns the deleted stamps.
    A round is ~0.7MB (digest + full state), so unbounded growth would eat an
    Atlas free tier in a few months."""
    if keep <= 0:
        return []
    old = list(
        _rounds().find({}, {"_id": 0, "stamp": 1}).sort("id", DESCENDING).skip(keep)
    )  # `id`, not `created_at` — see radar_round_list
    stamps = [d["stamp"] for d in old]
    if stamps:
        _rounds().delete_many({"stamp": {"$in": stamps}})
    return stamps
