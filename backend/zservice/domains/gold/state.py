"""Process-wide state of the gold job (moved unchanged from main.py)."""

import threading

gold_job_lock = threading.Lock()
gold_stop_event = threading.Event()
gold_job = {
    "status": "idle",
    "message": "",
    "started_at": None,
    "finished_at": None,
    "folder_link": None,
    "folder_name": None,
    "result": None,
}
