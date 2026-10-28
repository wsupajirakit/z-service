"""Bar-close times and order days must be right in both US and Thai time.

User rule: every "wait" or "close" says what to wait for, which bar closes and when,
in both zones, and which day to place the order once the trigger fires.

The cases are the ones naive time guessing always breaks: crossing midnight in Thai
time, Friday to Monday, market holidays, half days and DST (ET -4 summer / -5 winter).

    venv/bin/python -m pytest tests/radar/test_timing.py
"""

from datetime import datetime

from radar_engine import timing as T


def test_every_time_always_comes_as_pair():
    # ---- every time always comes as a pair ---------------------------------
    f = T.fmt_both(datetime(2026, 8, 12, 16, 0, tzinfo=T.ET))
    assert "ET" in f["et"] and "ไทย" in f["th"] and "=" in f["both"], f
    assert "16:00" in f["et"] and "03:00" in f["th"], f  # 16:00 ET = 03:00 Thai time the next day
    assert "พุธ" in f["et"] and "พฤหัสฯ" in f["th"], "ข้ามเที่ยงคืนแล้ววันต้องเลื่อนด้วย"


def test_daily_bar_closes_at_16_00_et_bell():
    # ---- the daily bar closes at the 16:00 ET bell -------------------------
    b = T.bar_close("2026-08-12 11:15:00", "1d")
    assert b["date_et"] == "2026-08-12" and "16:00" in b["et"], b
    assert b["date_th"] == "2026-08-13", "ฝั่งไทยต้องเป็นวันถัดไป"


def test_4h_1h_follow_grid_of_bars_formula_uses_not_round_grid():
    # ---- 4H/1H follow the grid of the bars the formula uses, not a round grid
    # Confirmed on real CSVs (audit 2026-08-13): stock 4H bars start 01:30/05:30/09:30/13:30/17:30;
    # the formula keeps only the 09:30 and 13:30 bars => closes 13:30 and 17:30 ET (it used to be
    # 08:00/12:00/16:00, the index/FX grid — every row's wait time was 2.5 h off)
    b4 = T.bar_close("2026-08-12 11:15:00", "4h")
    assert "13:30" in b4["et"] and b4["date_et"] == "2026-08-12", b4["et"]
    b4 = T.bar_close("2026-08-12 14:00:00", "4h")
    assert "17:30" in b4["et"], b4["et"]
    b4 = T.bar_close("2026-08-12 18:00:00", "4h")
    assert "13:30" in b4["et"] and b4["date_et"] == "2026-08-13", b4["et"]


def test_1h_rth_bars_only_closes_10_00_16_00_after_close_next_one_is():
    # 1H: RTH bars only — closes 10:00–16:00 · after the close the next one is 10:00 tomorrow
    b1 = T.bar_close("2026-08-12 11:15:00", "1h")
    assert "12:00" in b1["et"], b1["et"]
    b1 = T.bar_close("2026-08-12 09:40:00", "1h")
    assert "10:00" in b1["et"], b1["et"]
    b1 = T.bar_close("2026-08-12 16:30:00", "1h")
    assert "10:00" in b1["et"] and b1["date_et"] == "2026-08-13", (
        f"หลังปิดตลาดต้องรอแท่ง RTH แรกของพรุ่งนี้ ได้ {b1['et']}"
    )


def test_weekly_bar_closes_on_friday():
    # ---- the weekly bar closes on Friday ----------------------------------
    w = T.bar_close("2026-08-12 11:15:00", "1w")
    assert w["date_et"] == "2026-08-14" and "ศุกร์" in w["et"], w


def test_friday_evening_order_is_for_monday_not_saturday():
    # ---- Friday evening -> the order is for Monday, not Saturday ----------
    o = T.order_window("2026-08-14 15:00:00", "1d")
    assert o["order_open"]["date_et"] == "2026-08-17", o["order_open"]
    assert "จันทร์" in o["order_open"]["et"], o["order_open"]["et"]


def test_market_holiday_labor_day_mon_7_sep_2026_is_skipped():
    # ---- market holiday: Labor Day, Mon 7 Sep 2026, is skipped ------------
    o = T.order_window("2026-09-04 15:00:00", "1d")  # the Friday before Labor Day
    assert o["order_open"]["date_et"] == "2026-09-08", (
        f"ต้องข้าม Labor Day ไปอังคาร ได้ {o['order_open']['date_et']}"
    )


def test_dst_in_winter_et_5_12_h_from_thai_time():
    # ---- DST: in winter ET = -5, 12 h from Thai time ----------------------
    win = T.bar_close("2026-12-15 11:00:00", "1d")
    assert "16:00" in win["et"] and "04:00" in win["th"], win


def test_dst_in_summer_et_4_11_h_from_thai_time():
    summer = T.bar_close("2026-08-12 11:00:00", "1d")
    assert "03:00" in summer["th"], "หน้าร้อน (EDT) ต้องต่าง 11 ชม."


def test_half_day_christmas_eve_24_dec_closes_13_00_et():
    # ---- half day (Christmas Eve, 24 Dec, closes 13:00 ET) ----------------
    half = T.bar_close("2026-12-24 10:00:00", "1d")
    assert "13:00" in half["et"], f"วันครึ่งวันต้องปิด 13:00 ET ได้ {half['et']}"
    assert "ครึ่งวัน" in half["label"], half["label"]


def test_round_s_time_pack_covers_every_tf_and_has_order_day():
    # ---- a round's time pack covers every TF and has the order day --------
    c = T.clock_pack("2026-08-12 11:15:00")
    assert set(c["bars"]) == {"1h", "4h", "1d", "1w"}, list(c["bars"])
    for tf, b in c["bars"].items():
        assert "ET" in b["both"] and "ไทย" in b["both"], f"{tf} ไม่มีสองเวลา"
    assert c["order"]["1d"]["text"].count("ET") >= 2, "ข้อความสั่งงานต้องมีสองเวลาครบ"


def test_unreadable_as_of_must_not_crash():
    # ---- an unreadable as-of must not crash -------------------------------
    assert T.bar_close("", "1d") is None and T.bar_close("ไม่ใช่เวลา", "1d") is None
    assert T.clock_pack(None)["bars"] == {}
