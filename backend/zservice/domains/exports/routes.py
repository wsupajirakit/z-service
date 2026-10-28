"""/api/export, /api/export/check, /api/export_formula, /api/export_news, /api/export_zip
(moved unchanged from main.py)."""

import io

from fastapi import APIRouter, Response

from zservice.core.errors import ApiError
from zservice.db.repos import history as history_repo
from zservice.db.repos import watchlist as watchlist_repo
from zservice.integrations.tradingview.intervals import INTERVAL_MAP

from .formula_csv import build_formula_csv_bytes
from .news_csv import build_news_csv_bytes
from .selection import fetch_export_rows
from .stock_csv import build_export_csv_bytes

router = APIRouter()


@router.get("/api/export/check")
def export_check(interval: str, list_name: str):
    names = (
        [n.strip() for n in list_name.split(",")] if list_name and "," in list_name else list_name
    )

    if list_name == "All Symbols":
        history_symbols = set(history_repo.history_distinct_symbols(interval))
        available = list(history_symbols)
        return {
            "total_in_list": len(available),
            "available_count": len(available),
            "missing_count": 0,
            "missing_symbols": [],
        }

    watchlist_symbols = watchlist_repo.watchlist_symbols(names)
    history_symbols = set(history_repo.history_distinct_symbols(interval, names))

    available = [s for s in watchlist_symbols if s in history_symbols]
    missing = [s for s in watchlist_symbols if s not in history_symbols]

    return {
        "total_in_list": len(watchlist_symbols),
        "available_count": len(available),
        "missing_count": len(missing),
        "missing_symbols": missing,
    }


@router.get("/api/export")
def export_csv(interval: str, part: int = 1, list_name: str | None = None):
    if interval not in INTERVAL_MAP:
        raise ApiError(
            400,
            "exports.invalid_interval",
            "Invalid interval. Use 15m, 30m, 1h, 4h, 1d, or 1w.",
            params={"allowed": "15m, 30m, 1h, 4h, 1d, 1w"},
        )

    csv_content = build_export_csv_bytes(interval, part, list_name)

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=ztrade_export_{interval}_part{part}.csv"
        },
    )


@router.get("/api/export_formula")
def export_formula():
    csv_content = build_formula_csv_bytes()
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=ztrade_formula.csv"},
    )


@router.get("/api/export_news")
def export_news():
    csv_content = build_news_csv_bytes()
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=ztrade_news.csv"},
    )


@router.get("/api/export_zip")
def export_zip(interval: str | None = None, all: bool = False, list_name: str | None = None):
    """Bundle the export CSV(s) + formula into a single ZIP.

    Mobile browsers (esp. iOS Safari) allow only one download per tap and handle
    blob downloads poorly, so the frontend hits this single
    URL instead of firing several sequential downloads.

    - all=true  -> all 4 timeframes (1w, 1d, 4h, 1h) part1+part2 + formula (9 files)
    - interval=x -> that interval part1+part2 + formula (3 files)
    """
    if all:
        intervals = ["1w", "1d", "4h", "1h"]
        zip_name = "ztrade_export_all.zip"
    else:
        if interval not in INTERVAL_MAP:
            raise ApiError(
                400,
                "exports.invalid_interval",
                "Invalid interval. Use 15m, 30m, 1h, 4h, 1d, or 1w.",
                params={"allowed": "15m, 30m, 1h, 4h, 1d, 1w"},
            )
        intervals = [interval]
        zip_name = f"ztrade_export_{interval}.zip"

    import zipfile

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        # Formula first so it leads the bundle (matches the "9 files" ordering)
        zf.writestr("ztrade_formula.csv", build_formula_csv_bytes())
        for itv in intervals:
            # Query Mongo once per interval; build both parts from the same rows.
            itv_rows = fetch_export_rows(itv, list_name)
            zf.writestr(
                f"ztrade_export_{itv}_part1.csv",
                build_export_csv_bytes(itv, 1, list_name, rows=itv_rows),
            )
            zf.writestr(
                f"ztrade_export_{itv}_part2.csv",
                build_export_csv_bytes(itv, 2, list_name, rows=itv_rows),
            )

    return Response(
        content=buf.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={zip_name}"},
    )
