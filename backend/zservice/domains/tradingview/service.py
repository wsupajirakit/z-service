"""TradingView connection self-test (/api/tv/test): auth mode, circuit breaker, then a
fetch probe per symbol and a verdict. Log texts are shown as-is by the dashboards.

Probes use throwaway connections so the shared fetch path is untouched.
"""

import base64
import concurrent.futures
import contextlib
import json
import time
from datetime import datetime

from tvDatafeed import Interval

from zservice.core.clock import current_tz
from zservice.core.messages import coded
from zservice.integrations.tradingview import config as tv_config
from zservice.integrations.tradingview.auth import STATE, current_auth_token
from zservice.integrations.tradingview.client import make_tv
from zservice.integrations.tradingview.throttle import THROTTLE

PROBES = [
    ("AAPL", "NASDAQ"),
    ("XAUUSD", "OANDA"),
]
PROBE_BARS = 50
CONNECT_TIMEOUT_S = 10
FETCH_TIMEOUT_S = 20
SLOW_PROBE_S = 5  # a probe slower than this hints at soft-throttling

VERDICTS = {
    "ok": ("เชื่อมต่อ TradingView ปกติ ✓", "ok"),
    "slow": ("เชื่อมต่อได้แต่ช้า — น่าจะโดน soft-throttle อยู่ ควรพัก 5-15 นาทีก่อนรัน job", "warn"),
    "partial": ("เชื่อมต่อได้บางส่วน — โดน limit เป็นช่วงๆ ควรพักก่อนรัน job", "warn"),
    "down": (
        "เชื่อมต่อไม่ได้ / ติด limit — พัก 5-15 นาที ปิดแท็บ TradingView ใน browser แล้วทดสอบใหม่",
        "error",
    ),
}


VERDICT_CODES = {key: f"tv.verdict_{key}" for key in VERDICTS}
# Picked at run time from VERDICT_CODES; declared literally for the translation check.
MESSAGE_CODES = {"tv.verdict_ok": (), "tv.verdict_slow": (), "tv.verdict_partial": (),
                 "tv.verdict_down": ()}  # fmt: skip


def connection_test() -> dict:
    """Probe TradingView with the active auth mode and report each step."""
    logs = []

    def log(message: dict, level="info"):
        time_text = datetime.now(current_tz()).strftime("%H:%M:%S")
        entry = {"time": time_text, "level": level, "message": message["text"]}
        logs.append({**entry, "code": message["code"], "params": message["params"]})

    t_start = time.time()
    _report_auth_mode(log)
    _report_cooldown(log)
    outcomes = []
    for i, (sym, exch) in enumerate(PROBES):
        if i > 0:
            time.sleep(tv_config.get_settings().min_request_interval)
        outcomes.append(_probe(sym, exch, log))

    passed = sum(o in ("ok", "slow") for o in outcomes)
    total = len(PROBES)
    key = _verdict_key(passed, total, slow="slow" in outcomes)
    verdict, vlevel = VERDICTS[key]
    summary = coded(VERDICT_CODES[key], f"สรุป: {verdict}")
    code = summary["code"]
    log(summary, vlevel)
    return {
        "ok": passed == total,
        "verdict": verdict,
        "verdict_code": code,
        "verdict_level": vlevel,
        "passed": passed,
        "total": total,
        "duration": round(time.time() - t_start, 1),
        "logs": logs,
    }


def _report_auth_mode(log) -> None:
    """Which auth is active right now (login > manual token > anonymous)."""
    cfg = tv_config.get_settings()
    manual_tok, username = cfg.auth_token.get_secret_value(), cfg.username
    active = current_auth_token()
    if username and active and active == STATE.token:
        mins = (STATE.exp - time.time()) / 60 if STATE.exp else 0
        text = f"login ด้วย TV_USERNAME ({username}) สำเร็จ — token เหลือ {mins:.0f} นาที (ต่ออายุอัตโนมัติ)"
        log(coded("tv.login_ok", text, username=username, minutes=round(mins)), "ok")
    elif active and active == manual_tok:
        if username:
            text = (
                f"login ด้วย TV_USERNAME ({username}) ไม่สำเร็จ — "
                "fallback มาใช้ TV_AUTH_TOKEN (เช็ค user/pass)"
            )
            log(coded("tv.login_failed_token_used", text, username=username), "warn")
        _report_manual_token(log, manual_tok)
    elif username:
        text = f"login ด้วย TV_USERNAME ({username}) ไม่สำเร็จและไม่มี token สำรอง — โหมด anonymous"
        log(coded("tv.login_failed_anonymous", text, username=username), "warn")
    else:
        text = "ไม่มี token/login — โหมด anonymous จะโดน limit ง่ายกว่าปกติ"
        log(coded("tv.anonymous", text), "warn")


def _report_manual_token(log, token: str) -> None:
    """Remaining lifetime from the JWT's exp claim (read, never verified: display only)."""
    try:
        payload = json.loads(base64.urlsafe_b64decode(token.split(".")[1] + "=="))
        mins = (payload["exp"] - time.time()) / 60
    except Exception:
        log(coded("tv.token_unreadable", "ใช้ TV_AUTH_TOKEN (อ่านวันหมดอายุจาก token ไม่ได้)"), "warn")
        return
    if mins > 0:
        text = f"ใช้ TV_AUTH_TOKEN — เหลืออายุอีก {mins:.0f} นาที"
        log(coded("tv.token_ok", text, minutes=round(mins)), "ok")
    else:
        text = f"TV_AUTH_TOKEN หมดอายุแล้ว ({-mins:.0f} นาทีก่อน) — เอา token ใหม่มาใส่ หรือลบทิ้ง"
        log(coded("tv.token_expired", text, minutes=round(-mins)), "warn")


def _report_cooldown(log) -> None:
    cooldown_left = THROTTLE.cooldown_left()
    if cooldown_left > 0:
        text = (
            f"Circuit breaker กำลังพัก request อีก {cooldown_left:.0f} วิ (เพิ่งเจอ limit) — "
            "ทดสอบข้ามช่วงพักให้เลย"
        )
        log(coded("tv.cooldown_active", text, seconds=round(cooldown_left)), "warn")
    else:
        text = "ไม่มี cooldown ค้าง — ระบบไม่ได้เจอ limit ในช่วงที่ผ่านมา"
        log(coded("tv.cooldown_none", text), "info")


def _probe(sym: str, exch: str, log) -> str:
    """One fetch on a throwaway connection: 'ok', 'slow', 'empty', 'timeout' or 'error'."""
    target = f"{exch}:{sym}"
    probe_tv = None
    probe_ex = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    t0 = time.time()
    try:
        probe_tv = probe_ex.submit(make_tv).result(timeout=CONNECT_TIMEOUT_S)
        df = probe_ex.submit(
            probe_tv.get_hist,
            symbol=sym,
            exchange=exch,
            interval=Interval.in_1_hour,
            n_bars=PROBE_BARS,
            extended_session=False,
        ).result(timeout=FETCH_TIMEOUT_S)
        elapsed = time.time() - t0
        if df is None or df.empty:
            text = f"{target} ตอบกลับว่างใน {elapsed:.1f} วิ — โดน limit หรือ connection โดนตัด"
            log(coded("tv.probe_empty", text, target=target, seconds=f"{elapsed:.1f}"), "error")
            return "empty"
        bars, seconds = len(df), f"{elapsed:.1f}"
        if elapsed > SLOW_PROBE_S:
            text = f"{target} ดึงได้ {len(df)} แท่งใน {elapsed:.1f} วิ — ช้าผิดปกติ อาจโดน soft-throttle"
            log(coded("tv.probe_slow", text, target=target, bars=bars, seconds=seconds), "warn")
            return "slow"
        text = f"{target} ดึงได้ {len(df)} แท่งใน {elapsed:.1f} วิ"
        log(coded("tv.probe_ok", text, target=target, bars=bars, seconds=seconds), "ok")
        return "ok"
    except concurrent.futures.TimeoutError:
        waited = f"{time.time() - t0:.0f}"
        text = f"{target} ค้างเกิน {waited} วิ — เข้าข่ายโดน throttle/limit"
        log(coded("tv.probe_timeout", text, target=target, seconds=waited), "error")
        return "timeout"
    except Exception as e:
        log(coded("tv.probe_error", f"{target} error: {e}", target=target, error=str(e)), "error")
        return "error"
    finally:
        probe_ex.shutdown(wait=False, cancel_futures=True)
        with contextlib.suppress(Exception):  # best-effort socket cleanup
            if probe_tv is not None and getattr(probe_tv, "ws", None) is not None:
                probe_tv.ws.shutdown()


def _verdict_key(passed: int, total: int, slow: bool) -> str:
    if passed == total:
        return "slow" if slow else "ok"
    return "partial" if passed > 0 else "down"
