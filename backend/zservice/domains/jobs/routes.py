"""/api/automate, /api/auto/{start,stop,start_all}, /api/automate/status (moved unchanged
from main.py)."""

from fastapi import APIRouter

from zservice.core.errors import ApiError
from zservice.core.job_state import add_log, job, stop_event
from zservice.domains.symbols.service import server_symbols
from zservice.integrations.tradingview.intervals import INTERVAL_MAP

from .runner import run_auto_job, run_custom_job
from .schemas import AutomateRequest, AutoRequest
from .worker import start_worker

router = APIRouter()


@router.post("/api/automate")
def start_automate(req: AutomateRequest):
    valid = [tf for tf in req.timeframes if tf in INTERVAL_MAP]
    if not valid:
        raise ApiError(
            400,
            "jobs.no_timeframes",
            "No valid timeframes. Use 1h, 4h, 1d, 1w.",
            params={"allowed": "1h, 4h, 1d, 1w"},
        )
    if not req.symbols:
        raise ApiError(400, "jobs.no_symbols", "No symbols provided.")
    if not start_worker(run_custom_job, valid, req.symbols, req.extended_session, req.rows, False):
        raise ApiError(409, "jobs.already_running", "A job is already running.")
    return {"status": "started", "mode": "custom", "timeframes": valid, "symbols": len(req.symbols)}


@router.post("/api/auto/start")
def start_auto(req: AutoRequest):
    if not req.symbols:
        raise ApiError(400, "jobs.no_symbols", "No symbols provided.")
    if not start_worker(run_auto_job, req.symbols, req.rows, req.force_all_tf):
        raise ApiError(409, "jobs.already_running", "A job is already running.")
    return {
        "status": "started",
        "mode": "auto",
        "symbols": len(req.symbols),
        "csv_mode": "legacy" if req.force_all_tf else "default",
    }


@router.post("/api/auto/stop")
def stop_auto():
    stop_event.set()
    return {"status": "stopping"}


@router.get("/api/automate/status")
def automate_status():
    return job


@router.post("/api/auto/start_all")
def start_auto_all():
    """Start the auto job with the SERVER symbol list (no frontend involved)."""
    syms, _ = server_symbols()
    if not syms:
        raise ApiError(400, "jobs.server_list_empty", "server symbol list is empty")
    if not start_worker(run_auto_job, syms, 80, False):
        raise ApiError(409, "jobs.already_running", "A job is already running.")
    add_log(f"[auto] started from server symbol list ({len(syms)} symbols)")
    return {"status": "started", "mode": "auto", "symbols": len(syms)}
