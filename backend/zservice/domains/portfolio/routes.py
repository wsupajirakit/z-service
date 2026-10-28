"""/api/portfolio routes (moved unchanged from main.py, including error handling)."""

import logging

from fastapi import APIRouter

from zservice.core.errors import ApiError
from zservice.core.schemas import RenameRequest

from . import service
from .schemas import PortfolioAdd

log = logging.getLogger("zs.portfolio")
router = APIRouter()


@router.get("/api/portfolio")
def get_portfolio():
    return service.all_portfolios()


@router.post("/api/portfolio")
def add_portfolio(req: PortfolioAdd):
    try:
        service.add(req.port_name, req.symbol, req.quantity, req.buy_price, req.action)
    except Exception as e:
        log.error("Error adding to portfolio: %s", e)
    return {"status": "ok"}


@router.delete("/api/portfolio/{port_name}/{symbol}")
def clear_portfolio_symbol(port_name: str, symbol: str):
    try:
        service.remove_symbol(port_name, symbol)
    except Exception as e:
        log.error("Error removing from portfolio: %s", e)
    return {"status": "ok"}


@router.put("/api/portfolio/{port_name}")
def rename_portfolio(port_name: str, req: RenameRequest):
    if not req.new_name or not req.new_name.strip():
        raise ApiError(400, "lists.invalid_name", "Invalid name")
    try:
        service.rename(port_name, req.new_name.strip())
    except Exception as e:
        log.error("Error renaming portfolio: %s", e)
        raise ApiError(500, "lists.rename_failed", "Error renaming portfolio") from None
    return {"status": "ok"}
