"""The background thread a job runs on (single-flight) and the cooldown between rounds."""

import threading
import time

from zservice.core.job_state import job_lock, stop_event

from . import heartbeat


def start_worker(target, *args) -> bool:
    """Run target(*args) on a daemon thread. False when a job (custom or auto) is running."""
    if not job_lock.acquire(blocking=False):
        return False
    stop_event.clear()

    def _runner():
        try:
            heartbeat.beat(force=True)
            target(*args)
        finally:
            heartbeat.clear()
            stop_event.clear()
            job_lock.release()

    threading.Thread(target=_runner, daemon=True).start()
    return True


def cooldown(seconds: float) -> None:
    """Rest between auto rounds: wakes early on stop and keeps the heartbeat fresh."""
    deadline = time.monotonic() + seconds
    while not stop_event.is_set():
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return
        heartbeat.beat()
        stop_event.wait(min(remaining, heartbeat.WRITE_EVERY_S))
