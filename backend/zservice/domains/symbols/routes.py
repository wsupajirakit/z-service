"""GET /api/symbols and GET /api/version."""

from fastapi import APIRouter

from zservice.core.job_state import job
from zservice.domains.jobs import config as jobs_config

from .service import load_build_symbols, server_symbols, version_info

router = APIRouter()


@router.get("/api/symbols")
def get_symbols():
    syms, missing = server_symbols()
    build = load_build_symbols()
    db_extra = len(syms) - len({s["symbol"] for s in build})
    return {
        "count": len(syms),
        "symbols": syms,
        "missing_exchange": missing,
        "sources": {"build": len(build), "db_extra": db_extra},
    }


@router.get("/api/version")
def get_version():
    syms, missing = server_symbols()
    return {
        **version_info(),
        "symbols_count": len(syms),
        "build_symbols": len(load_build_symbols()),
        "missing_exchange": missing,
        "job_phase": job.get("phase"),
        "job_round": job.get("round"),
        "job_total": job.get("total"),
        "autostart": jobs_config.get_settings().autostart,
    }
