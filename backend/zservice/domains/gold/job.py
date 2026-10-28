"""Server-side gold job: run the analysis, upload to Drive and notify Telegram per the
destination settings. The Telegram text is built in telegram.py."""

import html
from datetime import datetime

from zservice.core.clock import current_tz
from zservice.domains.settings.service import get_dest_setting
from zservice.integrations.telegram import send_telegram_message

from .analysis import _gold_analyze_core
from .export import drive_upload_gold_bundle
from .schemas import GoldAnalyzeRequest
from .state import gold_job, gold_stop_event
from .telegram import gold_job_message


def run_gold_job(req: GoldAnalyzeRequest):
    gold_job.update(
        {
            "status": "running",
            "message": "",
            "started_at": _now_iso(),
            "finished_at": None,
            "folder_link": None,
            "folder_name": None,
            "result": None,
        }
    )
    gold_stop_event.clear()
    try:
        dest = get_dest_setting()
        result = _gold_analyze_core(req)
        gold_job["result"] = result
        info = _upload(result) if dest["dest_gold_drive"] else None
        gold_job["finished_at"] = _now_iso()
        gold_job["status"] = "done"
        if info:
            gold_job["folder_link"] = info["link"]
            gold_job["folder_name"] = info["name"]
        if dest["dest_gold_telegram"]:
            send_telegram_message(gold_job_message(result, info, dest["dest_gold_drive"]))
    except Exception as e:
        gold_job.update(
            {"status": "error", "message": str(e), "finished_at": _now_iso(),
             # An ApiError's code lets the web UI translate the failure.
             "message_code": getattr(e, "code", None), "message_params": getattr(e, "params", {})}
        )  # fmt: skip
        send_telegram_message(f"❌ <b>Gold analyze error</b>\n{html.escape(str(e))}")


def _now_iso() -> str:
    return datetime.now(current_tz()).isoformat()


def _upload(result: dict) -> dict | None:
    """Drive bundle {link, name}; None when the upload failed (the job still succeeds)."""
    try:
        return drive_upload_gold_bundle(result)
    except Exception as e:
        print(f"[drive] gold upload failed: {e}")
        return None
