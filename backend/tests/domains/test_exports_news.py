"""News in the exports: the formula CSV takes the first 5 headlines per feed, the news CSV
takes all of them (the one difference between the two former copies of the fetcher)."""

import types
import urllib.request

import feedparser
import pytest

from zservice.domains.exports.formula_csv import build_formula_csv_bytes
from zservice.domains.exports.news_csv import build_news_csv_bytes

ENTRIES = 8


class _Resp:
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self):
        return b"<rss/>"


@pytest.fixture
def one_live_feed(monkeypatch):
    def urlopen(req, timeout=3):
        if "cnbc" not in req.full_url:
            raise OSError("feed down")
        return _Resp()

    entries = [
        {"title": f"t{i}", "link": f"https://x/{i}", "published": f"p{i}"} for i in range(ENTRIES)
    ]
    monkeypatch.setattr(urllib.request, "urlopen", urlopen)
    monkeypatch.setattr(feedparser, "parse", lambda content: types.SimpleNamespace(entries=entries))


def test_formula_keeps_five_per_feed(one_live_feed):
    text = build_formula_csv_bytes().decode("utf-8-sig")
    assert text.count("LATEST_FINANCIAL_NEWS,,CNBC (World),") == 5
    assert "ไม่พบข่าวสาร" not in text


def test_news_csv_keeps_all(one_live_feed):
    text = build_news_csv_bytes().decode("utf-8-sig")
    assert text.count("CNBC (World)") == ENTRIES


def test_formula_without_any_news_writes_the_empty_marker(monkeypatch):
    monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: (_ for _ in ()).throw(OSError()))
    assert "ไม่พบข่าวสาร" in build_formula_csv_bytes().decode("utf-8-sig")
