"""/api/gold/{config,price,models,analyze,automate,automate/stop,status} (moved unchanged
from main.py). The standalone gold *mode* routes (/api/gold/export, /api/gold/modes) are
still in backend/gold.py."""

import json
import threading
import urllib.parse
import urllib.request

from fastapi import APIRouter

from zservice.core.errors import ApiError
from zservice.domains.market_data.pipeline import process_symbol
from zservice.integrations import gemini
from zservice.integrations.gemini import GEMINI_BASE

from .analysis import _gold_analyze_core
from .config import GOLD_DEFAULT_MODEL, GOLD_SOURCES, GOLD_TIMEFRAMES
from .job import run_gold_job
from .schemas import GoldAnalyzeRequest
from .state import gold_job, gold_job_lock, gold_stop_event

router = APIRouter()

# Codes this module returns in plain response dicts (for the translation check).
MESSAGE_CODES = {"gold.stop_sent": (), "gold.not_running": ()}


@router.get("/api/gold/config")
def gold_config():
    """Static config for the Gold tab: available broker sources and timeframes."""
    return {
        "sources": GOLD_SOURCES,
        "timeframes": GOLD_TIMEFRAMES,
        "default_model": GOLD_DEFAULT_MODEL,
    }


@router.get("/api/gold/price")
def get_gold_price(exchange: str = "OANDA"):
    """Fetch the latest price of XAUUSD from the given exchange quickly."""
    try:
        data = process_symbol("XAUUSD", exchange, "1h", extended_session=False, rows=1, store=False)
        if data:
            return {"price": data[-1].get("close")}
        return {"price": None}
    except Exception as e:
        raise ApiError(500, "gold.price_failed", str(e), params={"reason": str(e)}) from e


@router.get("/api/gold/models")
def gold_models():
    """List Gemini models that support generateContent, for the model dropdown."""
    if not gemini.configured():
        raise ApiError(400, "ai.no_api_key", "GEMINI_API_KEY is not set on the server.")
    url = f"{GEMINI_BASE}/models?pageSize=200"  # key in the header, not the URL (B14)
    try:
        req = urllib.request.Request(  # noqa: S310 — fixed https Gemini endpoint
            url, headers=gemini.auth_headers({"Accept": "application/json"})
        )
        with urllib.request.urlopen(req, timeout=15) as resp:  # noqa: S310 — fixed https
            data = json.loads(resp.read())
    except Exception as e:
        raise ApiError(
            502,
            "ai.models_failed",
            f"Failed to list Gemini models: {e}",
            params={"reason": str(e)},
        ) from e

    models = []
    for m in data.get("models", []):
        methods = m.get("supportedGenerationMethods", [])
        if "generateContent" not in methods:
            continue
        name = m.get("name", "").replace("models/", "")
        # Skip non-chat variants (tts/image/embedding/audio) — they can't do text analysis.
        if any(
            t in name
            for t in ("tts", "image", "embedding", "audio", "aqa", "imagen", "veo", "lyria")
        ):
            continue
        models.append({"name": name, "displayName": m.get("displayName", name)})

    # Sort so the recommended default surfaces first, then alphabetical.
    models.sort(key=lambda x: (x["name"] != GOLD_DEFAULT_MODEL, x["name"]))
    return {"models": models, "default": GOLD_DEFAULT_MODEL}


@router.post("/api/gold/analyze")
def gold_analyze(req: GoldAnalyzeRequest):
    """Fetch XAUUSD across multiple timeframes + latest news, then ask Gemini for a
    short-term (day/swing) entry plan with a concrete Long/Short strategy."""
    return _gold_analyze_core(req)


@router.post("/api/gold/automate/stop")
def stop_gold_job():
    if gold_job["status"] == "running":
        gold_stop_event.set()
        return {"detail": "Stop signal sent", "code": "gold.stop_sent"}
    return {"detail": "No job running", "code": "gold.not_running"}


@router.post("/api/gold/automate")
def start_gold_job(req: GoldAnalyzeRequest):
    """Kick off a server-side gold analysis (async). Notifies Telegram + uploads
    the result to a timestamped Drive folder when done."""
    if not gold_job_lock.acquire(blocking=False):
        since = gold_job.get("started_at")
        raise ApiError(
            409,
            "gold.already_running",
            f"A gold job is already running (started {since})."
            if since
            else "A gold job is already running.",
            params={"started_at": since or ""},
        )

    def _runner():
        try:
            run_gold_job(req)
        finally:
            gold_stop_event.clear()
            gold_job_lock.release()

    threading.Thread(target=_runner, daemon=True).start()
    return {"status": "started", "mode": "gold", "exchange": req.exchange}


@router.get("/api/gold/status")
def gold_status():
    return gold_job
