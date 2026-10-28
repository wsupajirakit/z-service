"""Symbol list + build metadata readers (moved unchanged from main.py)."""

import json
import logging

from zservice.core.job_state import add_log
from zservice.db.repos import watchlist as watchlist_repo

from . import config as symbols_config

_DEV_VERSION = {"version": "dev", "commit": "unknown", "build_time": None}


def load_build_symbols() -> list[dict]:
    try:
        with open(symbols_config.get_settings().symbols_path(), encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def version_info() -> dict:
    settings = symbols_config.get_settings()
    try:
        with open(settings.version_path(), encoding="utf-8") as f:
            info = json.load(f)
    except Exception:
        info = dict(_DEV_VERSION)
    if info.get("commit") in (None, "", "unknown") and settings.source_commit:
        info["commit"] = settings.source_commit[:12]
    return info


def server_symbols() -> tuple[list[dict], list[str]]:
    """Union of build-time symbols and DB watchlist symbols (those with an exchange).
    Returns (symbols[{symbol,name,exchange}], missing_exchange[sym])."""
    out: dict[str, dict] = {}
    for s in load_build_symbols():
        sym = str(s.get("symbol", "")).strip().upper()
        if sym and s.get("exchange"):
            out[sym] = {"symbol": sym, "name": s.get("name") or sym, "exchange": s["exchange"]}
    missing: list[str] = []
    try:
        for r in watchlist_repo.watchlist_all():
            sym = str(r.get("symbol", "")).strip().upper()
            if not sym or sym in out:
                continue
            ex = (r.get("exchange") or "").strip().upper()
            if ex:
                out[sym] = {"symbol": sym, "name": r.get("name") or sym, "exchange": ex}
            elif sym not in missing:
                missing.append(sym)
    except Exception as e:  # DB down -> still serve the build list
        add_log(f"[symbols] watchlist read failed: {e}", logging.WARNING)
    return sorted(out.values(), key=lambda x: x["symbol"]), sorted(missing)
