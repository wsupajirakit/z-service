"""/api/stock_radar/{scan,history}."""

from fastapi import APIRouter

from zservice.core.schemas import clamp

from . import service
from .schemas import StockRadarRequest

router = APIRouter()


@router.post("/api/stock_radar/scan")
def stock_radar_scan(req: StockRadarRequest):
    return service.run_scan(req)


@router.get("/api/stock_radar/history")
def stock_radar_history(limit: int = 50):
    return service.history(clamp(limit, 1, 500))
