"""History reads and maintenance (moved unchanged from main.py)."""

import json
from datetime import datetime, timedelta

from zservice.core.clock import current_tz
from zservice.db.repos import history as history_repo

CLEANUP_HOURS_RANGE = (1, 720)


def summary_rows() -> list[dict]:
    return [
        {
            "id": row["id"],
            "timestamp": row["timestamp"],
            "symbol": row["symbol"],
            "exchange": row["exchange"],
            "interval": row["interval"],
            "extended_session": bool(row["extended_session"]),
        }
        for row in history_repo.history_list()
    ]


def detail(history_id: int):
    """Stored bars for one snapshot, or None when the id does not exist."""
    result_json = history_repo.history_get_result(history_id)
    return None if result_json is None else json.loads(result_json)


def clear_all() -> None:
    history_repo.history_delete_all()


def cleanup(hours: int) -> dict:
    """Delete rows older than `hours` but keep the newest row per (symbol, interval), so
    the export never loses a symbol. Every fetch appends a row and only the latest
    snapshot is used downstream, so this bounds DB growth."""
    cutoff = (datetime.now(current_tz()) - timedelta(hours=hours)).isoformat()
    before = history_repo.history_count()
    deleted = history_repo.history_cleanup(cutoff)
    after = history_repo.history_count()
    return {"deleted": deleted, "rows_before": before, "rows_after": after, "cutoff": cutoff}
