"""One job step: fetch every symbol for one timeframe, then save the batch under a single
timestamp so all symbols of the snapshot share one as-of (single-snapshot architecture)."""

import json
import logging
from datetime import datetime

from zservice.core.clock import current_tz
from zservice.core.job_state import add_log, job, stop_event
from zservice.db.repos import history as history_repo
from zservice.domains.market_data.pipeline import process_symbol

from . import config as jobs_config
from . import heartbeat


def run_step(tf, ext, symbols, rows, start_index=0):
    """Fetch symbols[start_index:] for one timeframe. Returns (ok, [failed]); updates job."""
    ok, failed, batch = 0, [], []
    job["current_tf"] = tf
    if start_index == 0:
        job["current"] = 0
    job["total"] = len(symbols)
    job["phase"] = "fetching"

    for i in range(start_index, len(symbols)):
        if stop_event.is_set():
            break
        heartbeat.beat()  # cross-container liveness (rate-limited to once a minute)
        sym, exch = symbols[i].get("symbol"), symbols[i].get("exchange")
        job["current_symbol"] = sym
        try:
            # Always a fresh fetch (never a stored result) so the batch has one as-of.
            batch.append((sym, exch, process_symbol(sym, exch, tf, ext, rows, store=False)))
            ok += 1
        except Exception as e:
            failed.append(sym)
            job["failed"].append(f"{tf}:{sym}")
            add_log(f"{tf} {sym} failed: {e}", logging.ERROR)
        job["current"] = i + 1
        if i < len(symbols) - 1:
            # Idle wait, breaks early on stop.
            stop_event.wait(jobs_config.get_settings().symbol_delay_s)

    # A stopped step saves nothing: a partial batch would mix as-of times.
    if batch and not stop_event.is_set():
        _save_batch(tf, ext, batch, failed)
    return ok, failed


def _save_batch(tf, ext, batch, failed) -> None:
    if failed:
        add_log(
            f"[{tf}] Batch fetch completed with {len(failed)} failures. "
            f"Saving {len(batch)} successful symbols with unified timestamp.",
            logging.WARNING,
        )
    else:
        add_log(
            f"[{tf}] Batch fetch completed for {len(batch)} symbols. "
            "Saving to DB with unified timestamp.",
            logging.INFO,
        )
    try:
        batch_timestamp = datetime.now(current_tz()).isoformat()
        for sym, exch, result_list in batch:
            history_repo.history_upsert(
                sym, exch, tf, ext, batch_timestamp, json.dumps(result_list)
            )
    except Exception as e:
        add_log(f"[{tf}] DB Batch save error: {e}", logging.ERROR)
