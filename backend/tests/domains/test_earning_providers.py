"""FMP sends its key in the `apikey` header; one query-key retry when the header is refused."""

import io
import urllib.error

import pytest

from zservice.domains.earning_scan import providers


@pytest.fixture
def calls(monkeypatch, env):
    seen = []
    env(FMP_API_KEY="k3y")

    def fake(url, timeout=10, headers=None):
        seen.append((url, dict(headers or {})))
        if headers and headers.get("apikey") and seen[0][0].endswith("REFUSE"):
            raise urllib.error.HTTPError(url, 401, "no", {}, io.BytesIO())
        return [{"ok": True}]

    monkeypatch.setattr(providers, "_http_get_json", fake)
    return seen


def test_key_goes_in_the_header(calls):
    assert providers._fmp_get_json("https://fmp.example/a?x=1") == [{"ok": True}]
    assert calls == [("https://fmp.example/a?x=1", {"apikey": "k3y"})]


def test_refused_header_falls_back_to_the_query_once(calls):
    providers._fmp_get_json("https://fmp.example/REFUSE")
    assert [url for url, _ in calls] == [
        "https://fmp.example/REFUSE",
        "https://fmp.example/REFUSE?apikey=k3y",
    ]
