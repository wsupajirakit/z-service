"""Where a finished stock job's results go: Drive CSV bundle and/or Telegram, per the
destination settings (moved unchanged from main.py)."""

from datetime import datetime

from zservice.core.clock import current_tz, tz_suffix
from zservice.domains.exports.formula_csv import build_formula_csv_bytes
from zservice.domains.exports.selection import fetch_export_rows
from zservice.domains.exports.stock_csv import build_export_csv_bytes
from zservice.domains.settings.service import get_dest_setting
from zservice.integrations import drive
from zservice.integrations.drive import (
    drive_create_subfolder,
    drive_folder_link,
    drive_upload_bytes,
)
from zservice.integrations.telegram import send_telegram_message


def drive_upload_stock_bundle() -> dict | None:
    """Create a timestamped folder and upload the 8 stock CSVs + formula into it.

    Returns {"folder_id", "link", "name", "count"} or None if Drive isn't
    configured (so a missing setup never breaks the automate job).
    """
    if not drive.configured():
        print("[drive] not configured; skipping stock upload")
        return None
    stamp = datetime.now(current_tz()).strftime("%Y-%m-%d_%H-%M-%S")
    folder_name = f"stock_{stamp}_{tz_suffix()}"
    folder = drive_create_subfolder(folder_name)
    fid = folder["id"]

    # Formula first, then every timeframe's two parts (same set as the export zip).
    drive_upload_bytes("ztrade_formula.csv", build_formula_csv_bytes(), "text/csv", fid)
    count = 1
    for itv in ["1w", "1d", "4h", "1h"]:
        itv_rows = fetch_export_rows(itv)  # query Mongo once, reuse for both parts
        drive_upload_bytes(
            f"ztrade_export_{itv}_part1.csv",
            build_export_csv_bytes(itv, 1, rows=itv_rows),
            "text/csv",
            fid,
        )
        drive_upload_bytes(
            f"ztrade_export_{itv}_part2.csv",
            build_export_csv_bytes(itv, 2, rows=itv_rows),
            "text/csv",
            fid,
        )
        count += 2
    return {"folder_id": fid, "link": drive_folder_link(fid), "name": folder_name, "count": count}


def _deliver_stock_summary(summary: str, do_upload: bool):
    """Deliver a finished stock summary according to the destination settings.

    - dest_stock_drive: upload the CSV bundle (only when do_upload) and append the
      folder link to the summary.
    - dest_stock_telegram: send the (possibly link-augmented) summary to Telegram.
    Never raises — a Drive failure must not break the automate job.
    """
    dest = get_dest_setting()
    if do_upload and dest["dest_stock_drive"]:
        try:
            info = drive_upload_stock_bundle()
            if info:
                summary += (
                    f"\n\n📁 Drive ({info['count']} ไฟล์): "
                    f'<a href="{info["link"]}">{info["name"]}</a>'
                )
        except Exception as e:
            print(f"[drive] stock upload failed: {e}")
            summary += f"\n\n📁 Drive: อัปโหลดไม่สำเร็จ ({e})"
    if dest["dest_stock_telegram"]:
        send_telegram_message(summary)
