"""The deterministic action tables the page renders, all produced by lib (never re-derived
here), each row answering: enter now? / from when? / latest when?"""

from .. import lib, timing, uipt


def _entry_answers(
    state: dict,
    rows: list,
    *,
    confirm_tf: str,
    entry_key: str,
    accumulate: bool = False,
    respect_stage: bool = True,
) -> list:
    """Fill the 3 answers (enter now? / from when? / latest when?) into every row
    of every table — user rule: every section that lists stocks answers per name."""
    asof = state.get("asof_et")
    views = state.get("views") or {}
    for r in rows:
        v = views.get(r.get("sym")) or {}
        stage = (v.get("_stage") or {}).get("stage") or ""
        w1 = v.get("1w") or {}
        # respect_stage=False for screens that already carry their own gates (SPRING passed 7
        # gates incl. "1W not Dist") — judging them by the UIPT stage, a different screen,
        # would answer "do not enter" for the whole list the formula picked for accumulation.
        stage_dead = stage.startswith("KILL") or stage.startswith("FAIL")
        dead = w1.get("status") == "Dist" or (respect_stage and stage_dead)
        # The conflict must still be visible (report frame: "nice spring but stage KILL")
        # — still scale in per the formula, knowing the strict screen disagrees: size down.
        if not respect_stage and stage_dead and not dead:
            d1 = v.get("1d") or {}
            why = (
                "1D เงินกำลังออก (IPI Dist)"
                if d1.get("status") == "Dist"
                else f"ตะแกรงเข้ม UIPT ให้ stage {stage}"
            )
            caution = (
                f"⚠ ขัดแย้งกับตะแกรงเข้ม: {why} — สปริงยังทยอยได้ตามสูตร "
                f"แต่ลดไม้ลงและห้ามรีบเติมจนกว่า stage จะหายแดง"
            )
        else:
            caution = None
        r.update(
            uipt.entry_verdict(
                asof_iso=asof,
                confirm_tf=confirm_tf,
                entry=r.get(entry_key),
                state_tag=uipt.state_tag(v),
                phase4=bool((v.get("_stage") or {}).get("p4")),
                dead=dead,
                dead_reason=(
                    "เงินรายสัปดาห์แจกของ (1W Dist) — โดน Kill-Switch"
                    if w1.get("status") == "Dist"
                    else f"stage {stage} — ระบบตัดออกจากสนามแล้ว"
                ),
                accumulate=accumulate,
            )
        )
        if caution:
            r["conflict_caution"] = caution
    return rows


# Bump this whenever the packs shape changes (field added / meaning changed) —
# rounds stored with an older version get their packs recomputed when read.
# (seen 13 Aug: old production rounds showed "⏳ —" because the 3-answer
# fields did not exist yet, and fingerprint reuse kept bringing those rounds back)
PACKS_VERSION = 3


_DEAD_STAGES = {"KILL", "FAIL", "NO-DATA"}
_SPRING_MAX_RISK = 6.0
_CONVICTION_MIN = 6.0
_SETUP_FIELDS = (
    "entry_breakout", "entry_pullback", "stop", "stop_tight", "tp1", "tp2", "rr_breakout",
    "rr_to_tp1", "pivot", "dist_to_pivot_pct",
)  # fmt: skip


def build_packs(state: dict) -> dict:
    """The deterministic action tables the page renders, all produced by lib —
    never re-derived here. Same numbers as run.sh on the stock-radar side."""
    views = state.get("views") or {}
    # Every table gives the same 3 answers: enter now? / from when? / latest when?
    # Near-pivot queue and conviction are short-medium trades confirmed on 4H · -ez/spring
    # are medium-long, confirmed on the daily bar · spring scales in, no breakout wait
    near = _entry_answers(state, lib.rank_short(views), confirm_tf="4h", entry_key="entry_breakout")
    conv = _entry_answers(
        state, _conviction_table(views), confirm_tf="4h", entry_key="entry_breakout"
    )
    ez = _entry_answers(state, _ez_table(views), confirm_tf="1d", entry_key="px_now")
    # SPRING has its own 7 gates (incl. 1W not Dist) — no second cut by the UIPT stage
    spring = _entry_answers(
        state,
        _spring_table(state, views),
        confirm_tf="1d",
        entry_key="entry_pullback",
        accumulate=True,
        respect_stage=False,
    )
    return {
        "_v": PACKS_VERSION,
        "near_pivot": near,
        "spring": spring,
        "ez": ez,
        "conviction": conv,
        "stage_gloss": dict(lib.STAGE_GLOSS),
        # UIPT-S / UIPT-M per the formula file's UIPT_HORIZON spec — lib.py has neither
        **uipt.packs(state),
        # Bar-close times / order days of this round (ET + Thai) from the real NYSE calendar;
        # every "wait"/"close" time on the page comes from here
        "clock": timing.clock_pack(state.get("asof_et")),
    }


def _spring_table(state: dict, views: dict) -> list:
    noneq = set((state.get("universe") or {}).get("noneq") or [])
    spring = []
    for s, v in views.items():
        if s in noneq:
            continue
        cs = lib.coiled_spring(v)
        if cs and cs["risk_score"] <= _SPRING_MAX_RISK:
            spring.append({"sym": s, **cs})
    spring.sort(key=lambda r: (r["risk_score"], -(r["rs60"] or -99)))
    return spring


def _ez_table(views: dict) -> list:
    ez = []
    for s, v in views.items():
        e, st = v.get("_stage_ez"), (v.get("_stage") or {}).get("stage")
        if not e or e.get("stage") == st or e.get("stage") in _DEAD_STAGES:
            continue
        ts = lib.trade_setup(v)
        ez.append(
            {
                "sym": s,
                "default_stage": st,
                "ez_stage": e["stage"],
                "px_now": v.get("px_now"),
                "rs60": e.get("rs60"),
                "ext200_pct": e.get("ext200_pct"),
                "horizon": lib.ez_horizon(e),
                "action": lib.ez_action(e, ts),
                "gloss": lib.stage_gloss(e["stage"]),
                "why": e.get("ez_reason"),
            }
        )
    ez.sort(key=lambda r: -(r["rs60"] or -99))
    return ez


def _conviction_table(views: dict) -> list:
    conv = []
    for s, v in views.items():
        best = _best_conviction(v)
        if best and best["score"] >= _CONVICTION_MIN and best["ts"]:
            horizon = lib.conviction_horizon(best["stage"], best["ez"], best.get("ext200"))
            conv.append(
                {
                    "sym": s,
                    "score": best["score"],
                    "via": "-ez" if best["ez"] else "UIPT",
                    "stage": best["stage"],
                    "gloss": lib.stage_gloss(best["stage"]),
                    "horizon": horizon,
                    "ext200_pct": best.get("ext200"),
                    "rs60": best.get("rs60"),
                    **{k: best["ts"].get(k) for k in _SETUP_FIELDS},
                }
            )
    conv.sort(key=lambda r: -r["score"])
    return conv


def _best_conviction(view: dict):
    """Higher of the UIPT and the -ez conviction for one symbol."""
    best = None
    for use_ez in (False, True):
        c = lib.conviction(view, use_ez)
        if c and (best is None or c["score"] > best["score"]):
            best = c
    return best
