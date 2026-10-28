"""/api/history routes (moved unchanged from main.py).

The cleanup response keeps the legacy Thai `message` the old dashboard shows; the new web
UI builds its own text from `deleted` and the requested hours via its message files.
"""

from fastapi import APIRouter

from zservice.core.errors import ApiError

from . import service

router = APIRouter()

# Codes this module returns in plain response dicts (for the translation check).
MESSAGE_CODES = {"history.cleared": (), "history.cleaned": ("deleted", "hours")}


@router.get("/api/history")
def get_history():
    return service.summary_rows()


@router.get("/api/history/{history_id}")
def get_history_detail(history_id: int):
    result = service.detail(history_id)
    if result is None:
        raise ApiError(404, "history.not_found", "History record not found")
    return result


@router.delete("/api/history")
def clear_history():
    service.clear_all()
    return {"status": "success", "message": "History cleared", "code": "history.cleared"}


@router.post("/api/history/cleanup")
def cleanup_history(hours: int = 2):
    low, high = service.CLEANUP_HOURS_RANGE
    if not (low <= hours <= high):
        raise ApiError(
            400,
            "history.hours_range",
            "hours must be between 1 and 720.",
            params={"min": 1, "max": 720},
        )
    result = service.cleanup(hours)
    message = f"ลบ {result['deleted']} แถวที่เก่ากว่า {hours} ชม. (เก็บล่าสุดต่อ symbol ไว้)"
    params = {"deleted": result["deleted"], "hours": hours}
    return {"status": "success", **result, "message": message, "code": "history.cleaned",
            "params": params}  # fmt: skip
