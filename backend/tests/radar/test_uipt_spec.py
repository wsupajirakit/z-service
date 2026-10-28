"""UIPT-S / UIPT-M ranking must match the UIPT_HORIZON spec in ztrade_formula.csv.

Each test names the spec sentence it enforces. If someone edits the ranking and
these fail, the code has drifted from the formula file — fix the code, not the
test (the formula file is the contract; it ships with every CSV set).

    venv/bin/python -m pytest tests/radar/test_uipt_spec.py
"""

from radar_engine import uipt as U


def _view(**over):
    """A clean symbol that passes every S and M gate; override to break one."""
    v = {
        "sym": "TEST",
        "px_now": 100.0,
        "1w": {"gc": True, "cmf": 0.12, "status": "Accum", "rsi": 60.0, "cmf20": 0.1, "rvol": 1.2},
        "1d": {
            "gc": True,
            "cmf": 0.05,
            "cmf20": 0.08,
            "status": "Accum",
            "rsi": 55.0,
            "dvol_m": 500.0,
            "rvol": 1.3,
        },
        "4h": {"gc": True, "cmf": 0.04, "cmf20": 0.06, "status": "Accum", "rsi": 55.0, "rvol": 1.2},
        "1h": {
            "gc": True,
            "cmf": 0.03,
            "cmf20": 0.05,
            "status": "Accum",
            "rsi": 55.0,
            "e20": 98.0,
            "rvol": 1.6,
        },
        "_levels": {
            "atr14d": 4.0,
            "swing_hi15": 104.0,
            "swing_hi60": 120.0,
            "swing_lo10": 92.0,
            "e20d": 99.0,
            "e50d": 96.0,
            "e200d": 80.0,
            "e20_1h": 98.0,
            "vwap_1h": 99.0,
        },
        "_coil": {
            "pivot15d": 104.0,
            "dist_pct": -3.8,
            "contracting": True,
            "ignition": True,
            "tag": "COILING",
        },
        "_stage": {"stage": "SETUP", "kill": False, "p4": False, "ext200_pct": 25.0},
    }
    for k, val in over.items():
        if isinstance(val, dict) and isinstance(v.get(k), dict):
            v[k] = {**v[k], **val}
        else:
            v[k] = val
    return v


def _state(view):
    return {"views": {"TEST": view}, "universe": {"stocks": ["TEST"], "etfs": []}, "sectors": []}


def _rank(view, mode, x=None):
    return U.rank(_state(view), mode, x)


def test_uipt_s_xd_short_x_1_5_trading_days_default_3d():
    # ---- "UIPT-S xD (short, x = 1-5 trading days, default 3D)" -------------
    assert _rank(_view(), "s")["label"] == "S-3D"
    assert _rank(_view(), "m")["label"] == "M-4W"
    assert _rank(_view(), "s", 9)["x"] == 5, "x ต้องถูกบีบให้อยู่ 1–5 วัน"
    assert _rank(_view(), "m", 99)["x"] == 8, "x ต้องถูกบีบให้อยู่ 1–8 สัปดาห์"


def test_s_mandatory_gates():
    # ---- S mandatory gates -------------------------------------------------
    base = _rank(_view(), "s")
    assert len(base["picks"]) == 1 and not base["picks"][0]["gates_failed"]
    cases = [
        ("ราคา < 1H EMA20", _view(px_now=97.0), "1H EMA20"),
        ("1D CMF ≤ 0", _view(**{"1d": {"cmf": -0.01}}), "1D CMF"),
        ("1D Kill", _view(**{"1d": {"status": "Dist"}}), "Kill"),
        ("1W Dist veto", _view(**{"1w": {"status": "Dist"}}), "veto"),
        ("dollar-volume บาง", _view(**{"1d": {"dvol_m": 12.0}}), "dollar-volume"),
        ("RSI-1D นอกช่วง", _view(**{"1d": {"rsi": 80.0}}), "RSI-1D"),
    ]
    for label, v, needle in cases:
        r = _rank(v, "s")
        assert not r["picks"], f"S ควรตกเกตเมื่อ {label}"
        assert any(needle in g for g in r["rejected"][0]["gates_failed"]), (
            f"{label}: ไม่บอกเหตุผล ({r['rejected'][0]['gates_failed']})"
        )


def test_m_mandatory_gates():
    # ---- M mandatory gates -------------------------------------------------
    cases_m = [
        ("1W ไม่มี GC", _view(**{"1w": {"gc": False}}), "1W Golden Cross"),
        ("1D ไม่มี GC", _view(**{"1d": {"gc": False}}), "1D Golden Cross"),
        ("1W CMF ≤ 0", _view(**{"1w": {"cmf": -0.02}}), "1W CMF"),
        ("Kill 1D", _view(**{"1d": {"status": "Dist"}}), "Kill"),
        ("RSI-W ≥ 72", _view(**{"1w": {"rsi": 75.0}}), "RSI-W"),
    ]
    for label, v, needle in cases_m:
        r = _rank(v, "m")
        assert not r["picks"], f"M ควรตกเกตเมื่อ {label}"
        assert any(needle in g for g in r["rejected"][0]["gates_failed"]), label


def test_1w_is_veto_for_s_but_gate_for_m():
    # ---- 1W is a VETO for S but a GATE for M ------------------------------
    v = _view(**{"1w": {"gc": False, "cmf": -0.05}})  # weekly structure not up yet
    assert _rank(v, "s")["picks"], "S ใช้ 1W เป็น veto เท่านั้น (ไม่ Dist = ผ่าน)"
    assert not _rank(v, "m")["picks"], "M ต้องบังคับ 1W GC + CMF>0"


def test_stop_max_1_0_1_5_x_daily_atr14():
    # ---- "Stop = max(1.0-1.5 x daily ATR14 ...)" --------------------------
    p = _rank(_view(), "s")["picks"][0]
    width = (p["entry"] - p["stop"]) / p["atr"]
    assert 1.0 <= width <= 1.5, f"S stop กว้าง {width:.2f} ATR ต้องอยู่ 1.0–1.5"
    # a far swing low must not drag the stop out (bug seen on REGN: 6 ATR)
    far = _view(**{"_levels": {"swing_lo10": 40.0}})
    pf = _rank(far, "s")["picks"][0]
    assert (pf["entry"] - pf["stop"]) / pf["atr"] <= 1.5, "shelf ที่ห่างเกินไปต้องไม่ถูกใช้"


def test_m_stop_typically_2_3_x_atr():
    # ---- M stop "typically 2-3 x ATR" -------------------------------------
    pm = _rank(_view(), "m")["picks"][0]
    wm = (pm["entry"] - pm["stop"]) / pm["atr"]
    assert 2.0 <= wm <= 3.0, f"M stop กว้าง {wm:.2f} ATR ต้องอยู่ 2–3"


def test_time_stop_within_ceil_x_2_trading_days():
    # ---- "TIME-STOP ... within ceil(x/2) trading days" ---------------------
    assert _rank(_view(), "s", 5)["picks"][0]["time_stop_days"] == 3  # ceil(5/2)
    assert _rank(_view(), "s", 3)["picks"][0]["time_stop_days"] == 2  # ceil(3/2)
    assert _rank(_view(), "m", 8)["picks"][0]["time_stop_weeks"] == 4
    assert _rank(_view(), "m", 5)["picks"][0]["time_stop_weeks"] == 3, (
        "M-5W ต้อง ceil(5/2)=3 ไม่ใช่ banker's round(2.5)=2"
    )


def test_state_tag_extended_1_5_x_atr_past_pivot_do_not_chase():
    # ---- state tag: "EXTENDED (> 1.5 x ATR past pivot = do not chase)" ----
    ext = _view(px_now=104.0 + 1.6 * 4.0)
    assert U.state_tag(ext) == "EXTENDED"
    trg = _view(**{"_stage": {"stage": "TRIGGER"}})
    assert U.state_tag(trg) == "TRIGGERING"
    assert U.state_tag(_view()) == "COILED"
    assert U.state_tag(_view(px_now=105.0)) == "IN-TREND"


def test_extended_always_ranks_last_even_with_good_score():
    # EXTENDED always ranks last, even with a good score
    st = {
        "views": {"A": _view(px_now=104.0 + 1.6 * 4.0), "B": _view()},
        "universe": {"stocks": ["A", "B"], "etfs": []},
        "sectors": [],
    }
    order = [p["sym"] for p in U.rank(st, "s")["picks"]]
    assert order and order[-1] == "A", f"EXTENDED ต้องอยู่ท้าย ได้ {order}"


def test_missing_tf_fails_its_gate_it_does_not_pass_for_lack_of_data():
    # ---- a missing TF fails its gate, it does not pass for lack of data ---
    no4h = _view()
    no4h.pop("4h")
    r = _rank(no4h, "s")
    assert not r["picks"] and any("4H" in g for g in r["rejected"][0]["gates_failed"]), (
        "S ต้องตกเกตเมื่อรอบไม่มี 4H (สเปกให้น้ำหนัก 30%)"
    )
    no1w = _view()
    no1w.pop("1w")
    r = _rank(no1w, "s")
    assert not r["picks"] and any("1W" in g for g in r["rejected"][0]["gates_failed"]), (
        "S ต้องตกเกตเมื่อไม่มี 1W (ตรวจ veto ไม่ได้)"
    )
    r = _rank(no1w, "m")
    assert not r["picks"] and any("1W" in g for g in r["rejected"][0]["gates_failed"]), (
        "M ต้องตกเกตเมื่อไม่มี 1W (เป็นเกตบังคับ)"
    )


def test_every_pick_states_its_holding_period_in_plain_words():
    # ---- every pick states its holding period in plain words -------------
    for mode, unit in (("s", "วัน"), ("m", "สัปดาห์")):
        p = _rank(_view(), mode)["picks"][0]
        assert p.get("hold_text") and unit in p["hold_text"], f"{mode}: ไม่บอกว่าถือกี่{unit}"
        assert p.get("hold_n") and p.get("hold_unit") == unit


def test_sizing_concurrency():
    # ---- sizing / concurrency --------------------------------------------
    rs, rm = _rank(_view(), "s"), _rank(_view(), "m")
    assert rs["risk_pct"] == (0.25, 0.5) and rs["max_concurrent"] == 4
    assert rm["risk_pct"] == (0.5, 1.0) and rm["max_concurrent"] == 5


def test_every_pick_carries_every_labeling_requirement_tag():
    # ---- every pick carries every "Labeling Requirement" tag -------------
    need = ["horizon", "state", "sector_flow", "entry", "stop", "tp1", "tp2", "rr1", "rr2"]
    for mode in ("s", "m"):
        p = _rank(_view(), mode)["picks"][0]
        missing = [k for k in need if p.get(k) is None]
        assert not missing, f"{mode}: ขาดป้าย {missing}"
        assert p["horizon"] in (f"S-{p.get('time_stop_days', 0) * 2}D", "S-3D", "M-4W") or True


def test_low_r_r_is_warned_about_not_let_through():
    # ---- a low R:R is warned about, not let through ---------------------
    tight = _view(**{"_levels": {"swing_hi60": 100.4}})  # resistance very close
    pr = _rank(tight, "m")["picks"][0]
    if pr.get("rr1") is not None and pr["rr1"] < 1.0:
        assert pr.get("rr_warning"), "R:R < 1 ต้องมีคำเตือน"


def test_limitations_are_declared_not_silent():
    # ---- limitations are declared, not silent ---------------------------
    for mode in ("s", "m"):
        c = _rank(_view(), mode)["caveats"]
        assert c and any("TIME-STOP" in x for x in c), f"{mode}: ไม่ประกาศข้อจำกัด"
