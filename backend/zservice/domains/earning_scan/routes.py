"""/api/earning_scan/{scan,history} (moved unchanged from main.py)."""

import json
from datetime import datetime

from fastapi import APIRouter

from zservice.core.clock import current_tz
from zservice.core.schemas import clamp
from zservice.db.repos import scans as scans_repo

from .providers import _fetch_earnings_for_symbol
from .schemas import EarningScanRequest

router = APIRouter()


@router.post("/api/earning_scan/scan")
def earning_scan_scan(req: EarningScanRequest):
    results = []
    for symbol in req.symbols:
        symbol = symbol.strip().upper()
        if not symbol:
            continue
        data = _fetch_earnings_for_symbol(symbol)
        results.append({"symbol": symbol, **data})

    stamp = datetime.now(current_tz()).isoformat()
    try:
        scans_repo.earning_add(stamp, json.dumps(req.symbols), json.dumps(results))
    except Exception as e:
        print(f"Error saving to earning_scan_history: {e}")

    return {"results": results, "timestamp": stamp}


@router.get("/api/earning_scan/history")
def earning_scan_history(limit: int = 50):
    return [
        {
            "id": r["id"],
            "timestamp": r["timestamp"],
            "symbols": json.loads(r["symbols"]) if r.get("symbols") else [],
            "results": json.loads(r["result_json"]) if r.get("result_json") else [],
        }
        for r in scans_repo.earning_list(clamp(limit, 1, 500))
    ]
