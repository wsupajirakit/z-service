"""Telegram, Gemini and the Drive root-folder guard — offline (urlopen / Drive client faked)."""

import io
import json
import types
import urllib.error
import urllib.request

import pytest
from fastapi import HTTPException

from zservice.integrations import drive, gemini, telegram


class _Resp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_telegram_skips_without_config_and_sends_to_every_chat(monkeypatch, env, capsys):
    sent = []
    monkeypatch.setattr(urllib.request, "urlopen", lambda req, timeout: sent.append(req) or _Resp())
    env(TELEGRAM_BOT_TOKEN=None)
    telegram.send_telegram_message("hi")
    assert sent == [] and "skipping" in capsys.readouterr().out
    env(TELEGRAM_BOT_TOKEN="t", TELEGRAM_ALLOWED_CHAT_IDS="1, 2")
    telegram.send_telegram_message("hi")
    assert len(sent) == 2 and b"chat_id=2" in sent[1].data


def test_gemini_retries_overload_then_returns_text(monkeypatch):
    calls = []
    ok = {"candidates": [{"content": {"parts": [{"text": " answer "}]}}]}

    def urlopen(req, timeout):
        calls.append(1)
        if len(calls) == 1:
            raise urllib.error.HTTPError(req.full_url, 503, "busy", {}, io.BytesIO(b"busy"))
        return _Resp(json.dumps(ok).encode())

    monkeypatch.setattr(urllib.request, "urlopen", urlopen)
    monkeypatch.setattr(gemini.time, "sleep", lambda s: None)
    assert gemini.call_gemini("m", "p") == "answer" and len(calls) == 2


def test_gemini_bad_key_is_502_without_retry(monkeypatch):
    def urlopen(req, timeout):
        raise urllib.error.HTTPError(req.full_url, 400, "bad", {}, io.BytesIO(b"bad key"))

    monkeypatch.setattr(urllib.request, "urlopen", urlopen)
    with pytest.raises(HTTPException) as e:
        gemini.call_gemini("m", "p")
    assert e.value.status_code == 502 and "HTTP 400" in e.value.detail


def _svc(parents: dict):
    def get(fileId, fields):
        if fileId not in parents:
            return types.SimpleNamespace(execute=lambda: (_ for _ in ()).throw(OSError()))
        return types.SimpleNamespace(execute=lambda: {"id": fileId, "parents": parents[fileId]})

    return types.SimpleNamespace(files=lambda: types.SimpleNamespace(get=get))


def test_drive_guard_allows_only_the_root_tree(env):
    # Real Drive ids are 28-44 URL-safe characters; short fakes would fail the shape check.
    names = ("ROOT", "child", "grand", "outside", "other")
    root, child, grand, outside, other = (f"{n}_0123456789abcdef" for n in names)
    env(GDRIVE_ROOT_FOLDER_ID=root)
    svc = _svc({child: [root], grand: [child], outside: [other], other: []})
    drive._assert_under_root(svc, grand)  # no raise
    for target in (outside, "unknown_0123456789abcdef"):
        with pytest.raises(HTTPException) as e:
            drive._assert_under_root(svc, target)
        assert e.value.status_code == 403


def test_gemini_key_goes_in_the_header_not_the_url(monkeypatch, env):
    seen = {}
    ok = {"candidates": [{"content": {"parts": [{"text": "x"}]}}]}

    def urlopen(req, timeout):
        seen["url"], seen["key"] = req.full_url, req.get_header("X-goog-api-key")
        return _Resp(json.dumps(ok).encode())

    monkeypatch.setattr(urllib.request, "urlopen", urlopen)
    env(GEMINI_API_KEY="secret-key")
    gemini.call_gemini("m", "p")
    assert seen["key"] == "secret-key" and "secret-key" not in seen["url"]


def test_finnhub_key_goes_in_the_header(monkeypatch, env):
    from zservice.domains.earning_scan import providers

    seen = []

    def urlopen(req, timeout):
        seen.append((req.full_url, req.get_header("X-finnhub-token")))
        return _Resp(b"[]")

    monkeypatch.setattr(urllib.request, "urlopen", urlopen)
    env(FINNHUB_API_KEY="fh-key")
    providers._fetch_earnings_finnhub("AAA")
    assert seen and all(key == "fh-key" and "fh-key" not in url for url, key in seen)
