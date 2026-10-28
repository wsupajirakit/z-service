"""Settings service + routes with an in-memory store (no Mongo)."""

from datetime import timedelta

import pytest
from tests.fakes import swap_repos

from zservice.domains.settings import service


class FakeStore:
    def __init__(self, data=None, broken=False):
        self.data = dict(data or {})
        self.broken = broken

    def settings_get(self, key):
        if self.broken:
            raise RuntimeError("db down")
        return self.data.get(key)

    def settings_get_many(self, keys):
        return {k: self.data[k] for k in keys if k in self.data}

    def settings_set(self, key, value):
        self.data[key] = value


@pytest.fixture
def fake(monkeypatch):
    from zservice.core import clock
    from zservice.integrations.tradingview import mode

    store = FakeStore()
    for module in (service, clock, mode):
        swap_repos(monkeypatch, module, store)
    return store


def test_timezone_defaults_and_round_trip(fake):
    assert service.get_tz_setting() == {"offset_minutes": 420, "label": "Asia/Bangkok (UTC+7)"}
    service.set_tz_setting(120, "Europe/Rome (UTC+2)")
    assert service.current_tz().utcoffset(None) == timedelta(minutes=120)
    assert service.current_tz_label() == "Europe/Rome (UTC+2)"


def test_bad_stored_offset_falls_back_to_default(fake):
    fake.data["tz_offset_minutes"] = "not-a-number"
    assert service.get_tz_setting()["offset_minutes"] == 420


def test_int_settings_default_when_unset_or_db_broken(fake, monkeypatch):
    assert service.get_tv_mode_setting() == 3
    assert service.get_auto_skip_minutes_setting() == 15
    from zservice.integrations.tradingview import mode

    broken = FakeStore(broken=True)
    swap_repos(monkeypatch, service, broken)
    swap_repos(monkeypatch, mode, broken)
    assert service.get_tv_mode_setting() == 3
    assert service.get_auto_skip_minutes_setting() == 15


def test_destinations_default_on_and_partial_update(fake):
    assert all(service.get_dest_setting().values())
    service.set_dest_setting({"dest_gold_telegram": False, "unknown": False})
    dest = service.get_dest_setting()
    assert dest["dest_gold_telegram"] is False and dest["dest_stock_drive"] is True
    assert "unknown" not in fake.data


def test_routes_validate_ranges(fake):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from zservice.domains.settings.routes import router

    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    assert (
        client.post(
            "/api/settings/timezone", json={"offset_minutes": 900, "label": "x"}
        ).status_code
        == 400
    )
    ok = client.post("/api/settings/timezone", json={"offset_minutes": 60, "label": "  "})
    assert ok.json() == {"offset_minutes": 60, "label": "Asia/Bangkok (UTC+7)"}
    assert client.post("/api/settings/auto_skip_minutes", json={"minutes": 0}).status_code == 400
    assert client.post("/api/settings/auto_skip_minutes", json={"minutes": 30}).json() == {
        "minutes": 30
    }
