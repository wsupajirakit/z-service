"""Offline main module for characterization tests: no Mongo, no TradingView, no network."""

import urllib.request

import pytest


def _no_network(*_args, **_kwargs):
    raise OSError("network disabled in characterization tests")


@pytest.fixture(scope="session")
def main_module():
    import main

    return main


@pytest.fixture
def offline(monkeypatch, main_module):
    """Block every outbound HTTP call the export builders could make (RSS feeds)."""
    monkeypatch.setattr(urllib.request, "urlopen", _no_network)
    return main_module
