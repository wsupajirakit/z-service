"""/api/settings/{timezone,destinations,auto_skip_minutes} — moved unchanged from main.py.

The tv_mode and tv_token routes stay in main.py until the TradingView client moves,
because they reset its in-memory login state.
"""

from fastapi import APIRouter

from zservice.core.errors import ApiError

from . import service
from .schemas import AutoSkipMinutesRequest, DestinationsRequest, TimezoneRequest

router = APIRouter()


@router.get("/api/settings/timezone")
def read_timezone():
    return service.get_tz_setting()


@router.post("/api/settings/timezone")
def update_timezone(req: TimezoneRequest):
    low, high = service.TZ_OFFSET_RANGE_MIN
    if not (low <= req.offset_minutes <= high):
        raise ApiError(
            400,
            "settings.offset_range",
            "offset_minutes must be between -720 and 840.",
            params={"min": -720, "max": 840},
        )
    label = req.label.strip()[: service.TZ_LABEL_MAX_LEN] or service.DEFAULT_TZ_LABEL
    service.set_tz_setting(req.offset_minutes, label)
    return service.get_tz_setting()


@router.get("/api/settings/destinations")
def read_destinations():
    return service.get_dest_setting()


@router.post("/api/settings/destinations")
def update_destinations(req: DestinationsRequest):
    service.set_dest_setting({k: v for k, v in req.model_dump().items() if v is not None})
    return service.get_dest_setting()


@router.get("/api/settings/auto_skip_minutes")
def read_auto_skip_minutes():
    return {"minutes": service.get_auto_skip_minutes_setting()}


@router.post("/api/settings/auto_skip_minutes")
def update_auto_skip_minutes(req: AutoSkipMinutesRequest):
    low, high = service.AUTO_SKIP_RANGE
    if not (low <= req.minutes <= high):
        raise ApiError(
            400,
            "settings.minutes_range",
            "Minutes must be between 1 and 100",
            params={"min": 1, "max": 100},
        )
    service.set_auto_skip_minutes_setting(req.minutes)
    return {"minutes": service.get_auto_skip_minutes_setting()}
