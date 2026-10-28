"""Start the auto job shortly after boot with the server symbol list.

ZS_AUTOSTART=0 disables it; ZS_AUTOSTART_DELAY is the wait for the TradingView session to
warm up (config.JobsSettings).
"""

import logging
import threading
import time

from zservice.core.job_state import add_log, job
from zservice.domains.symbols.service import server_symbols

from . import config as jobs_config
from . import heartbeat
from .runner import run_auto_job
from .worker import start_worker


def _autostart_worker():
    """After boot: wait a bit (TradingView session warm-up), then start the auto job with the
    server symbol list if nothing is running."""
    time.sleep(jobs_config.get_settings().autostart_delay_s)
    if not _wait_for_other_container():
        return
    if job.get("status") == "running":
        return
    syms, missing = server_symbols()
    if not syms:
        add_log("[autostart] no symbols available — skipped", logging.WARNING)
        return
    if start_worker(run_auto_job, syms, 80, False):
        add_log(
            f"[autostart] auto job started with {len(syms)} server symbols"
            + (f" · {len(missing)} DB symbols lack exchange: {missing[:10]}" if missing else "")
        )
    else:
        add_log("[autostart] a job was already running — skipped")


TAKEOVER_POLL_S = 60


def _wait_for_other_container() -> bool:
    """Wait while another container's job heartbeat is fresh (rolling update overlap).
    Returns False if a job started here meanwhile."""
    announced = False
    while (owner := heartbeat.other_owner_alive()) is not None:
        if job.get("status") == "running":
            return False
        if not announced:
            add_log(f"[autostart] {owner} is still running the job — waiting to take over")
            announced = True
        time.sleep(TAKEOVER_POLL_S)
    return True


def start_if_enabled() -> None:
    if jobs_config.get_settings().autostart:
        threading.Thread(target=_autostart_worker, daemon=True).start()
