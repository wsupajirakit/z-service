"""Cross-container liveness of the auto job (plan item B12).

During a rolling update Coolify runs the old and the new container side by side. Without
coordination the new one's autostart would launch a second auto job while the old one is
still fetching — double TradingView load. The running job writes a heartbeat (owner +
time) to the settings collection at most once a minute; autostart waits while another
owner's heartbeat is fresh and takes over once it goes stale.
"""

import contextlib
import json
import os
import socket
import threading
import time

from zservice.db.repos import settings as settings_repo

from . import config as jobs_config

KEY = "automate_heartbeat"
WRITE_EVERY_S = 60
OWNER = f"{socket.gethostname()}:{os.getpid()}"

_last_write = {"at": 0.0}
_lock = threading.Lock()


def beat(force: bool = False) -> None:
    """Record that this process is running the job (rate-limited; never raises)."""
    now = time.time()
    with _lock:
        if not force and now - _last_write["at"] < WRITE_EVERY_S:
            return
        _last_write["at"] = now
    with contextlib.suppress(Exception):  # a missed beat only delays a takeover by a minute
        settings_repo.settings_set(KEY, json.dumps({"owner": OWNER, "at": now}))


def clear() -> None:
    with contextlib.suppress(Exception):  # stale-by-age works even if this write is lost
        settings_repo.settings_set(KEY, json.dumps({"owner": OWNER, "at": 0}))


def other_owner_alive(now: float | None = None) -> str | None:
    """Owner id of another process with a fresh heartbeat, else None."""
    try:
        raw = settings_repo.settings_get(KEY)
        data = json.loads(raw) if raw else {}
    except Exception:
        return None
    owner, at = data.get("owner"), float(data.get("at") or 0)
    now = time.time() if now is None else now
    if owner and owner != OWNER and now - at < jobs_config.get_settings().heartbeat_stale_s:
        return owner
    return None
