"""Watchlist grouping and portfolio position math, plus the routes over a fake store."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from tests.fakes import swap_repos

from zservice.domains.portfolio import service as portfolio
from zservice.domains.watchlist import service as watchlist


def _trade(port, sym, qty, price, action, ts="t"):
    return {
        "port_name": port,
        "symbol": sym,
        "quantity": qty,
        "buy_price": price,
        "timestamp": ts,
        "action": action,
    }


def test_portfolio_average_price_after_buys_and_a_sell():
    rows = [
        _trade("Main", "AAA", 10, 100.0, "buy"),
        _trade("Main", "AAA", 10, 110.0, "buy"),
        _trade("Main", "AAA", 5, 120.0, "sell"),
        _trade("Main", "BBB", 3, 50.0, "buy"),
        _trade("Main", "BBB", 3, 55.0, "sell"),  # closed: not a position
        _trade("Alt", "CCC", 1, 9.999, "buy"),
    ]
    out = portfolio.summarize(rows)
    assert list(out) == ["Main", "Alt"]
    assert out["Main"]["positions"] == [{"symbol": "AAA", "total_quantity": 15, "avg_price": 100.0}]
    assert out["Alt"]["positions"] == [{"symbol": "CCC", "total_quantity": 1, "avg_price": 10.0}]
    assert len(out["Main"]["history"]) == 5
    assert set(out["Main"]["history"][0]) == {
        "symbol",
        "quantity",
        "buy_price",
        "timestamp",
        "action",
    }


def test_unknown_action_is_kept_in_history_but_moves_nothing():
    out = portfolio.summarize([_trade("P", "X", 4, 10.0, "buy"), _trade("P", "X", 4, 1.0, "gift")])
    assert out["P"]["positions"] == [{"symbol": "X", "total_quantity": 4, "avg_price": 10.0}]
    assert len(out["P"]["history"]) == 2


def test_watchlist_groups_by_list_in_stored_order():
    rows = [
        {"list_name": "B", "symbol": "Y", "name": "y", "timestamp": "2", "exchange": "NYSE"},
        {"list_name": "A", "symbol": "X", "name": "x", "timestamp": "1"},
        {"list_name": "B", "symbol": "Z", "name": "z", "timestamp": "3"},
    ]
    out = watchlist.group_by_list(rows)
    assert list(out) == ["B", "A"]
    assert out["B"] == [
        {"symbol": "Y", "name": "y", "timestamp": "2"},
        {"symbol": "Z", "name": "z", "timestamp": "3"},
    ]


class FakeStore:
    def __init__(self):
        self.calls = []

    def __getattr__(self, name):
        def record(*args, **kwargs):
            self.calls.append((name, args, kwargs))
            if name == "watchlist_rename":
                raise RuntimeError("db down")
            return []

        return record


@pytest.fixture
def client(monkeypatch):
    from zservice.core import clock
    from zservice.domains.portfolio.routes import router as portfolio_router
    from zservice.domains.watchlist.routes import router as watchlist_router

    fake = FakeStore()
    for module in (portfolio, watchlist):
        swap_repos(monkeypatch, module, fake)
    monkeypatch.setattr(clock, "now_iso", lambda: "2026-10-24T12:00:00+07:00")
    monkeypatch.setattr(watchlist, "now_iso", clock.now_iso)
    monkeypatch.setattr(portfolio, "now_iso", clock.now_iso)
    app = FastAPI()
    app.include_router(watchlist_router)
    app.include_router(portfolio_router)
    return TestClient(app), fake


def test_watchlist_add_normalizes_exchange(client):
    c, fake = client
    body = {"symbol": "QQQ", "name": "Invesco QQQ Trust", "list_name": "X", "exchange": " nasdaq "}
    assert c.post("/api/watchlist", json=body).json() == {"status": "ok"}
    name, args, kwargs = fake.calls[-1]
    assert name == "watchlist_add" and kwargs == {"exchange": "NASDAQ"}
    assert args == ("X", "QQQ", "Invesco QQQ Trust", "2026-10-24T12:00:00+07:00")


def test_rename_rules(client):
    c, _ = client
    assert c.put("/api/watchlist/A", json={"new_name": "  "}).status_code == 400
    assert c.put("/api/watchlist/A", json={"new_name": "B"}).status_code == 500  # db error
    assert c.put("/api/portfolio/A", json={"new_name": "B"}).json() == {"status": "ok"}
