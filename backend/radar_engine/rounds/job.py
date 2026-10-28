"""One round at a time in the background (a round is minutes of Mongo reads + a full
screen): own lock, own status dict, polled by the UI.

The status carries `message` (the legacy UI's text) next to `message_code` and
`message_params`, which the web UI translates (zservice/core/messages.py).
"""

import threading

from zservice.core.messages import coded

from . import compute
from . import config as rounds_config
from .clock import now_iso
from .csv_set import normalize_timeframes

radar_job_lock = threading.Lock()
radar_job: dict = {
    "status": "idle",  # idle | running | done | error
    "phase": "",  # building | screening | saving
    "message": "",
    "message_code": None,
    "message_params": {},
    "timeframes": [],
    "list_name": None,
    "stamp": None,
    "reused": False,
    "started_at": None,
    "finished_at": None,
}
_PRUNED_SHOWN = 3


def round_status() -> dict:
    return dict(radar_job)


def start_round(timeframes=None, list_name: str | None = None, new_record: bool = False) -> bool:
    """Kick off a round in the background. False = a round is already running."""
    tfs = normalize_timeframes(timeframes)  # validate BEFORE taking the lock
    if not radar_job_lock.acquire(blocking=False):
        return False
    radar_job.update(
        {
            "status": "running",
            "phase": "building",
            "timeframes": tfs,
            "list_name": list_name or None,
            "stamp": None,
            "reused": False,
            "started_at": now_iso(),
            "finished_at": None,
        }
    )
    _say(coded("radar.started", "เริ่มรอบใหม่"))
    try:
        worker = threading.Thread(target=_run, args=(tfs, list_name, new_record), daemon=True)
        worker.start()
    except BaseException:
        # The thread never started, so nothing will ever release the lock.
        radar_job.update({"status": "error", "phase": "", "finished_at": now_iso()})
        _say(coded("radar.thread_failed", "เริ่ม thread ไม่สำเร็จ"))
        radar_job_lock.release()
        raise
    return True


def _run(tfs, list_name, new_record) -> None:
    try:
        res = compute.run_round(tfs, list_name, progress=_progress, new_record=new_record)
        radar_job.update(
            {"status": "done", "phase": "", "stamp": res["stamp"], "reused": res["reused"]}
        )
        _say(_done_message(res))
    except BaseException as e:
        # BaseException, not Exception: lib.run_screen raises SystemExit when it finds no
        # CSVs, and SystemExit is swallowed silently in a worker thread. Leaving status at
        # "running" would disable the button and spin the poller for every user.
        reason = str(e) or e.__class__.__name__
        radar_job.update({"status": "error", "phase": ""})
        _say(coded("radar.failed", reason, reason=reason))
    finally:
        radar_job["finished_at"] = now_iso()
        radar_job_lock.release()


def _progress(phase: str, message: dict) -> None:
    radar_job["phase"] = phase
    _say(message)


def _say(message: dict) -> None:
    radar_job["message"] = message["text"]
    radar_job["message_code"] = message["code"]
    radar_job["message_params"] = message["params"]


def _done_message(res: dict) -> dict:
    if res["reused"]:
        return coded("radar.reused", "ข้อมูลไม่เปลี่ยนจากรอบก่อน — ใช้รอบเดิม")
    # Say it out loud when the retention cap deletes old rounds — silently dropping the
    # user's history would be a nasty surprise.
    dropped = res.get("pruned") or []
    if not dropped:
        return coded("radar.done", "เสร็จแล้ว")
    shown = ", ".join(dropped[:_PRUNED_SHOWN]) + ("..." if len(dropped) > _PRUNED_SHOWN else "")
    keep = rounds_config.get_settings().keep_rounds
    text = f"เสร็จแล้ว · เก็บได้สูงสุด {keep} รอบ จึงลบรอบเก่าสุด {len(dropped)} รอบ ({shown})"
    return coded("radar.done_pruned", text, keep=keep, count=len(dropped), stamps=shown)
