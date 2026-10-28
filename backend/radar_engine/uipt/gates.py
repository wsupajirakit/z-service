"""UIPT-S / UIPT-M gates: which spec conditions a symbol passes or fails (with reasons)."""

from .config import DVOL_MIN_M, as_float


def gates_s(v: dict) -> tuple[list[str], list[str]]:
    """Mandatory gates for UIPT-S. Returns (passed, failed-with-reason).

    Spec: "price >= 1H EMA20, 1D CMF > 0 or rising 3 bars, no 1D Kill, median
    dollar-volume > $30M/day, RSI-1D between 45-70" and "1W used only as veto
    (1W Distribution proxy = exclude)".
    """
    ok, bad = [], []
    d1, w1, h1 = v.get("1d") or {}, v.get("1w") or {}, v.get("1h") or {}
    px = as_float(v.get("px_now"))
    e20h = as_float((v.get("_levels") or {}).get("e20_1h")) or as_float(h1.get("e20"))

    # 4H is 30% of the S score and 1W is a veto — when that TF is absent from the round
    # the gate fails, it does not "pass" for lack of contrary data (silent and plausible is
    # the danger)
    if not h1:
        bad.append("ไม่มีข้อมูล 1H ในรอบนี้ — 1H คือชั้นทริกเกอร์ของไม้สั้น ประเมินไม่ได้")
        return ok, bad
    if not v.get("4h"):
        bad.append("ไม่มีข้อมูล 4H ในรอบนี้ (สเปกให้น้ำหนัก 4H 30%) — ประเมินไม่ได้")
    if not w1:
        bad.append("ไม่มีข้อมูล 1W ในรอบนี้ — ตรวจ veto (1W Dist) ไม่ได้")

    if px and e20h:
        (ok if px >= e20h else bad).append(f"ราคา {'≥' if px >= e20h else '<'} 1H EMA20 ({e20h:g})")
    else:
        bad.append("ไม่มีราคา/1H EMA20")

    cmf_d = as_float(d1.get("cmf"))
    if cmf_d is None:
        bad.append("ไม่มี 1D CMF")
    elif cmf_d > 0:
        ok.append(f"1D CMF {cmf_d:+.3f} > 0")
    else:
        bad.append(f"1D CMF {cmf_d:+.3f} ≤ 0 (เช็ค 'ขึ้น 3 แท่ง' ไม่ได้ ข้อมูลมีแท่งเดียว)")

    if d1.get("status") == "Dist":
        bad.append("1D Kill (IPI Dist)")
    else:
        ok.append("ไม่มี 1D Kill")

    if w1.get("status") == "Dist":
        bad.append("1W Dist = veto")
    else:
        ok.append("1W ไม่ Dist")

    _liquidity_and_rsi_s(d1, ok, bad)
    return ok, bad


def _liquidity_and_rsi_s(d1: dict, ok: list, bad: list) -> None:
    """UIPT-S: median dollar-volume above the floor, RSI-1D within 45–70."""
    dv = as_float(d1.get("dvol_m"))
    if dv is None:
        bad.append("ไม่มี dollar-volume")
    elif dv > DVOL_MIN_M:
        ok.append(f"dollar-volume ${dv:,.0f}M > ${DVOL_MIN_M:g}M")
    else:
        bad.append(f"dollar-volume ${dv:,.0f}M ≤ ${DVOL_MIN_M:g}M (บางเกิน)")

    rsi = as_float(d1.get("rsi"))
    if rsi is None:
        bad.append("ไม่มี RSI-1D")
    elif 45 <= rsi <= 70:
        ok.append(f"RSI-1D {rsi:g} อยู่ 45–70")
    else:
        bad.append(f"RSI-1D {rsi:g} นอกช่วง 45–70")


def gates_m(v: dict) -> tuple[list[str], list[str]]:
    """Mandatory gates for UIPT-M.

    Spec: "full Phase-2 (1W Golden Cross + 1D Golden Cross + 1W CMF > 0),
    Phase-3 pullback context preferred (price inside daily EMA20-EMA50 zone or
    first touch after breakout), no Kill on 1D or 1W, RSI-W < 72."
    """
    ok, bad = [], []
    d1, w1 = v.get("1d") or {}, v.get("1w") or {}

    if not w1:
        bad.append("ไม่มีข้อมูล 1W ในรอบนี้ — UIPT-M ต้องใช้ 1W เป็นเกตบังคับ ประเมินไม่ได้")
        return ok, bad
    if not v.get("4h"):
        bad.append("ไม่มีข้อมูล 4H ในรอบนี้ (สเปกให้น้ำหนัก 4H 20% สำหรับจับจังหวะ)")

    (ok if w1.get("gc") else bad).append(f"1W Golden Cross {'ผ่าน' if w1.get('gc') else 'ไม่ผ่าน'}")
    (ok if d1.get("gc") else bad).append(f"1D Golden Cross {'ผ่าน' if d1.get('gc') else 'ไม่ผ่าน'}")

    cmf_w = as_float(w1.get("cmf"))
    if cmf_w is None:
        bad.append("ไม่มี 1W CMF")
    elif cmf_w > 0:
        ok.append(f"1W CMF {cmf_w:+.3f} > 0")
    else:
        bad.append(f"1W CMF {cmf_w:+.3f} ≤ 0")

    if d1.get("status") == "Dist" or w1.get("status") == "Dist":
        bad.append(f"Kill: 1D={d1.get('status')} / 1W={w1.get('status')}")
    else:
        ok.append("ไม่มี Kill ทั้ง 1D และ 1W")

    rsi_w = as_float(w1.get("rsi"))
    if rsi_w is None:
        bad.append("ไม่มี RSI-W")
    elif rsi_w < 72:
        ok.append(f"RSI-W {rsi_w:g} < 72")
    else:
        bad.append(f"RSI-W {rsi_w:g} ≥ 72 (ร้อนเกิน)")
    return ok, bad


def _pullback_ctx(v: dict) -> bool:
    """Spec (M, 'preferred' not mandatory): "price inside daily EMA20-EMA50 zone
    or first touch after breakout" — scored as a bonus, never a hard gate."""
    lv, px = v.get("_levels") or {}, as_float(v.get("px_now"))
    e20, e50 = as_float(lv.get("e20d")), as_float(lv.get("e50d"))
    if not (px and e20 and e50):
        return False
    lo, hi = min(e20, e50), max(e20, e50)
    return lo * 0.99 <= px <= hi * 1.01
