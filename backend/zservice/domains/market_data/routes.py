"""POST /api/data — fetch one symbol now (moved unchanged from main.py)."""

from fastapi import APIRouter

from .pipeline import process_symbol
from .schemas import DataRequest

router = APIRouter()


@router.post("/api/data")
def get_tradingview_data(req: DataRequest):
    return process_symbol(req.symbol, req.exchange, req.interval, req.extended_session, req.rows)
