"""A round computed here must reproduce, line for line, the digest stock-radar produced from
the same CSV set — the guard against the two systems drifting apart (if radar_engine/lib.py
is ever edited locally instead of re-synced, this fails). Also: rounds stay idempotent,
never hide a partial set, and a crash never wedges the job.

Offline (store and CSV builders faked) but slow (~90 s: several full screens), so it runs
when asked: ZS_RUN_PARITY=1 venv/bin/python -m pytest tests/radar/test_rounds_parity.py
The commit gate runs it whenever radar/export code changes, with ZS_REQUIRE_PARITY=1 so a
missing reference set fails instead of skipping.
"""

import json
import os
import time

import pytest
from radar_engine import rounds
from radar_engine.rounds import compute, deps

from . import reference as ref
from .reference import FakeApp, FakeStore

pytestmark = pytest.mark.parity


@pytest.fixture(scope="module")
def world():
    if not ref.available():
        # The commit gate sets ZS_REQUIRE_PARITY=1: a parity check that cannot run must fail.
        missing = f"reference set not found ({ref.REF_CSV or ref.SR})"
        (pytest.fail if os.environ.get("ZS_REQUIRE_PARITY") == "1" else pytest.skip)(missing)
    store = FakeStore()
    deps.override(app=FakeApp(), store=store)
    res = rounds.run_round()
    yield res, store
    deps.reset()


@pytest.fixture
def fresh_store(world):
    """A copy of the store after the first full round, so a test can add rounds freely."""
    _, store = world
    copy = FakeStore(store.docs)
    deps.override(store=copy)
    yield copy
    deps.override(store=store)


def test_full_round_reproduces_the_stock_radar_digest(world):
    res, _ = world
    doc = res["round"]
    assert res["reused"] is False and doc["stamp"] == ref.STAMP, res
    with open(ref.REF_DIGEST, encoding="utf-8") as f:
        expected = ref.digest_lines(f.read())
    got = ref.digest_lines(doc["digest_md"])
    for i, (want, have) in enumerate(zip(expected, got, strict=False)):
        assert want == have, f"digest line {i + 1} differs:\n  want {want!r}\n  got  {have!r}"
    assert len(got) == len(expected), f"digest length: want {len(expected)}, got {len(got)}"
    portfolio = json.loads(doc["full_json"])["portfolio"]
    assert "Portfolio" not in doc["digest_md"] and not portfolio, "portfolio leaked into a round"


def test_round_metadata_is_complete_and_honest(world):
    doc = world[0]["round"]
    assert doc["partial"] is False and doc["screen_mode"] == "full", doc["screen_mode"]
    assert doc["timeframes"] == ["1w", "1d", "4h", "1h"], doc["timeframes"]
    assert doc["regime_hint"] and doc["kill_pct"] is not None
    assert doc["asof_et_iso"].endswith(("-04:00", "-05:00")), doc["asof_et_iso"]
    for tf, meta in doc["tf_meta"].items():
        assert meta["symbols_in_csv"] > 0, tf
        assert meta["fetched_at_max"] == FakeApp.TS[tf], tf
        assert meta["bar_asof_iso"].endswith(("-04:00", "-05:00")), (tf, meta["bar_asof_iso"])
    assert any(w["code"] == "radar.tf_older" and w["params"]["tf"] == "1W"
               for w in doc["warnings_coded"]), doc["warnings"]  # fmt: skip
    assert doc["warnings"] == [w["text"] for w in doc["warnings_coded"]]


def test_payloads_are_json_safe_and_carry_the_packs(world):
    doc = world[0]["round"]
    full, packs = json.loads(doc["full_json"]), json.loads(doc["packs_json"])
    assert full["fingerprint"] == doc["fingerprint"] and full["views"], "full_json broken"
    assert set(packs) == {"_v", "near_pivot", "spring", "ez", "conviction", "stage_gloss",
                          "uipt_s", "uipt_m", "clock"}, list(packs)  # fmt: skip
    # Stamped, so rounds stored by older code repair themselves when read.
    assert packs["_v"] == rounds.PACKS_VERSION
    for tf, bar in packs["clock"]["bars"].items():  # every "wait" carries both time zones
        assert "ET" in bar["both"] and "ไทย" in bar["both"], tf
    assert packs["clock"]["order"]["1d"]["order_open"]["date_et"], "no order day"
    for key, label in (("uipt_s", "S-3D"), ("uipt_m", "M-4W")):
        assert packs[key]["label"] == label and "picks" in packs[key], packs[key].get("label")
        assert all(p.get("hold_text") for p in packs[key]["picks"]), f"{key}: no holding period"


def test_spring_verdicts_come_from_its_own_gates(world):
    # Regression (2026-08-13): every spring got "do not enter" because the shared verdict
    # helper judged them by the UIPT stage — a different screen. A spring passed 7 gates
    # (incl. 1W not Dist): it is enterable (accumulate), and a KILL/FAIL strict stage shows
    # as a conflict note, not a ban.
    doc = world[0]["round"]
    full, packs = json.loads(doc["full_json"]), json.loads(doc["packs_json"])
    for row in packs["spring"]:
        assert row.get("can_enter_now") is True, (row["sym"], row.get("verdict_head"))
        stage = (full["views"][row["sym"]].get("_stage") or {}).get("stage") or ""
        if stage.startswith(("KILL", "FAIL")):
            assert row.get("conflict_caution"), f"{row['sym']}: stage {stage} conflict unflagged"


def test_new_record_keeps_kill_pct(world, fresh_store):
    # Regression (2026-08-14): the `_v2` counter reused the universe-size variable, so
    # kill_pct became kill_count/1*100 (the page showed 14600%) for every new_record round.
    first = world[0]["round"]
    second = rounds.run_round(new_record=True)["round"]
    for doc in (first, second):
        assert doc["breadth_n"] > 2 and 0 <= doc["kill_pct"] <= 100, doc["stamp"]
    assert (first["kill_pct"], first["breadth_n"]) == (second["kill_pct"], second["breadth_n"])
    assert second["stamp"].endswith("_v2"), second["stamp"]


def test_same_data_twice_reuses_the_round(fresh_store):
    again = rounds.run_round()
    assert again["reused"] is True and again["stamp"] == ref.STAMP, again
    assert len(fresh_store.docs) == 1, f"{len(fresh_store.docs)} rounds stored"


def test_partial_round_is_marked_and_says_what_it_lost(fresh_store):
    part = rounds.run_round(["1d", "1h"])["round"]
    assert part["partial"] is True and part["stamp"] != ref.STAMP
    assert part["timeframes"] == ["1d", "1h"], part["timeframes"]
    codes = {w["code"] for w in part["warnings_coded"]}
    assert {"radar.missing_1w_unselected", "radar.missing_4h_unselected"} <= codes, codes
    # 1d+1h falls into UIPT-S, whose structure gate IS 4H: the round must say so, or an
    # all-NO-DATA screen with kill% = 0 reads like a calm market.
    assert "radar.short_without_4h" in codes, codes
    assert len(fresh_store.docs) == 2


def test_bad_timeframes_are_rejected_before_any_work(world):
    for bad in (["1m"], ["daily"]):
        with pytest.raises(rounds.RadarError):
            rounds.run_round(bad)
    assert rounds.normalize_timeframes(["1h", "1w"]) == ["1w", "1h"]


def test_a_crash_ends_as_error_and_frees_the_lock(world, monkeypatch):
    # lib.run_screen raises SystemExit (not Exception) when it finds no CSVs, and a worker
    # thread swallows it silently: status must not stay "running" forever.
    def boom(*_args, **_kwargs):
        raise SystemExit("simulated screen failure")

    monkeypatch.setattr(compute, "run_round", boom)
    for _ in range(2):  # the second start proves the lock was released
        assert rounds.start_round(["1d"]) is True
        for _ in range(100):
            if rounds.round_status()["status"] != "running":
                break
            time.sleep(0.05)
        status = rounds.round_status()
        assert status["status"] == "error" and status["message_code"] == "radar.failed", status
        assert "simulated screen failure" in status["message"]
