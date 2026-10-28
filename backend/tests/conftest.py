"""Shared test setup: run fully offline (no Mongo, no TradingView, no auto job).

* Tests see the process environment only: a developer's .env / .env.local (real Drive,
  Gemini, Telegram keys) is never loaded, so no test depends on, or reaches, a real service.
* MONGO_URI is always blanked, even when the shell exports one: a test must never touch a
  real database (the opt-in `mongo` group uses ZS_TEST_MONGO_URI instead).
"""

import os
import sys

import pytest

BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND)

os.environ["ZS_AUTOSTART"] = "0"
os.environ["MONGO_URI"] = ""
os.environ.setdefault("AUTH_SECRET", "test-only-secret-" + "x" * 32)
for _name in ("TV_USERNAME", "TV_PASSWORD", "TV_AUTH_TOKEN"):
    os.environ.setdefault(_name, "")

from zservice import bootstrap  # noqa: E402 — after the env above
from zservice.core import config as zs_config  # noqa: E402

bootstrap.load_env = lambda: None  # main.py calls it on import

# Opt-in test groups (marker -> env that turns it on): slow or reaching outside the machine.
OPT_IN = {
    "parity": ("ZS_RUN_PARITY", "digest parity with stock-radar, ~90 s"),
    "live": ("ZS_RUN_LIVE", "calls TradingView for real"),
    "mongo": ("ZS_TEST_MONGO_URI", "needs a local test MongoDB, never production"),
}


def pytest_configure(config):
    for marker, (env, why) in OPT_IN.items():
        config.addinivalue_line("markers", f"{marker}: {why} (set {env} to run)")


@pytest.fixture(autouse=True)
def _fresh_settings():
    """Every test reads the environment afresh (monkeypatch restores it after each test)."""
    zs_config.reset()
    yield
    zs_config.reset()


@pytest.fixture
def env(monkeypatch):
    """Set variables for one test (None unsets one); the cached settings re-read them."""

    def apply(**values: str | None) -> None:
        for name, value in values.items():
            if value is None:
                monkeypatch.delenv(name, raising=False)
            else:
                monkeypatch.setenv(name, value)
        zs_config.reset()

    return apply


def pytest_collection_modifyitems(config, items):
    for item in items:
        for marker, (env, why) in OPT_IN.items():
            if marker in item.keywords and not os.environ.get(env):
                item.add_marker(pytest.mark.skip(reason=f"{why}: set {env}"))
