"""Process-wide state of the fetch job (moved unchanged from main.py).

Lives in core, not domains/jobs, because the TradingView client (an integration) also logs
through add_log and honours stop_event; integrations must not import domains.

`job` is mutated in place by the runner and read by /api/automate/status; nothing may
rebind it. `stop_event` stays set between jobs on purpose (see the TradingView throttle).
"""

import logging
import threading
from datetime import datetime

from zservice.core.logging import logger

JOB_LOG_LIMIT = 50  # lines kept in job["logs"] for the status endpoint

job_lock = threading.Lock()
stop_event = threading.Event()

job = {
    "mode": "idle",  # idle | custom | auto
    "status": "idle",  # idle | running | done | error | stopped
    "round": 0,  # auto: current round number (1-based while running)
    "timeframes": [],
    "current_tf": None,
    "current_symbol": None,
    "current": 0,  # symbols done in the current step
    "total": 0,  # symbols in the current step
    "step_index": 0,  # 1-based step within the round
    "step_total": 0,
    "phase": "idle",  # idle | fetching | cooldown
    "cooldown_until": None,  # ISO ts; frontend derives the countdown from this
    "failed": [],  # ["tf:SYM", ...] for the current run/round
    "started_at": None,
    "finished_at": None,
    "last_round_finished_at": None,
    "message": "",
    "logs": [],
    "custom_symbols": [],
    "custom_extended": False,
    "custom_rows": 40,
}


def add_log(msg: str, level=logging.INFO) -> None:
    """Log to the "automate" logger and keep the line for the status endpoint."""
    if level == logging.ERROR:
        logger.error(msg)
    elif level == logging.WARNING:
        logger.warning(msg)
    else:
        logger.info(msg)
    ts = datetime.now().strftime("%H:%M:%S")
    job["logs"].append(f"[{ts}] {msg}")
    if len(job["logs"]) > JOB_LOG_LIMIT:
        job["logs"].pop(0)
