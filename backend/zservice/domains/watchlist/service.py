"""Watchlist reads and writes (moved unchanged from main.py)."""

from zservice.core.clock import now_iso
from zservice.db.repos import watchlist as watchlist_repo


def group_by_list(rows: list[dict]) -> dict[str, list[dict]]:
    """{list_name: [{symbol, name, timestamp}, ...]} in stored order."""
    lists: dict[str, list[dict]] = {}
    for r in rows:
        lists.setdefault(r["list_name"], []).append(
            {"symbol": r["symbol"], "name": r["name"], "timestamp": r["timestamp"]}
        )
    return lists


def all_lists() -> dict[str, list[dict]]:
    return group_by_list(watchlist_repo.watchlist_all())


def add(list_name: str, symbol: str, name: str, exchange: str | None) -> None:
    watchlist_repo.watchlist_add(
        list_name, symbol, name, now_iso(), exchange=(exchange or "").strip().upper() or None
    )


def remove(list_name: str, symbol: str) -> None:
    watchlist_repo.watchlist_remove(list_name, symbol)


def rename(list_name: str, new_name: str) -> None:
    watchlist_repo.watchlist_rename(list_name, new_name)
