"""Trade plans per horizon: entry, structural stop, targets, R:R, time stop."""

import math

from .config import as_float


def plan_s(v: dict, days: int) -> dict:
    """Spec (S): "Stop = max(1.0-1.5 x daily ATR14, below trigger-bar low or
    pivot shelf). Targets: T1 = 1.5-2 x ATR or nearest swing high, T2 = 2.5-3.5
    x ATR. TIME-STOP: ... within ceil(x/2) trading days"."""
    lv, coil = v.get("_levels") or {}, v.get("_coil") or {}
    px = as_float(v.get("px_now"))
    atr = as_float(lv.get("atr14d"))
    pivot = as_float(coil.get("pivot15d")) or as_float(lv.get("swing_hi15"))
    if not (px and atr and pivot):
        return {}
    entry = pivot  # entry only on the breakout
    # "Stop = max(1.0-1.5 x daily ATR14, below trigger-bar low or pivot shelf)"
    # max() in the spec means "pick the one tight enough", not reach for a swing low 6 ATR away:
    # a shelf counts only within 1.5 ATR; farther is not a short-trade shelf
    shelf = as_float(lv.get("swing_lo10"))
    stop = entry - 1.25 * atr  # middle of the 1.0–1.5 ATR range
    if shelf is not None and entry - 1.5 * atr <= shelf < entry:
        stop = min(stop, shelf)
    # T1 = "1.5-2 x ATR or nearest swing high" — a nearer swing high is the real resistance
    hi60 = as_float(lv.get("swing_hi60"))
    t1 = entry + 1.75 * atr
    if hi60 and entry + 0.5 * atr < hi60 < t1:
        t1 = hi60
    t2 = entry + 3.0 * atr
    risk = entry - stop
    return {
        "entry": round(entry, 2),
        "entry_rule": "ปิดยืนเหนือ (breakout เท่านั้น)",
        "stop": round(stop, 2),
        "tp1": round(t1, 2),
        "tp2": round(t2, 2),
        "rr1": round((t1 - entry) / risk, 2) if risk > 0 else None,
        "rr2": round((t2 - entry) / risk, 2) if risk > 0 else None,
        "atr": atr,
        "risk_per_share": round(risk, 2) if risk > 0 else None,
        "time_stop_days": math.ceil(days / 2),
        "time_stop_rule": f"ไม่ขยับ +0.5×ATR ({0.5 * atr:.2f}) ภายใน {math.ceil(days / 2)} "
        "วันทำการ = ออกที่ราคาตลาด",
    }


def plan_m(v: dict, weeks: int) -> dict:
    """Spec (M): "Stop = structural: below daily swing low / EMA50D / base low
    (typically 2-3 x ATR). Targets: T1 = prior high or measured move, T2 =
    weekly extension level. TIME-STOP: formal thesis reassessment at x/2"."""
    lv = v.get("_levels") or {}
    px = as_float(v.get("px_now"))
    atr = as_float(lv.get("atr14d"))
    if not (px and atr):
        return {}
    # "structural: below daily swing low / EMA50D / base low (typically 2-3 x ATR)"
    # take the nearest structure level still below price, then clamp it into 2–3 ATR
    lo10, e50d = as_float(lv.get("swing_lo10")), as_float(lv.get("e50d"))
    cands = [c for c in (lo10, e50d) if c is not None and c < px]
    stop = max(cands) if cands else px - 2.5 * atr  # max = the level closest to price
    if px - stop > 3.0 * atr:  # wider than the spec
        stop = px - 3.0 * atr
    elif px - stop < 2.0 * atr:  # too tight for a medium trade
        stop = px - 2.0 * atr
    hi15, hi60 = as_float(lv.get("swing_hi15")), as_float(lv.get("swing_hi60"))
    t1 = hi15 if (hi15 and hi15 > px) else px + 2.0 * atr
    t2 = hi60 if (hi60 and hi60 > t1) else t1 + 2.0 * atr
    risk = px - stop
    return {
        "entry": round(px, 2),
        "entry_rule": "ทยอยเข้าโซน EMA20–50 รายวัน (Phase-3 pullback)",
        "entry_pullback": as_float(lv.get("e20d")),
        "stop": round(stop, 2),
        "tp1": round(t1, 2),
        "tp2": round(t2, 2),
        "rr1": round((t1 - px) / risk, 2) if risk > 0 else None,
        "rr2": round((t2 - px) / risk, 2) if risk > 0 else None,
        "atr": atr,
        "risk_per_share": round(risk, 2) if risk > 0 else None,
        "time_stop_weeks": max(1, math.ceil(weeks / 2)),
        "time_stop_rule": f"ทบทวน thesis ที่ {max(1, math.ceil(weeks / 2))} สัปดาห์ · "
        f"1D CMF ลบ 3 วันติด = ออกทันทีไม่ว่าราคาเป็นยังไง · "
        f"รีวิวทุกวันงบ/CPI/FOMC ในหน้าต่างถือ",
    }
