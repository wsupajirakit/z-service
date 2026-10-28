"""Security pass 25 Oct: bounded request bodies and fields, Gemini model names."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from zservice.core.errors import ApiError
from zservice.domains.jobs.schemas import AutomateRequest
from zservice.domains.stock_radar.schemas import StockRadarRequest
from zservice.integrations import gemini
from zservice.security import tokens as session_auth
from zservice.security.body_limit import BodySizeLimit


@pytest.fixture
def client():
    import main

    return TestClient(main.app, raise_server_exceptions=False)


def _bearer():
    return {"Authorization": f"Bearer {session_auth.create_token('me')}"}


def test_symbol_entries_must_be_plain_strings():
    ok = AutomateRequest(timeframes=["1d"], symbols=[{"symbol": "AAA", "exchange": "NYSE",
                                                     "name": "Kept"}])  # fmt: skip
    assert ok.symbols == [{"symbol": "AAA", "exchange": "NYSE", "name": "Kept"}]
    for bad in ({"symbol": {"$ne": None}}, {"symbol": ""}, {"symbol": "X" * 33}, {}):
        with pytest.raises(ValidationError):
            AutomateRequest(timeframes=["1d"], symbols=[bad])


def test_rows_and_lists_are_bounded(client):
    body = {"timeframes": ["1d"], "symbols": [{"symbol": "AAA"}], "rows": 10**7}
    assert client.post("/api/automate", json=body, headers=_bearer()).status_code == 422
    many = {"timeframes": ["1d"] * 9, "symbols": [{"symbol": "AAA"}]}
    assert client.post("/api/automate", json=many, headers=_bearer()).status_code == 422
    with pytest.raises(ValidationError):
        StockRadarRequest(symbols=[], formulas=["x" * 4001], timeframes=["1d"])


def test_model_name_cannot_leave_its_path_segment(monkeypatch):
    with pytest.raises(ValidationError):
        StockRadarRequest(symbols=[], formulas=[], timeframes=[], model="../../v1/files")
    monkeypatch.setattr(gemini.urllib.request, "urlopen", pytest.fail)  # must not be called
    for bad in ("../x", "a/b", "m?key=1", "a..b", ""):
        with pytest.raises(ApiError) as err:
            gemini.call_gemini(bad, "hi")
        assert err.value.code == "ai.invalid_model"


def test_body_over_the_cap_is_refused_before_the_route():
    seen = []
    app = FastAPI()

    @app.post("/echo")
    async def echo(request: __import__("fastapi").Request):
        seen.append(len(await request.body()))
        return {"ok": True}

    app.add_middleware(BodySizeLimit, max_bytes=100)
    client = TestClient(app)
    assert client.post("/echo", content=b"x" * 100).status_code == 200
    big = client.post("/echo", content=b"x" * 101)
    assert big.status_code == 413 and big.json()["code"] == "http.too_large"

    def chunks():  # no Content-Length: counted while streaming
        for _ in range(5):
            yield b"x" * 50

    assert client.post("/echo", content=chunks()).status_code == 413
    assert seen == [100]


def test_limit_params_are_clamped(client, monkeypatch):
    from zservice.db.repos import scans as scans_repo

    asked = []
    monkeypatch.setattr(scans_repo, "earning_list", lambda n: asked.append(n) or [])
    for value in (0, -5, 10**9):
        client.get(f"/api/earning_scan/history?limit={value}", headers=_bearer())
    assert asked == [1, 1, 500]
