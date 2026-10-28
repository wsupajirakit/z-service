"""Radar Summary API — compute a radar "round" and browse past rounds.

Self-contained router (mounted by zservice/app.py, protected by the app-wide auth
middleware like every other /api route). It touches nothing that already
exists: no existing endpoint changes behaviour, and the CSV export path is
reused read-only through radar_engine.rounds.

    POST   /api/radar_round/run        start a round (409 if one is running)
    GET    /api/radar_round/status     progress of the running/last round
    GET    /api/radar_round/tf_status  what is stored per timeframe right now
    GET    /api/radar_round/list       past rounds, newest first (metadata only)
    GET    /api/radar_round/{stamp}    one round in full (digest + state + packs)
    DELETE /api/radar_round/{stamp}    drop a round

Route order matters: the literal paths are declared before /{stamp} so FastAPI
never matches "status" as a stamp.
"""

import json

from fastapi import APIRouter
from radar_engine import rounds

from zservice.core.errors import ApiError
from zservice.core.schemas import clamp
from zservice.db.repos import radar_rounds as radar_rounds_repo

from .schemas import RoundRequest

router = APIRouter(prefix="/api/radar_round", tags=["radar_round"])


@router.post("/run")
def start_round(req: RoundRequest):
    try:
        started = rounds.start_round(req.timeframes, req.list_name, req.new_record)
    except rounds.RadarError as e:
        raise ApiError(400, "radar.invalid_request", str(e), params={"reason": str(e)}) from e
    if not started:
        job = rounds.round_status()
        raise ApiError(
            409,
            "radar.already_running",
            f"A radar round is already running (started {job.get('started_at')}).",
            params={"started_at": job.get("started_at") or ""},
        )
    return rounds.round_status()  # same shape as /status, so the UI can poll on from here


@router.get("/status")
def round_status():
    return rounds.round_status()


@router.get("/tf_status")
def tf_status(list_name: str | None = None):
    """Per-timeframe freshness — read this BEFORE running a round: it says how
    many symbols each timeframe holds and when that data was written to the DB."""
    return rounds.tf_status(list_name)


@router.get("/list")
def list_rounds(limit: int = 30):
    # The round picker reads kill% from here; rounds stored by buggy code (kill% in the
    # tens of thousands) are repaired from their frozen state before being returned.
    rounds = [
        rounds.repair_round_meta(r)
        for r in radar_rounds_repo.radar_round_list(clamp(limit, 1, 200))
    ]
    return {"rounds": rounds}


@router.get("/{stamp}")
def get_round(stamp: str):
    doc = radar_rounds_repo.radar_round_get(stamp)
    if not doc:
        raise ApiError(404, "radar.not_found", f"no round {stamp}", params={"stamp": stamp})
    # Rounds stored by older code get their packs recomputed here from the frozen state:
    # same formulas, only fields added later (e.g. the 3 answers, bar wait times) appear.
    doc = rounds.ensure_packs_current(doc)
    # Stored as JSON strings (BSON-safe ticker keys); handed back parsed so the
    # page renders tables straight from the object.
    doc["full"] = json.loads(doc.pop("full_json", "null") or "null")
    doc["packs"] = json.loads(doc.pop("packs_json", "null") or "null")
    return doc


@router.delete("/{stamp}")
def delete_round(stamp: str):
    if not radar_rounds_repo.radar_round_delete(stamp):
        raise ApiError(404, "radar.not_found", f"no round {stamp}", params={"stamp": stamp})
    return {"status": "deleted", "stamp": stamp}
