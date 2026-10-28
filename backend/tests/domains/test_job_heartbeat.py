"""B12: autostart never launches a second auto job while another container's is alive."""

import json

import pytest
from tests.fakes import swap_repos

from zservice.domains.jobs import autostart, heartbeat


class FakeStore:
    def __init__(self):
        self.data = {}

    def settings_get(self, key):
        return self.data.get(key)

    def settings_set(self, key, value):
        self.data[key] = value


@pytest.fixture
def fake(monkeypatch):
    store = FakeStore()
    swap_repos(monkeypatch, heartbeat, store)
    heartbeat._last_write["at"] = 0.0
    return store


def test_beat_is_rate_limited_and_clear_marks_stale(fake, monkeypatch):
    times = iter([1000.0, 1010.0, 1100.0])
    monkeypatch.setattr(heartbeat.time, "time", lambda: next(times))
    heartbeat.beat()
    first = json.loads(fake.data[heartbeat.KEY])
    heartbeat.beat()  # 10 s later: skipped
    assert json.loads(fake.data[heartbeat.KEY]) == first
    heartbeat.beat()  # 100 s later: written
    assert json.loads(fake.data[heartbeat.KEY])["at"] == 1100.0
    heartbeat.clear()
    assert json.loads(fake.data[heartbeat.KEY])["at"] == 0


def test_other_owner_alive_only_when_fresh_and_not_us(fake, env):
    env(ZS_JOB_HEARTBEAT_STALE_S="180")
    fake.data[heartbeat.KEY] = json.dumps({"owner": "old-container:1", "at": 1000.0})
    assert heartbeat.other_owner_alive(now=1000.0 + 60) == "old-container:1"
    assert heartbeat.other_owner_alive(now=1000.0 + 180 + 1) is None
    fake.data[heartbeat.KEY] = json.dumps({"owner": heartbeat.OWNER, "at": 1000.0})
    assert heartbeat.other_owner_alive(now=1001.0) is None


def test_autostart_waits_for_the_old_container_then_takes_over(fake, monkeypatch):
    alive = iter(["old:1", "old:1", None])
    sleeps = []
    monkeypatch.setattr(heartbeat, "other_owner_alive", lambda: next(alive))
    monkeypatch.setattr(autostart.time, "sleep", lambda s: sleeps.append(s))
    assert autostart._wait_for_other_container() is True
    assert sleeps == [autostart.TAKEOVER_POLL_S, autostart.TAKEOVER_POLL_S]
