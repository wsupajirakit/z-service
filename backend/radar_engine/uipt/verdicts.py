"""The 3 answers every table gives per name: enter now? / from when? / latest when?"""

from .. import timing


def entry_verdict(
    *,
    asof_iso: str | None,
    confirm_tf: str,
    entry=None,
    state_tag: str = "COILED",
    phase4: bool = False,
    dead: bool = False,
    dead_reason: str = "",
    accumulate: bool = False,
) -> dict:
    """The 3 answers every table on the page must give per name (user rule, 13 Aug):

        1. can I enter now
        2. from when can I enter   (ET + Thai time)
        3. the latest time / the condition after which the move is missed

    Shared by every section — UIPT-S/M, the near-pivot queue, conviction, -ez,
    SPRING — so the whole page answers the same way.

    confirm_tf : the confirming bar ('4h' short trades · '1d' medium/long)
    dead       : names not to touch (KILL/FAIL/1W Dist) — answers "no" with the reason
    accumulate : long-term accumulation (SPRING) is scaled into, no breakout wait
    """
    ow = timing.order_window(asof_iso, confirm_tf) if asof_iso else None
    close = ow["bar_close"] if ow else None
    opn = ow["order_open"] if ow else None
    e = f"{entry:g}" if isinstance(entry, (int, float)) else None
    if dead:
        return _verdict_dead(dead_reason)
    if accumulate:
        return _verdict_accumulate(e, close, opn)
    if state_tag == "TRIGGERING" and phase4:
        return _verdict_triggering(e, close, opn)
    if state_tag == "EXTENDED":
        return _verdict_extended(e, close)
    return _verdict_waiting(e, close, opn)


def _both(slot):
    return slot["both"] if slot else None


def _verdict_dead(reason: str) -> dict:
    return {
        "can_enter_now": False,
        "verdict_head": "ห้ามเข้า",
        "verdict_why": reason or "โดนตัดตามกติกา Kill-Switch",
        "enter_from": "ยังไม่ได้ — ต้องรอเงื่อนไขที่ทำให้โดนตัดหายไปก่อน",
        "enter_from_both": None,
        "deadline": "ไม่ต้องรอ — ตัวนี้ออกจากสนามรอบนี้แล้ว",
        "confirm_at_both": None,
    }


def _verdict_accumulate(e, close, opn) -> dict:
    deadline = "ไม่มีเส้นตาย — ห้ามซื้อไล่ รอย่อรอบใหม่"
    if close:
        deadline = (
            f"ไม่มีเส้นตายตายตัว — ทบทวนอีกทีที่ {close['both']} "
            f"(แท่งรายวันปิด) · ห้ามซื้อไล่ ถ้าขึ้นไปไกลให้รอย่อรอบใหม่"
        )
    return {
        "can_enter_now": True,
        "verdict_head": "เข้าได้เลย (ทยอยสะสม)",
        "verdict_why": (
            f"ไม้ยาวเข้าแบบทยอยที่โซนย่อ {e} ไม่ต้องรอ breakout"
            if e
            else "ไม้ยาวเข้าแบบทยอยที่โซนย่อ ไม่ต้องรอ breakout"
        ),
        "enter_from": "ตอนนี้ — ทยอยไม้แรกได้ระหว่างเวลาทำการ",
        "enter_from_both": _both(opn),
        "deadline": deadline,
        "confirm_at_both": _both(close),
    }


def _verdict_triggering(e, close, opn) -> dict:
    if close and e:
        deadline = (
            f"ช้าสุด {close['both']} (แท่งยืนยันถัดไปปิด) หรือก่อนราคาวิ่งพ้น {e} เกิน 1.5 ATR — อย่างใดถึงก่อน"
        )
    elif close:
        deadline = f"ช้าสุด {close['both']}"
    else:
        deadline = f"ช้าสุดก่อนราคาวิ่งพ้น {e} เกิน 1.5 ATR" if e else "—"
    return {
        "can_enter_now": True,
        "verdict_head": "เข้าได้เลย",
        "verdict_why": (
            f"ยิงครบเงื่อนไขแล้ว — ปิดเหนือ {e} + วอลุ่มหนุน + เงินเข้า" if e else "ยิงครบเงื่อนไขแล้ว"
        ),
        "enter_from": "ตอนนี้ — ระหว่างเวลาทำการ",
        "enter_from_both": _both(opn),
        "deadline": deadline,
        "confirm_at_both": _both(close),
    }


def _verdict_extended(e, close) -> dict:
    return {
        "can_enter_now": False,
        "verdict_head": "เข้าไม่ได้ — ตกรถแล้ว",
        "verdict_why": (
            f"ราคาวิ่งพ้น {e} เกิน 1.5 ATR ไปแล้ว ไล่ตอนนี้เสี่ยงโดนย่อสวน" if e else "ราคาวิ่งไปไกลจากจุดเข้าแล้ว"
        ),
        "enter_from": "รอย่อกลับมาที่โซนเข้าก่อน แล้วประเมินใหม่",
        "enter_from_both": _both(close),
        "deadline": (
            f"ประเมินใหม่ที่ {close['both']} (แท่งยืนยันถัดไปปิด)" if close else "ไม่มีกำหนด — ตัวนี้ต้องรอรอบใหม่"
        ),
        "confirm_at_both": _both(close),
    }


def _verdict_waiting(e, close, opn) -> dict:
    if e and close:
        why = f"ราคาต้องปิดเหนือ {e} ให้ได้ก่อน ({close['label']})"
    else:
        why = f"ราคาต้องปิดเหนือ {e} ให้ได้ก่อน" if e else "ต้องรอแท่งยืนยันปิดก่อน"
    if opn and e:
        deadline = f"ช้าสุด {opn['both']} + ยังไม่พุ่งพ้น {e} เกิน 1.5 ATR — เลยจากนั้นถือว่าตกรถ"
    elif opn:
        deadline = f"ช้าสุด {opn['both']}"
    else:
        deadline = f"ช้าสุดก่อนราคาพุ่งพ้น {e} เกิน 1.5 ATR" if e else "—"
    return {
        "can_enter_now": False,
        "verdict_head": "ยังเข้าไม่ได้ — ต้องรอปิดยืนยันก่อน",
        "verdict_why": why,
        "enter_from": (f"เข้าได้ตั้งแต่เปิดตลาด {opn['both']}" if opn else "เข้าได้หลังแท่งยืนยันปิดผ่าน"),
        "enter_from_both": _both(opn),
        "confirm_at_both": _both(close),
        "deadline": deadline,
    }
