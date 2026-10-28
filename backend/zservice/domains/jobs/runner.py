"""Background fetch jobs: custom (chosen timeframes once) and auto (rounds forever with a
cooldown). Each runs on worker.start_worker; one step per timeframe is step.run_step."""

import html
import logging
from datetime import datetime, timedelta

from zservice.core.clock import current_tz
from zservice.core.job_state import add_log, job, stop_event
from zservice.integrations.telegram import send_telegram_message

from . import config as jobs_config
from .delivery import _deliver_stock_summary
from .schedule import (
    AUTO_STEPS,
    _last_tf_bar_key,
    _load_tf_bar_keys,
    _save_tf_bar_keys,
    steps_due,
)
from .step import run_step
from .summary import summary_text
from .worker import cooldown

# extended_session default per timeframe (mirrors the frontend AUTO_STEPS)
EXTENDED_DEFAULT = {"1h": True, "4h": True, "1d": False, "1w": False}
AUTO_COOLDOWN_SECONDS = 900  # 15 min rest between rounds


def _now() -> datetime:
    return datetime.now(current_tz())


def _reset_job(mode, started, timeframes, n_symbols, **extra) -> None:
    job.update(
        {
            "mode": mode,
            "status": "running",
            "round": 0,
            "timeframes": timeframes,
            "current_tf": None,
            "current_symbol": None,
            "current": 0,
            "total": n_symbols,
            "step_index": 0,
            "step_total": len(timeframes),
            "phase": "fetching",
            "cooldown_until": None,
            "failed": [],
            "started_at": started.isoformat(),
            "finished_at": None,
            "last_round_finished_at": None,
            "message": "",
            **extra,
        }
    )


def _end_job(status: str) -> datetime:
    finished = _now()
    job["status"] = status
    job["phase"] = "idle"
    job["finished_at"] = finished.isoformat()
    return finished


def _fail_job(error: Exception, label: str) -> None:
    job["status"] = "error"
    job["phase"] = "idle"
    job["message"] = str(error)
    # An ApiError's code lets the web UI translate the failure (zservice/core/errors.py).
    job["message_code"] = getattr(error, "code", None)
    job["message_params"] = getattr(error, "params", {})
    job["finished_at"] = _now().isoformat()
    send_telegram_message(f"❌ <b>{label} error</b>\n{html.escape(str(error))}")


# --- custom ---------------------------------------------------------------------------


def run_custom_job(timeframes, symbols, extended_override, rows, resume=False):
    started = _now()
    if resume:
        job.update({"status": "running", "phase": "fetching", "message": "", "finished_at": None})
        start_tf_idx, start_sym_idx = max(0, job["step_index"] - 1), job["current"]
    else:
        _reset_job(
            "custom",
            started,
            timeframes,
            len(symbols),
            custom_symbols=symbols,
            custom_extended=extended_override,
            custom_rows=rows,
        )
        start_tf_idx, start_sym_idx = 0, 0

    try:
        per_tf = []
        for idx in range(start_tf_idx, len(timeframes)):
            if stop_event.is_set():
                break
            tf = timeframes[idx]
            job["step_index"] = idx + 1
            ext = (
                EXTENDED_DEFAULT.get(tf, False) if extended_override is None else extended_override
            )
            # A resumed job restarts mid-list only on its first timeframe.
            first = start_sym_idx if idx == start_tf_idx else 0
            per_tf.append((tf, ext, *run_step(tf, ext, symbols, rows, first)))

        stopped = stop_event.is_set()
        finished = _end_job("idle")
        title = "⏹ <b>Automate หยุดแล้ว</b>" if stopped else "✅ <b>Automate เสร็จแล้ว</b>"
        summary = summary_text(title, started, finished, timeframes, per_tf, len(symbols), rows)
        # Only push a full Drive bundle when the job actually finished (not on stop).
        _deliver_stock_summary(summary, do_upload=not stopped)
    except Exception as e:
        _fail_job(e, "Automate")


# --- auto -----------------------------------------------------------------------------


def run_auto_job(symbols, rows, force_all_tf=False):
    _load_tf_bar_keys()  # restore per-TF markers so a restart resumes the cadence
    legacy = force_all_tf or jobs_config.get_settings().force_all_tf
    tfs = [tf for tf, _ in AUTO_STEPS]
    _reset_job("auto", _now(), tfs, len(symbols), csv_mode="legacy" if legacy else "default")
    if legacy:
        add_log(
            "[auto] csv mode = LEGACY — all 4 timeframes every round (for newly added symbols"
            " that have no 1d/1w bars yet)",
            logging.INFO,
        )
    try:
        while not stop_event.is_set():
            if not _auto_round(symbols, rows, force_all_tf):
                break
            _rest_between_rounds()
        _end_job("stopped")
        send_telegram_message(f"⏹ <b>Auto Automate หยุดแล้ว</b> (จบที่รอบ {job['round']})")
    except Exception as e:
        _fail_job(e, "Auto Automate")


def _auto_round(symbols, rows, force_all_tf) -> bool:
    """One round over the timeframes whose bar closed. False when stopped mid-round."""
    job["round"] += 1
    round_no = job["round"]
    job["failed"] = []
    round_started = _now()

    due, new_keys = steps_due(force_all=force_all_tf)
    due_tfs = [tf for tf, _ in due]
    job["timeframes"] = due_tfs
    job["step_total"] = len(due)
    skipped = [tf for tf, _ in AUTO_STEPS if tf not in due_tfs]
    if skipped:
        add_log(
            f"[auto] round {round_no}: fetching {due_tfs} · skipping {skipped} "
            f"(bar not closed yet) · all {len(symbols)} symbols",
            logging.INFO,
        )

    per_tf = []
    for idx, (tf, ext) in enumerate(due):
        if stop_event.is_set():
            break
        job["step_index"] = idx + 1
        per_tf.append((tf, ext, *run_step(tf, ext, symbols, rows)))
        _last_tf_bar_key[tf] = new_keys[tf]  # only mark done after the step actually ran
        _save_tf_bar_keys()  # survive a restart mid-round
    if stop_event.is_set():
        return False

    round_finished = _now()
    job["last_round_finished_at"] = round_finished.isoformat()
    title = f"✅ <b>Auto Automate — รอบที่ {round_no} เสร็จแล้ว</b>"
    n = len(symbols)
    _deliver_stock_summary(
        summary_text(title, round_started, round_finished, due_tfs, per_tf, n, rows),
        do_upload=True,
    )
    return True


def _rest_between_rounds() -> None:
    """Cooldown: one efficient blocking wait (~0 CPU), wakes early on stop."""
    job["phase"] = "cooldown"
    job["cooldown_until"] = (_now() + timedelta(seconds=AUTO_COOLDOWN_SECONDS)).isoformat()
    cooldown(AUTO_COOLDOWN_SECONDS)
    job["phase"] = "fetching"
    job["cooldown_until"] = None
