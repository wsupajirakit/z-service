"""/api/watchlist routes (moved unchanged from main.py, including their error handling:
add/remove log and still answer ok; rename answers 400/500)."""

import logging

from fastapi import APIRouter

from zservice.core.errors import ApiError
from zservice.core.schemas import RenameRequest

from . import service
from .schemas import WatchlistAdd

log = logging.getLogger("zs.watchlist")
router = APIRouter()


@router.get("/api/watchlist")
def get_watchlist():
    return service.all_lists()


@router.post("/api/watchlist")
def add_watchlist(req: WatchlistAdd):
    try:
        service.add(req.list_name, req.symbol, req.name, req.exchange)
    except Exception as e:
        log.error("Error adding to watchlist: %s", e)
    return {"status": "ok"}


@router.delete("/api/watchlist/{list_name}/{symbol}")
def remove_watchlist(list_name: str, symbol: str):
    try:
        service.remove(list_name, symbol)
    except Exception as e:
        log.error("Error removing from watchlist: %s", e)
    return {"status": "ok"}


@router.put("/api/watchlist/{list_name}")
def rename_watchlist(list_name: str, req: RenameRequest):
    if not req.new_name or not req.new_name.strip():
        raise ApiError(400, "lists.invalid_name", "Invalid name")
    try:
        service.rename(list_name, req.new_name.strip())
    except Exception as e:
        log.error("Error renaming watchlist: %s", e)
        raise ApiError(500, "lists.rename_failed", "Error renaming watchlist") from None
    return {"status": "ok"}
