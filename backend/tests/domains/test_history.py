"""History routes over a fake store: shapes, 404, range check and the cleanup report."""

import json
from datetime import UTC

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from tests.fakes import swap_repos

from zservice.domains.history import service


class FakeStore:
    def __init__(self):
        self.rows = [
            {
                "id": 7,
                "timestamp": "ts",
                "symbol": "AAA",
                "exchange": "NASDAQ",
                "interval": "1d",
                "extended_session": 0,
                "extra": "dropped",
            },
        ]
        self.count = 10

    def history_list(self):
        return self.rows

    def history_get_result(self, history_id):
        return json.dumps([{"close": 1.5}]) if history_id == 7 else None

    def history_delete_all(self):
        self.rows = []

    def history_count(self):
        return self.count

    def history_cleanup(self, cutoff):
        self.count = 4
        return 6


@pytest.fixture
def client(monkeypatch):

    from zservice.domains.history.routes import router

    swap_repos(monkeypatch, service, FakeStore())
    monkeypatch.setattr(service, "current_tz", lambda: UTC)
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_list_shape(client):
    assert client.get("/api/history").json() == [
        {
            "id": 7,
            "timestamp": "ts",
            "symbol": "AAA",
            "exchange": "NASDAQ",
            "interval": "1d",
            "extended_session": False,
        }
    ]


def test_detail_and_404(client):
    assert client.get("/api/history/7").json() == [{"close": 1.5}]
    assert client.get("/api/history/8").status_code == 404


def test_cleanup_range_and_report(client):
    assert client.post("/api/history/cleanup?hours=0").status_code == 400
    body = client.post("/api/history/cleanup?hours=3").json()
    assert list(body) == [
        "status", "deleted", "rows_before", "rows_after", "cutoff", "message", "code", "params",
    ]  # fmt: skip
    assert body["code"] == "history.cleaned" and body["params"]["deleted"] == body["deleted"]
    assert (body["deleted"], body["rows_before"], body["rows_after"]) == (6, 10, 4)
    assert body["message"].startswith("ลบ 6 ")


def test_clear(client):
    assert client.delete("/api/history").json() == {
        "status": "success",
        "message": "History cleared",
        "code": "history.cleared",
    }
