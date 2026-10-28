"""/api/settings/tv_mode, /api/settings/tv_token and /api/tv/test (moved unchanged from
main.py)."""

import time

from fastapi import APIRouter

from zservice.core.errors import ApiError
from zservice.integrations.tradingview import auth
from zservice.integrations.tradingview.mode import (
    TV_MODES,
    get_tv_mode_setting,
    set_tv_mode_setting,
)

from . import service
from .schemas import TvModeRequest, TvTokenRequest

router = APIRouter()


@router.get("/api/settings/tv_mode")
def read_tv_mode():
    return {"mode": get_tv_mode_setting()}


@router.post("/api/settings/tv_mode")
def update_tv_mode(req: TvModeRequest):
    if req.mode not in TV_MODES:
        raise ApiError(400, "tv.invalid_mode", "Mode must be 1, 2, or 3")
    set_tv_mode_setting(req.mode)
    auth.reset_login()
    return {"mode": get_tv_mode_setting()}


@router.get("/api/settings/tv_token")
def read_tv_token():
    """Return token expiry info (not the token itself)."""
    return auth.token_status()


@router.post("/api/settings/tv_token")
def update_tv_token(req: TvTokenRequest):
    """Update the TradingView token in memory and the disk cache."""
    token = req.token.strip()
    if not token:
        raise ApiError(400, "tv.token_empty", "Token cannot be empty")
    exp = auth.jwt_exp(token)
    if exp <= time.time():
        raise ApiError(400, "tv.token_expired", "Token is already expired")
    auth.set_token(token, exp)
    mins_left = (exp - time.time()) / 60
    return {"status": "active", "expires_in_minutes": round(mins_left, 1)}


@router.post("/api/tv/test")
def tv_connection_test():
    return service.connection_test()
