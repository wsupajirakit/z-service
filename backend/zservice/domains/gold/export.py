"""Gold result -> CSV, and the timestamped Drive upload (moved unchanged from main.py)."""

import csv
import io
from datetime import datetime

from zservice.core.clock import current_tz, tz_suffix
from zservice.integrations import drive
from zservice.integrations.drive import (
    drive_create_subfolder,
    drive_folder_link,
    drive_upload_bytes,
)


def _build_gold_csv_bytes(result: dict, stamp: str) -> bytes:
    """Build a gold analysis CSV (Section, Key, Value) — same shape as the formula
    export so it imports cleanly. Includes the AI analysis + the input data."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Section", "Key", "Value"])

    # META
    writer.writerow(["META", "Symbol", "XAUUSD"])
    writer.writerow(["META", "Source", result.get("source_label", "")])
    writer.writerow(["META", "Model", result.get("model", "")])
    writer.writerow(["META", "Latest Price", result.get("latest_price", "")])
    writer.writerow(["META", "Timeframes", " / ".join(result.get("timeframes", []))])
    writer.writerow(["META", "News Count", result.get("news_count", "")])
    writer.writerow(["META", "Generated At", f"{stamp} ({tz_suffix()})"])

    # CROSS-MARKET (macro bias inputs)
    for k, label in [
        ("dxy_level", "DXY"),
        ("us10y_yield", "US10Y"),
        ("vix_level", "VIX"),
        ("silver_price", "Silver (XAGUSD)"),
    ]:
        writer.writerow(["CROSS_MARKET", label, (result.get("cross_market") or {}).get(k, "N/A")])

    # INPUT_INDICATOR (per-TF snapshots fed to the model)
    for key, label in [
        ("ema", "EMA"),
        ("momentum", "Momentum"),
        ("volume", "Volume"),
        ("volatility", "Volatility"),
    ]:
        for line in str((result.get("snapshots") or {}).get(key, "")).splitlines():
            if line.strip():
                writer.writerow(["INPUT_INDICATOR", label, line])

    # ANALYSIS (Gemini output) — one row per line so it stays readable in a cell grid
    for line in (result.get("analysis") or "").splitlines():
        if line.strip():
            writer.writerow(["ANALYSIS", "", line])

    # INPUT_TECHNICAL (the multi-TF bar summaries fed to the model)
    for block in result.get("tf_blocks", []):
        for line in str(block).splitlines():
            if line.strip():
                writer.writerow(["INPUT_TECHNICAL", "", line])

    # INPUT_NEWS (headlines fed to the model)
    for line in result.get("news_lines", []):
        writer.writerow(["INPUT_NEWS", "", line])

    return output.getvalue().encode("utf-8-sig")


def drive_upload_gold_bundle(result: dict) -> dict | None:
    """Create a timestamped gold folder and upload the analysis as a CSV."""
    if not drive.configured():
        print("[drive] not configured; skipping gold upload")
        return None
    stamp = datetime.now(current_tz()).strftime("%Y-%m-%d_%H-%M-%S")
    folder_name = f"gold_{stamp}_{tz_suffix()}"
    folder = drive_create_subfolder(folder_name)
    fid = folder["id"]
    drive_upload_bytes("gold_analysis.csv", _build_gold_csv_bytes(result, stamp), "text/csv", fid)
    return {"folder_id": fid, "link": drive_folder_link(fid), "name": folder_name}
