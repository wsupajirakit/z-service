"""Per-symbol state tags (COILED / TRIGGERING / EXTENDED ...) and the Phase-4 check."""

from .config import as_float


def state_tag(v: dict, tf: str = "1d") -> str:
    """COILED / TRIGGERING / IN-TREND / EXTENDED.

    Spec ("About-To-Pop Coil Detector"): "Tag every candidate: COILED (waiting
    for trigger) / TRIGGERING (Phase-4 firing now) / EXTENDED (> 1.5 x ATR past
    pivot = do not chase)."
    """
    coil = v.get("_coil") or {}
    lv = v.get("_levels") or {}
    px = as_float(v.get("px_now"))
    pivot = as_float(coil.get("pivot15d")) or as_float(lv.get("swing_hi15"))
    atr = as_float(lv.get("atr14d"))
    stage = (v.get("_stage") or {}).get("stage") or ""

    if px and pivot and atr and px > pivot + 1.5 * atr:
        return "EXTENDED"
    if stage.startswith("TRIGGER"):
        return "TRIGGERING"
    if px and pivot and px > pivot:
        return "IN-TREND"
    return "COILED"


def phase4_live(v: dict) -> bool:
    """Spec (S): "Entry ONLY via live Phase-4 trigger (1H RTH close above VWAP +
    RVOL_Dev > 50% + OBV rising + IPI Accumulation)". lib.py already evaluates
    exactly this and stores it as `_stage.p4` (its p4 uses rvol > 1.5, i.e.
    RVOL_Dev > 50%, plus OBV slope > 0 and IPI Accum), so we reuse that verdict
    instead of recomputing it differently."""
    return bool((v.get("_stage") or {}).get("p4"))
