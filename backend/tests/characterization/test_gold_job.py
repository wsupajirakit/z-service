"""Characterization of the server-side gold job (analysis -> Drive -> Telegram).

The analysis, Drive upload, settings and Telegram are faked in every gold module.
Pins the job state and the exact Telegram text (finish-time line masked).
"""

import sys
from datetime import UTC

import pytest

from .golden import check

GOLD_PACKAGE = "zservice.domains.gold."
SECTIONED = (
    "### 1. **Bias ตอนนี้**: LONG <score 7/10> & rising\n"
    "detail a\n"
    "2. **โครงสร้าง**: skip me\n"
    "6. **กลยุทธ์**: Entry 2050 | SL 2040 | TP 2080 (R:R > 2)\n"
    "7. **ความเสี่ยง**: skip too\n"
)
PLAIN_LONG = "ไม่มีหัวข้อ & ยาวมาก <x> " * 200

CASES = {
    "sections_drive_ok": dict(analysis=SECTIONED, drive="ok", dest=(True, True), root="R"),
    "drive_failed": dict(analysis=SECTIONED, drive="raise", dest=(True, True), root="R"),
    "drive_failed_no_root": dict(analysis=SECTIONED, drive="raise", dest=(True, True), root=""),
    "plain_long_no_drive": dict(analysis=PLAIN_LONG, drive="ok", dest=(False, True), root="R"),
    "telegram_off": dict(analysis=SECTIONED, drive="ok", dest=(True, False), root="R"),
    "analysis_error": dict(analysis=None, drive="ok", dest=(True, True), root="R"),
}


@pytest.fixture
def gold_job(main_module, monkeypatch):
    mods = [mod.__dict__ for name, mod in sys.modules.items() if name.startswith(GOLD_PACKAGE)]

    def put(name, value):
        for mod in mods:
            if name in mod:
                monkeypatch.setitem(mod, name, value)

    from zservice.domains.gold import job

    return job, put


@pytest.mark.parametrize("case", sorted(CASES))
def test_run_gold_job(gold_job, env, case):
    job, put = gold_job
    c = CASES[case]
    sent = []

    def analyze(req):
        if c["analysis"] is None:
            raise RuntimeError("gemini <quota> & down")
        return {"source_label": "OANDA", "model": "m1", "latest_price": 2050.5,
                "analysis": c["analysis"]}  # fmt: skip

    def upload(result):
        if c["drive"] == "raise":
            raise OSError("drive down")
        return {"link": "https://drive/x", "name": "2026-10-24_gold"}

    put("_gold_analyze_core", analyze)
    put("drive_upload_gold_bundle", upload)
    put("get_dest_setting", lambda: {"dest_gold_drive": c["dest"][0],
                                     "dest_gold_telegram": c["dest"][1]})  # fmt: skip
    env(GDRIVE_ROOT_FOLDER_ID=c["root"] or None)
    put("send_telegram_message", sent.append)
    put("current_tz", lambda: UTC)
    put("current_tz_label", lambda: "UTC")
    job.run_gold_job(None)
    state = {k: job.gold_job[k] for k in ("status", "message", "folder_link", "folder_name")}
    assert job.gold_job["finished_at"]
    messages = [
        "\n".join("🏁 เสร็จ: <masked>" if ln.startswith("🏁") else ln for ln in m.split("\n"))
        for m in sent
    ]
    check(f"gold_job_{case}", {"state": state, "telegram": messages})
