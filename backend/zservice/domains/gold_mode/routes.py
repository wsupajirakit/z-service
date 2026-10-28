"""/api/gold/export and /api/gold/modes (logic in service.py)."""

from fastapi import APIRouter
from fastapi.responses import Response

from . import service

router = APIRouter()


@router.get("/api/gold/export")
def gold_export(mode: str = "swing", exchange: str = "ICMARKETS"):
    mode, exchange = service.validate(mode, exchange)
    data, from_cache = service.export_zip(mode, exchange)
    return Response(
        content=data,
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename=gold_{mode}.zip",
            "X-Gold-Cache": "hit" if from_cache else "miss",
        },
    )


@router.get("/api/gold/modes")
def gold_modes():
    return service.modes_listing()
