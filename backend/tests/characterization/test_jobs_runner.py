"""Characterization of the fetch-job runner (custom + auto) before it moves out of main.py.

Everything external is faked: process_symbol, the store, Telegram and the Drive/Telegram
delivery. Fakes are installed in whichever module defines each function, so the same
tests keep running after the move.
"""

import inspect
import json
import sys
import threading
from datetime import UTC, datetime

import pytest

from zservice.core import job_state
from zservice.domains.jobs import runner as jobs_runner
from zservice.domains.jobs import schedule as jobs_schedule
from zservice.domains.jobs import step as jobs_step

JOBS_PACKAGE = "zservice.domains.jobs."
ET_MORNING = datetime.fromisoformat("2026-10-23T10:15:00-04:00")  # Friday, before the close
ET_EVENING = datetime.fromisoformat("2026-10-23T17:05:00-04:00")  # after the close


class Recorder:
    def __init__(self):
        self.upserts, self.settings, self.telegram, self.delivered = [], {}, [], []


@pytest.fixture
def runner(main_module, monkeypatch):
    m = main_module
    rec = Recorder()
    modules = {
        inspect.getmodule(f)
        for f in (jobs_runner.run_custom_job, jobs_runner.run_auto_job, jobs_step.run_step)
    }
    modules |= {inspect.getmodule(jobs_schedule.steps_due)}
    # Every module of the jobs package, so fakes keep applying however the runner is split.
    modules |= {mod for name, mod in sys.modules.items() if name.startswith(JOBS_PACKAGE)}

    def put(name, value):
        for mod in modules:
            if name in mod.__dict__:
                monkeypatch.setitem(mod.__dict__, name, value)

    def fake_process(sym, exch, tf, ext, rows, store=False):
        assert store is False  # the runner always batch-saves itself
        if sym == "BAD":
            raise RuntimeError("no data")
        return [{"sym": sym, "tf": tf, "ext": ext, "rows": rows}]

    from zservice.db.repos import history as history_repo
    from zservice.db.repos import settings as settings_repo

    monkeypatch.setattr(history_repo, "history_upsert", lambda *a: rec.upserts.append(a))
    monkeypatch.setattr(settings_repo, "settings_get", lambda k: rec.settings.get(k))
    monkeypatch.setattr(settings_repo, "settings_set", lambda k, v: rec.settings.__setitem__(k, v))
    put("process_symbol", fake_process)
    put("current_tz", lambda: UTC)
    put("current_tz_label", lambda: "UTC")
    put("send_telegram_message", lambda text: rec.telegram.append(text))
    put(
        "_deliver_stock_summary",
        lambda summary, do_upload: rec.delivered.append((summary, do_upload)),
    )
    job_state.stop_event.clear()
    yield m, rec, put
    job_state.stop_event.clear()


SYMS = [
    {"symbol": "AAA", "exchange": "NASDAQ"},
    {"symbol": "BAD", "exchange": "NYSE"},
    {"symbol": "CCC", "exchange": "NYSE"},
]


def test_steps_due_skips_timeframes_whose_bar_has_not_closed(runner):
    _m, rec, _ = runner
    rec.settings["auto_last_tf_bar_key"] = json.dumps(
        {
            "1h": "1h|2026-10-23|10",
            "4h": "4h|2026-10-23|2",
            "1d": "1d|2026-10-22",
            "1w": "1w|2026-10-22",
        }
    )
    jobs_schedule._load_tf_bar_keys()
    due, keys = jobs_schedule.steps_due(now_et=ET_MORNING)
    assert due == [("1h", True)] and keys == {"1h": "1h|2026-10-23|10"}  # nothing new: 1h only
    due, keys = jobs_schedule.steps_due(now_et=ET_EVENING)
    assert [tf for tf, _ in due] == ["1h", "4h", "1d", "1w"]
    assert keys["1d"] == "1d|2026-10-23" and keys["4h"] == "4h|2026-10-23|4"
    due, _ = jobs_schedule.steps_due(now_et=ET_MORNING, force_all=True)
    assert [tf for tf, _ in due] == ["1h", "4h", "1d", "1w"]


def test_custom_job_batches_one_timestamp_and_reports_failures(runner):
    _m, rec, _ = runner
    jobs_runner.run_custom_job(["1d", "1h"], SYMS, None, 80)
    assert job_state.job["status"] == "idle" and job_state.job["mode"] == "custom"
    assert job_state.job["failed"] == ["1d:BAD", "1h:BAD"]
    saved = [(a[0], a[2], a[3]) for a in rec.upserts]
    assert saved == [
        ("AAA", "1d", False),
        ("CCC", "1d", False),
        ("AAA", "1h", True),
        ("CCC", "1h", True),
    ]  # ext from EXTENDED_DEFAULT
    assert len({a[4] for a in rec.upserts if a[2] == "1d"}) == 1  # one timestamp per batch
    summary, upload = rec.delivered[-1]
    assert upload is True and "Automate เสร็จแล้ว" in summary and "สำเร็จ 2/3" in summary
    assert "❌ 1: BAD" in summary


def test_auto_job_runs_a_round_saves_keys_and_stops(runner):
    _m, rec, put = runner

    def deliver_then_stop(summary, do_upload):
        rec.delivered.append((summary, do_upload))
        job_state.stop_event.set()  # press stop during the cooldown

    put("_deliver_stock_summary", deliver_then_stop)
    jobs_runner.run_auto_job(SYMS[:1], 40)
    assert job_state.job["status"] == "stopped" and job_state.job["round"] == 1
    keys = json.loads(rec.settings["auto_last_tf_bar_key"])
    assert set(keys) <= {"1h", "4h", "1d", "1w"} and "1h" in keys
    assert rec.telegram[-1].startswith("⏹ <b>Auto Automate หยุดแล้ว</b>")
    assert "รอบที่ 1" in rec.delivered[0][0]


def _fail_bad(sym, exch, tf, ext, rows, store=False):
    if sym.startswith("BAD"):
        raise RuntimeError("no data")
    return [{"sym": sym}]


def test_custom_job_summary_text_lists_at_most_ten_failures(runner):
    _m, rec, put = runner
    put("process_symbol", _fail_bad)
    syms = [{"symbol": "OK1", "exchange": "NYSE"}]
    syms += [{"symbol": f"BAD{i:02}", "exchange": "NYSE"} for i in range(12)]
    jobs_runner.run_custom_job(["1w"], syms, True, 60)
    lines = rec.delivered[-1][0].split("\n")
    assert lines[0] == "✅ <b>Automate เสร็จแล้ว</b>"
    assert lines[1].startswith("🕒 เริ่ม: ") and lines[2].endswith(" (UTC)")
    assert lines[3:] == [
        "⏱ ใช้เวลา: 0 นาที 0 วินาที",
        "📊 Timeframes: 1w",
        "🔍 Filter: rows=60, symbols/TF=13",
        "",
        "• <b>1w</b> (ext=on): สำเร็จ 1/13 | ❌ 12: "
        + ", ".join(f"BAD{i:02}" for i in range(10))
        + " …",
    ]


def test_custom_job_stop_skips_the_save_and_the_drive_upload(runner):
    _m, rec, put = runner

    def process_then_stop(sym, exch, tf, ext, rows, store=False):
        job_state.stop_event.set()
        return [{"sym": sym}]

    put("process_symbol", process_then_stop)
    jobs_runner.run_custom_job(["1d", "1h"], SYMS, False, 80)
    assert job_state.job["status"] == "idle" and job_state.job["phase"] == "idle"
    assert rec.upserts == [] and job_state.job["current"] == 1
    summary, upload = rec.delivered[-1]
    assert upload is False and summary.startswith("⏹ <b>Automate หยุดแล้ว</b>")
    assert "• <b>1d</b> (ext=off): สำเร็จ 1/3" in summary and "<b>1h</b>" not in summary


def test_custom_job_resume_continues_from_the_saved_step_and_symbol(runner):
    _m, rec, _ = runner
    job_state.job.update({"step_index": 2, "current": 1, "failed": ["1d:BAD"], "status": "stopped"})
    jobs_runner.run_custom_job(["1d", "1h"], SYMS, None, 80, resume=True)
    assert [(a[0], a[2]) for a in rec.upserts] == [("CCC", "1h")]
    assert job_state.job["failed"] == ["1d:BAD", "1h:BAD"] and job_state.job["step_index"] == 2
    assert job_state.job["status"] == "idle" and "สำเร็จ 1/3" in rec.delivered[-1][0]


def test_custom_job_error_is_reported_html_escaped(runner):
    _m, rec, put = runner

    def boom(summary, do_upload):
        raise RuntimeError("<drive down>")

    put("_deliver_stock_summary", boom)
    jobs_runner.run_custom_job(["1d"], SYMS[:1], None, 80)
    assert job_state.job["status"] == "error" and job_state.job["message"] == "<drive down>"
    assert job_state.job["phase"] == "idle" and job_state.job["finished_at"]
    assert rec.telegram == ["❌ <b>Automate error</b>\n&lt;drive down&gt;"]


def test_auto_job_error_is_reported_html_escaped(runner):
    _m, rec, put = runner

    def boom(force_all=False):
        raise RuntimeError("a&b")

    put("steps_due", boom)
    jobs_runner.run_auto_job(SYMS[:1], 40, force_all_tf=True)
    assert job_state.job["status"] == "error" and job_state.job["csv_mode"] == "legacy"
    assert rec.telegram == ["❌ <b>Auto Automate error</b>\na&amp;b"]


def test_auto_job_stop_mid_round_skips_summary_and_cooldown(runner):
    _m, rec, put = runner

    def process_then_stop(sym, exch, tf, ext, rows, store=False):
        job_state.stop_event.set()
        return [{"sym": sym}]

    put("process_symbol", process_then_stop)
    jobs_runner.run_auto_job(SYMS[:1], 40, force_all_tf=True)
    assert job_state.job["status"] == "stopped" and job_state.job["cooldown_until"] is None
    assert rec.delivered == [] and job_state.job["timeframes"] == ["1h", "4h", "1d", "1w"]
    assert rec.telegram == ["⏹ <b>Auto Automate หยุดแล้ว</b> (จบที่รอบ 1)"]


def test_start_worker_is_single_flight(runner):
    from zservice.domains.jobs import routes

    release, ran = threading.Event(), threading.Event()

    def target():
        ran.set()
        release.wait(5)

    assert routes.start_worker(target) is True
    assert ran.wait(5)
    assert routes.start_worker(target) is False  # a job is already running
    release.set()
    for _ in range(100):
        if routes.start_worker(lambda: None):
            break
        threading.Event().wait(0.05)
    else:
        raise AssertionError("lock was not released after the job ended")
