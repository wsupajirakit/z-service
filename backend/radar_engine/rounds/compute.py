"""Compute one radar round and freeze it in Mongo.

fingerprint == the stock-radar fingerprint (content hash of the export CSVs), so re-running
on unchanged data reuses the existing round instead of writing a duplicate, exactly like
run.sh does on the stock-radar side.
"""

import os
import shutil
import tempfile

import pandas as pd
from pymongo.errors import DuplicateKeyError

from zservice.core.messages import coded

from .. import lib
from . import config as rounds_config
from . import deps
from .clock import et_iso, hours_between, now_iso
from .config import TIMEFRAMES
from .csv_set import build_csv_set, normalize_timeframes, report_progress
from .errors import RadarError
from .packs import build_packs
from .serialize import jsonable
from .warnings import age_warning, build_warnings


def run_round(
    timeframes=None, list_name: str | None = None, progress=None, new_record: bool = False
) -> dict:
    """Compute one radar round and freeze it in Mongo. Returns
    {stamp, reused, round} — `reused` means the identical CSV content had
    already been screened and the existing round was returned untouched. On the
    reused path `round` is the metadata-only document; fetch the payloads with
    deps.store().radar_round_get(stamp) when they are actually needed.

    new_record=True stores a new round even when the data did not change: the
    stamp would collide with the existing one, so it gets `_v2`, `_v3`, ... It is
    for "a new entry to look back on when I pressed it" while the market has no
    new data (every computed value is identical — same input, only the time differs).
    """
    tfs = normalize_timeframes(timeframes)
    screened = _screen(tfs, list_name, progress, new_record)
    if "reused" in screened:
        return screened
    state, present, tf_meta, skipped = screened["state"], *screened["csv_set"]

    report_progress(progress, "saving", coded("radar.saving", "บันทึกรอบลงฐานข้อมูล"))
    tfs_present = state.get("tfs_present") or present
    _finish_tf_meta(tf_meta, tfs_present, int(state.get("tz_shift_applied_h") or 0))
    warnings = build_warnings(tfs_present, skipped, tf_meta, state.get("screen_mode"))
    created_at = now_iso()
    asof_iso = et_iso(state["asof_et"])
    age_h = hours_between(asof_iso, created_at)
    stale = age_warning(age_h, state["asof_et"])
    if stale:
        warnings.insert(0, stale)

    stamp = os.path.basename(lib.history_dir("", state))
    if new_record:
        stamp = _free_stamp(stamp)
    doc = _round_doc(
        state,
        stamp=stamp,
        created_at=created_at,
        asof_iso=asof_iso,
        age_h=age_h,
        list_name=list_name,
        tfs=tfs,
        tfs_present=tfs_present,
        skipped=skipped,
        tf_meta=tf_meta,
        warnings=warnings,
    )
    return _save(doc)


def _save(doc: dict) -> dict:
    """Store the round; the same stamp already stored (identical content, concurrent run)
    is reused instead. Older rounds beyond RADAR_KEEP_ROUNDS are pruned."""
    try:
        deps.store().radar_round_add(doc)
    except DuplicateKeyError:
        existing = deps.store().radar_round_get(doc["stamp"])
        if existing:
            return {"stamp": doc["stamp"], "reused": True, "round": existing}
        raise
    pruned = deps.store().radar_round_prune(rounds_config.get_settings().keep_rounds)
    return {"stamp": doc["stamp"], "reused": False, "pruned": pruned, "round": doc}


def _screen(tfs: list[str], list_name: str | None, progress, new_record: bool) -> dict:
    """Write the CSV set to a temp dir and run the screen on it:
    {"state", "csv_set": (present, tf_meta, skipped)}, or the reuse answer when the
    same content was already screened (checked BEFORE the screen runs, so pressing
    the button on unchanged data costs one Mongo read, not a rescreen)."""
    csv_dir = tempfile.mkdtemp(prefix="radar_round_")
    try:
        present, tf_meta, skipped = build_csv_set(csv_dir, tfs, list_name, progress)
        if not present:
            raise RadarError(
                "ไม่มีข้อมูลใน DB สำหรับ timeframe ที่เลือก "
                f"({', '.join(t.upper() for t in tfs)}) — ต้อง fetch ก่อน"
            )
        export_paths = [p for tf in present for p in lib.newest_parts(csv_dir, tf)]
        # Same content hash stock-radar uses.
        existing = deps.store().radar_round_find_fingerprint(lib.fingerprint(export_paths))
        if existing and not new_record:
            return {"stamp": existing["stamp"], "reused": True, "round": existing}
        joined = "+".join(t.upper() for t in present)
        report_progress(
            progress, "screening", coded("radar.screening", f"รันสูตรเรดาร์ ({joined})", tfs=joined)
        )
        # port_path=None: portfolio positions never leave the local machine.
        state = lib.run_screen(csv_dir, port_path=None)
    finally:
        shutil.rmtree(csv_dir, ignore_errors=True)
    return {"state": state, "csv_set": (present, tf_meta, skipped)}


def _finish_tf_meta(tf_meta: dict, tfs_present: list[str], shift_h: int) -> None:
    """Per-TF metadata after the screen: in_screen, bar as-of with the same ET
    correction the screen applied, and its ISO form."""
    for tf, meta in tf_meta.items():
        meta["in_screen"] = tf in tfs_present
        bar = meta.get("bar_asof")
        if bar and shift_h:
            try:
                bar = str(pd.Timestamp(bar) + pd.Timedelta(hours=shift_h))
                meta["bar_asof"] = bar
            except ValueError:
                pass
        meta["bar_asof_iso"] = et_iso(bar)
        meta["fetched_at_label"] = "เวลาที่ z-service บันทึกชุดข้อมูล TF นี้ลง DB (จบรอบ fetch)"


def _free_stamp(stamp: str) -> str:
    """Same data = same stamp, so a forced new record takes the next free `_vN`."""
    base, ver = stamp, 1
    while deps.store().radar_round_get(stamp):
        ver += 1
        stamp = f"{base}_v{ver}"
    return stamp


def _round_doc(
    state: dict,
    *,
    stamp,
    created_at,
    asof_iso,
    age_h,
    list_name,
    tfs,
    tfs_present,
    skipped,
    tf_meta,
    warnings,
) -> dict:
    breadth = (state.get("regime") or {}).get("breadth") or {}
    # Universe size the kill% is divided by. (A loop counter once reused this name and
    # the page showed kill% 14600% — keep it distinct from anything else.)
    breadth_n = breadth.get("n") or 0
    uni = state.get("universe") or {}
    return {
        "stamp": stamp,
        "fingerprint": state["fingerprint"],
        "created_at": created_at,
        "asof_et": state["asof_et"],
        "asof_et_iso": asof_iso,
        "data_age_hours": round(age_h, 1) if age_h is not None else None,
        "list_name": list_name or None,
        "timeframes": tfs_present,
        "timeframes_requested": tfs,
        "timeframes_skipped": skipped,
        "tf_meta": tf_meta,
        "screen_mode": state.get("screen_mode"),
        "partial": len(tfs_present) < len(TIMEFRAMES),
        "universe": {
            "all": len(uni.get("all") or []),
            "stocks": len(uni.get("stocks") or []),
            "etfs": len(uni.get("etfs") or []),
            "noneq": len(uni.get("noneq") or []),
        },
        "kill_count": breadth.get("kill_count"),
        "kill_label": breadth.get("kill_label"),
        "kill_pct": (
            round(breadth.get("kill_count", 0) / breadth_n * 100, 1) if breadth_n else None
        ),
        "breadth_n": breadth_n,
        "regime_hint": (state.get("regime") or {}).get("permission_hint"),
        # Texts for the legacy UI; the coded list lets the web UI translate them.
        "warnings": [w["text"] for w in warnings],
        "warnings_coded": warnings,
        "digest_md": state["digest"],
        # Stored as JSON STRINGS (same pattern as history.result_json): ticker keys
        # like 'BRK.B' can never collide with BSON field-name rules, and the round
        # payload stays exactly what stock-radar writes to full.json.
        "full_json": jsonable({k: v for k, v in state.items() if k != "digest"}),
        "packs_json": jsonable(build_packs(state)),
    }
