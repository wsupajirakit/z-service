"""Self-healing reads of stored rounds: impossible kill%/breadth and packs from an older
PACKS_VERSION are recomputed from the frozen full_json and written back once."""

import contextlib
import json

from . import deps
from .packs import PACKS_VERSION, build_packs
from .serialize import jsonable


def repair_round_meta(meta: dict) -> dict:
    """Repair a listed round's kill%/breadth when the value is impossible.

    The round list does not load full_json (too large), so it first checks for an
    impossible value — kill% is always 0–100; above that the divisor was broken (bug of
    14 Aug: the `_v2` counter overwrote the universe size -> kill% in the tens of
    thousands). Only broken rounds load full_json to recompute, and the repair is
    written back to the DB so it happens once.
    """
    pct = meta.get("kill_pct")
    if pct is None or (0 <= pct <= 100 and (meta.get("breadth_n") or 0) > 2):
        return meta
    full = deps.store().radar_round_get(meta.get("stamp"))
    if not full or not full.get("full_json"):
        return meta
    fixed = ensure_packs_current(full)
    for k in ("kill_pct", "breadth_n", "kill_count"):
        if k in fixed:
            meta[k] = fixed[k]
    return meta


def ensure_packs_current(doc: dict) -> dict:
    """Bring an old round's packs to the current version when it is read (self-healing).

    Rounds stored by older code lack fields added later (e.g. the 3 answers, bar wait
    times), and fingerprint reuse keeps bringing old rounds back, so the repair happens
    at read time: when _v differs, recompute packs from full_json (a pure function of
    the frozen state — digest/fingerprint/stamp are untouched) and write them back."""
    try:
        packs = json.loads(doc.get("packs_json") or "{}")
    except ValueError:
        packs = {}
    if not doc.get("full_json"):
        return doc
    state = json.loads(doc["full_json"])

    # Repair a broken kill%/breadth: bug of 14 Aug, the `_v2` version counter overwrote the
    # universe-size variable, so kill_pct = kill_count/1*100 (e.g. 14600%) whenever
    # "save as a new record" was ticked · the right value can always be recomputed from full_json
    breadth = (state.get("regime") or {}).get("breadth") or {}
    n = breadth.get("n") or 0
    kill_pct = round(breadth.get("kill_count", 0) / n * 100, 1) if n else None
    fixed_meta = doc.get("breadth_n") != n or doc.get("kill_pct") != kill_pct
    if fixed_meta:
        doc["breadth_n"] = n
        doc["kill_pct"] = kill_pct
        doc["kill_count"] = breadth.get("kill_count")
        with contextlib.suppress(Exception):  # a read must not fail on a write-back
            deps.store().radar_round_update_meta(
                doc["stamp"],
                {"breadth_n": n, "kill_pct": kill_pct, "kill_count": breadth.get("kill_count")},
            )

    if packs.get("_v") == PACKS_VERSION:
        return doc
    doc["packs_json"] = jsonable(build_packs(state))
    # If the repair cannot be written (e.g. read-only DB) the reader still gets live values.
    with contextlib.suppress(Exception):
        deps.store().radar_round_update_packs(doc["stamp"], doc["packs_json"])
    return doc


def backfill_packs(stamp: str | None = None) -> list[str]:
    """Recompute `packs_json` for rounds stored before a pack was added.

    Safe to re-run: the packs are pure functions of `full_json`, which is the
    frozen screen state — no CSV rebuild, no refetch, and the digest and
    fingerprint are never touched. Without this, an old round would render
    empty UIPT-S/UIPT-M tables that look like "no candidates" instead of
    "this round predates the ranking".
    """
    stamps = [stamp] if stamp else [r["stamp"] for r in deps.store().radar_round_list(500)]
    done = []
    for st in stamps:
        doc = deps.store().radar_round_get(st)
        if not doc or not doc.get("full_json"):
            continue
        state = json.loads(doc["full_json"])
        deps.store().radar_round_update_packs(st, jsonable(build_packs(state)))
        done.append(st)
    return done
