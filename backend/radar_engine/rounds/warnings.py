"""Truthful warnings about what a round can and cannot answer (a partial or stale round
must never read like a complete, current one).

Each warning is a coded(...) message: `text` is the legacy UI's Thai sentence, `code` +
`params` let the web UI show it in the selected language.
"""

from zservice.core.messages import coded

from .clock import spread_hours, ts_key
from .config import STALE_DATA_HOURS, STALE_SPREAD_HOURS, TIMEFRAMES

_MISSING_TF_IMPACT = {
    "1w": "ไม่มี 1W → Kill-Switch ชั้นสัปดาห์ตรวจไม่ได้ · stage ทั้งหมดเชื่อถือได้ต่ำลง (UIPT เต็มรูปต้องมี 1W)",
    "1d": "ไม่มี 1D → ไม่มี stage UIPT เต็มรูป (จะตกไปโหมดสั้น UIPT-S) · breadth/RS คิดจาก 4H แทน",
    "4h": "ไม่มี 4H → ขาดชั้นยืนยันกลางทาง (โครงสร้างระหว่าง 1D กับ 1H)",
    "1h": "ไม่มี 1H → ไม่มี trigger ชั้นเข้าไม้ (VWAP/RVOL/OBV รายชั่วโมง) · stage จะไม่มีทางขึ้นเป็น TRIGGER",
}
_WHY = {"unselected": " (ไม่ได้เลือก)", "nodata": " (ไม่มีข้อมูลใน DB)"}
_SHORT_WITHOUT_4H = (
    "รอบนี้ตกไปโหมดสั้น (UIPT-S) ซึ่งใช้ 4H เป็นเกตโครงสร้าง แต่ไม่มี 4H "
    "→ ทุก symbol จะออกมาเป็น NO-DATA และ kill% = 0 ตามกลไก "
    "ไม่ใช่เพราะตลาดดี — รอบนี้ใช้ตัดสินใจไม่ได้ ต้องเลือก 4H หรือ 1W+1D ด้วย"
)
_DAYS_FROM_HOURS = 48  # an age this old is said in days
# _missing() picks one of these at run time (radar.missing_<tf>_<why>).
MESSAGE_CODES = {
    "radar.missing_1w_unselected": (), "radar.missing_1w_nodata": (),
    "radar.missing_1d_unselected": (), "radar.missing_1d_nodata": (),
    "radar.missing_4h_unselected": (), "radar.missing_4h_nodata": (),
    "radar.missing_1h_unselected": (), "radar.missing_1h_nodata": (),
}  # fmt: skip


def build_warnings(
    present: list[str], skipped: list[str], tf_meta: dict, screen_mode: str | None = None
) -> list[dict]:
    """A PARTIAL round must never read like a complete one."""
    out = [_missing(tf, tf in skipped) for tf in TIMEFRAMES if tf not in present]
    # Missing 4H means different things in the two modes: a lost confirmation layer in
    # FULL, but a dead screen in SHORT, where 4H IS the structure gate (UIPT-S) and every
    # symbol comes back NO-DATA without it.
    if screen_mode == "short" and "4h" not in present:
        out.insert(0, coded("radar.short_without_4h", _SHORT_WITHOUT_4H))
    out.extend(_clock_warnings(present, tf_meta))
    return out


def _missing(tf: str, had_no_data: bool) -> dict:
    why = "nodata" if had_no_data else "unselected"
    return coded(f"radar.missing_{tf}_{why}", _MISSING_TF_IMPACT[tf] + _WHY[why])


def _clock_warnings(present: list[str], tf_meta: dict) -> list[dict]:
    out = []
    fresh = {tf: tf_meta.get(tf, {}).get("fetched_at_max") for tf in present}
    newest = max((v for v in fresh.values() if v), key=ts_key, default=None)
    for tf, ts in fresh.items():
        gap = spread_hours(ts, newest)
        if gap is not None and gap >= STALE_SPREAD_HOURS:
            hours = f"{gap:.1f}"
            text = (
                f"{tf.upper()} เก่ากว่า TF ที่ใหม่สุดในรอบนี้ {hours} ชม. "
                "— ข้อมูลคนละนาฬิกา ระวังอ่าน confluence ข้าม TF"
            )
            out.append(coded("radar.tf_older", text, tf=tf.upper(), hours=hours))
        distinct = tf_meta.get(tf, {}).get("fetched_at_distinct", 1)
        if distinct > 1:
            text = f"{tf.upper()} มีเวลาบันทึกหลายค่า ({distinct} ค่า) — บาง symbol ค้างจากรอบเก่า"
            out.append(coded("radar.tf_mixed", text, tf=tf.upper(), count=distinct))
    return out


def age_warning(age_h: float | None, asof_et) -> dict | None:
    """Warn when the data is much older than now, or claims to be ahead of now."""
    if age_h is None:
        return None
    asof = str(asof_et)[:16]
    if age_h >= STALE_DATA_HOURS:
        days = age_h >= _DAYS_FROM_HOURS
        value = f"{age_h / 24:.1f}" if days else f"{age_h:.1f}"
        age = f"{value} วัน" if days else f"{value} ชม."
        text = (
            f"ข้อมูลในรอบนี้เก่ากว่าเวลาที่ประมวล {age} — เป็นภาพตลาด ณ {asof} ET ไม่ใช่ตอนนี้ "
            "(ต้อง fetch ข้อมูลใหม่ก่อนถ้าจะใช้ตัดสินใจวันนี้)"
        )
        if days:
            return coded("radar.data_old_days", text, age=value, asof=asof)
        return coded("radar.data_old_hours", text, age=value, asof=asof)
    if age_h <= -2:
        ahead = f"{-age_h:.1f}"
        text = (
            f"as-of ของรอบนี้ ({asof} ET) ล้ำเวลาปัจจุบัน {ahead} ชม. — ไฟล์ CSV ไม่มี header "
            "เวลา สูตรจึงประมาณจาก ปลายแท่งใหม่สุด (แท่ง 1W ปลายแท่งล้ำได้ถึง 7 วัน) "
            "อย่าอ่านเป็นเวลาจริง"
        )
        return coded("radar.asof_ahead", text, hours=ahead, asof=asof)
    return None
