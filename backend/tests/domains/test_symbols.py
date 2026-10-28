"""Server symbol list: build file + DB rows with an exchange; missing-exchange report."""

import json

from zservice.domains.symbols import service


def test_union_build_and_db(monkeypatch, env, tmp_path):
    build = [
        {"symbol": "qqq", "name": "Invesco QQQ", "exchange": "NASDAQ"},
        {"symbol": "NOEX", "name": "no exchange"},
    ]
    path = tmp_path / "symbols.json"
    path.write_text(json.dumps(build), encoding="utf-8")
    env(SYMBOLS_FILE=str(path))
    rows = [
        {"symbol": "QQQ", "name": "dup", "exchange": "NYSE"},  # build wins
        {"symbol": "abc", "name": "", "exchange": " nyse "},
        {"symbol": "ZZZ", "name": "z"},  # no exchange -> missing
        {"symbol": "ZZZ", "name": "z"},
    ]
    monkeypatch.setattr(service.watchlist_repo, "watchlist_all", lambda: rows)
    syms, missing = service.server_symbols()
    assert syms == [
        {"symbol": "ABC", "name": "ABC", "exchange": "NYSE"},
        {"symbol": "QQQ", "name": "Invesco QQQ", "exchange": "NASDAQ"},
    ]
    assert missing == ["ZZZ"]


def test_db_down_still_serves_build_list(monkeypatch, env, tmp_path):
    path = tmp_path / "symbols.json"
    path.write_text(json.dumps([{"symbol": "A", "exchange": "NYSE"}]), encoding="utf-8")
    env(SYMBOLS_FILE=str(path))

    def down():
        raise RuntimeError("db down")

    monkeypatch.setattr(service.watchlist_repo, "watchlist_all", down)
    assert service.server_symbols() == ([{"symbol": "A", "name": "A", "exchange": "NYSE"}], [])


def test_version_falls_back_to_dev(env, tmp_path):
    env(VERSION_FILE=str(tmp_path / "missing.json"))
    assert service.version_info()["version"] == "dev"


def test_version_takes_the_run_time_commit_when_the_build_had_none(env, tmp_path):
    meta = tmp_path / "VERSION.json"
    meta.write_text('{"version": "2026.10.27.1", "commit": "unknown", "build_time": null}')
    env(VERSION_FILE=str(meta), SOURCE_COMMIT="4be7dee0123456789abcdef")
    assert service.version_info()["commit"] == "4be7dee01234"
    meta.write_text('{"version": "2026.10.27.1", "commit": "abc123", "build_time": null}')
    assert service.version_info()["commit"] == "abc123"  # the build's own record wins
