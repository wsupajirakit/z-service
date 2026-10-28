"""The UIPT-S / UIPT-M ranking of a round, with the near-misses and their failed gates."""

import json
from pathlib import Path

from .. import timing
from .config import (
    M_MAX_CONCURRENT,
    M_RISK_PCT,
    M_WEEKS_DEFAULT,
    S_DAYS_DEFAULT,
    S_MAX_CONCURRENT,
    S_RISK_PCT,
    as_float,
)
from .gates import gates_m, gates_s
from .plans import plan_m, plan_s
from .scores import score_m, score_s
from .state import phase4_live, state_tag
from .verdicts import entry_verdict

# What each ranking cannot check from CSV snapshots (data file, shown with every ranking).
_CAVEATS = json.loads(Path(__file__).with_name("caveats.json").read_text(encoding="utf-8"))
_CAVEATS_S = _CAVEATS["short"]
_CAVEATS_M = _CAVEATS["medium"]


def wait_text(mode: str, state_tag: str, asof_iso: str | None) -> dict:
    """ "What to wait for, when it closes, which day to place the order" — real times in ET
    and Thai time.

    Short trades confirm on the 1h/4h bar · medium trades on the daily bar (the spec
    says M must not exit on 1h noise, so its confirmation is a daily bar).
    """
    tf = "4h" if mode == "s" else "1d"
    ow = timing.order_window(asof_iso, tf) if asof_iso else None
    if not ow:
        return {}
    close, opn = ow["bar_close"], ow["order_open"]
    if state_tag == "TRIGGERING":
        what = (
            f"ยิงแล้ว — เข้าได้เลยระหว่างเวลาทำการ · ถ้าพลาดไม้นี้ "
            f"รอ{close['label']} {close['both']} แล้วค่อยตั้ง order รอบเปิด {opn['both']}"
        )
    elif state_tag == "EXTENDED":
        what = (
            f"ห้ามไล่ — วิ่งเกิน 1.5 ATR จาก pivot แล้ว · รอย่อกลับมาก่อน "
            f"แล้วประเมินใหม่ที่{close['label']} {close['both']}"
        )
    else:
        what = (
            f"รอ{close['label']} {close['both']} ให้ปิดยืนเหนือจุดเข้าก่อน → "
            f"ถ้าปิดผ่านจริง ตั้ง order ตอนเปิดตลาด {opn['both']}"
        )
    return {
        "wait_for": what,
        "confirm_bar_tf": tf,
        "confirm_close_et": close["et"],
        "confirm_close_th": close["th"],
        "confirm_close_both": close["both"],
        "confirm_label": close["label"],
        "order_open_et": opn["et"],
        "order_open_th": opn["th"],
        "order_open_both": opn["both"],
        "order_date_et": opn["date_et"],
    }


def rank(state: dict, mode: str, x: int | None = None, limit: int = 25) -> dict:
    """Build the UIPT-S or UIPT-M ranking for one round.

    mode: 's' (x = trading days 1–5) or 'm' (x = weeks 1–8).
    Returns {mode, x, label, picks[], rejected[], caveats[]} — `rejected` keeps
    the near-misses WITH the gate they failed, because "why is my name not in
    the list" is the question this table gets asked most.
    """
    mode, x, label = _horizon(mode, x)
    views = state.get("views") or {}
    uni = state.get("universe") or {}
    asof_iso = state.get("asof_et")
    names = list(uni.get("stocks") or []) + list(uni.get("etfs") or [])
    sector_flow = _sector_flow_map(state)

    picks, rejected = [], []
    for sym in names:
        v = views.get(sym) or {}
        # A missing main TF fails a gate with its reason instead of being skipped
        # silently, so "nothing passed" reads as incomplete data, not an empty market.
        if not v.get("1d"):
            continue  # no 1D at all = not in this round's universe
        row = _rank_row(sym, v, mode, x, label, asof_iso, sector_flow)
        (rejected if row["gates_failed"] else picks).append(row)

    # Live triggers (Phase-4 in) first, then by score · EXTENDED always last.
    picks.sort(key=lambda r: (r["state"] == "EXTENDED", not r["phase4_live"], -r["score"]))
    rejected.sort(key=lambda r: (len(r["gates_failed"]), -r["score"]))
    return {
        "mode": mode,
        "x": x,
        "label": label,
        "max_concurrent": S_MAX_CONCURRENT if mode == "s" else M_MAX_CONCURRENT,
        "risk_pct": S_RISK_PCT if mode == "s" else M_RISK_PCT,
        "picks": picks[:limit],
        "rejected": rejected[:limit],
        "caveats": _CAVEATS_S if mode == "s" else _CAVEATS_M,
    }


def _horizon(mode: str, x: int | None) -> tuple[str, int, str]:
    """(mode, clamped x, label): S = 1–5 trading days, M = 1–8 weeks."""
    mode = mode.lower()
    if mode not in ("s", "m"):
        raise ValueError("mode must be 's' or 'm'")
    if mode == "s":
        x = max(1, min(5, int(x or S_DAYS_DEFAULT)))
        return mode, x, f"S-{x}D"
    x = max(1, min(8, int(x or M_WEEKS_DEFAULT)))
    return mode, x, f"M-{x}W"


def _rank_row(sym, v, mode, x, label, asof_iso, sector_flow) -> dict:
    short = mode == "s"
    ok, bad = gates_s(v) if short else gates_m(v)
    plan = plan_s(v, x) if short else plan_m(v, x)
    tag = state_tag(v)
    row = {
        "sym": sym,
        "horizon": label,
        "score": score_s(v) if short else score_m(v),
        # Every row says in plain words how long to hold, not just the S-3D label.
        "hold_text": (
            f"เล่นสั้น ถือ {x} วันทำการ (ประมาณ {x * 7 // 5 or 1} วันปฏิทิน)"
            if short
            else f"เล่นกลาง ถือ {x} สัปดาห์ (~{max(1, round(x / 4.3))} เดือน)"
        ),
        "hold_unit": "วัน" if short else "สัปดาห์",
        "hold_n": x,
        "state": tag,
        "sector_flow": sector_flow.get(sym, "NEUTRAL"),
        "stage": (v.get("_stage") or {}).get("stage"),
        "px": as_float(v.get("px_now")),
        "ext200_pct": (v.get("_stage") or {}).get("ext200_pct"),
        "gates_ok": ok,
        "gates_failed": bad,
        "phase4_live": phase4_live(v),
        "risk_pct": S_RISK_PCT if short else M_RISK_PCT,
        **plan,
        **wait_text(mode, tag, asof_iso),
        **entry_verdict(
            asof_iso=asof_iso,
            confirm_tf="4h" if short else "1d",
            entry=plan.get("entry"),
            state_tag=tag,
            phase4=phase4_live(v),
        ),
    }
    # R:R is an outcome of the plan, not a spec gate — but a trade that does not pay
    # for its risk must say so plainly instead of just sitting in the table.
    rr1 = row.get("rr1")
    if rr1 is not None and rr1 < 1.0:
        row["rr_warning"] = (
            f"R:R ถึง T1 แค่ {rr1} — เสี่ยงมากกว่าที่หวังได้ (stop กว้างตามโครงสร้าง แต่แนวต้านแรกอยู่ใกล้) ไม่คุ้มเข้า"
        )
    return row


def _sector_flow_map(state: dict) -> dict:
    """Spec (Labeling): every pick needs a sector-flow tag from the Layer-0 map.
    The round's sector table ranks ETFs by RS20; we tag a symbol IN/OUT only when
    it IS one of those ETFs — mapping arbitrary stocks to a sector needs data the
    CSV set does not carry, and guessing would be worse than NEUTRAL."""
    rows = state.get("sectors") or []
    ranked = [r for r in rows if r.get("rs20") is not None]
    ranked.sort(key=lambda r: -r["rs20"])
    out = {}
    for i, r in enumerate(ranked):
        if i < 3:
            out[r["sym"]] = "IN"
        elif i >= len(ranked) - 3:
            out[r["sym"]] = "OUT"
        else:
            out[r["sym"]] = "NEUTRAL"
    return out


def packs(state: dict, s_days: int | None = None, m_weeks: int | None = None) -> dict:
    """Both rankings, ready to store in a round document."""
    return {"uipt_s": rank(state, "s", s_days), "uipt_m": rank(state, "m", m_weeks)}
