"""Typed per-domain configuration (zservice/core/config.py)."""

import subprocess
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

from zservice.core import config, config_docs

BACKEND = Path(__file__).resolve().parents[2]
REFERENCE = BACKEND.parent / "docs" / "config-reference.md"


def test_reference_doc_is_current():
    expected = config_docs.render(config_docs.discover())
    assert REFERENCE.read_text(encoding="utf-8") == expected, (
        "docs/config-reference.md is stale: run backend/venv/bin/python tools/config_reference.py"
    )


def test_the_app_validates_every_settings_class_at_startup():
    # A fresh process: what create_app() registers must be every class in the code base,
    # or a malformed value of the missing one would only fail on first use.
    script = (
        "from zservice import bootstrap; bootstrap.load_env = lambda: None; import main; "
        "from zservice.core import config; "
        "print(sorted(c.__name__ for c in config.registered()))"
    )
    env = {"MONGO_URI": "", "ZS_AUTOSTART": "0", "AUTH_SECRET": "x" * 40, "PATH": ""}
    out = subprocess.run(  # noqa: S603 — fixed interpreter and script
        [sys.executable, "-c", script], cwd=BACKEND, env=env, capture_output=True, text=True
    )
    assert out.returncode == 0, out.stderr
    at_startup = out.stdout.strip().splitlines()[-1]
    assert at_startup == str(sorted(c.__name__ for c in config_docs.discover()))


@pytest.mark.parametrize(
    ("name", "value"),
    [("ZS_MAX_BODY_BYTES", "lots"), ("ZS_LOGIN_RATE_LIMIT", "0"), ("APP_BASE", "app"),
     ("ZS_AUTOSTART", "maybe"), ("ZS_CORS_ORIGINS", "*")],
)  # fmt: skip
def test_a_malformed_value_stops_the_boot_naming_the_variable(env, name, value):
    config_docs.discover()
    env(**{name: value})
    with pytest.raises(ValidationError, match=name):
        config.validate_all()


def test_blank_means_default_and_secrets_never_print(env):
    from zservice.domains.auth import config as auth_config
    from zservice.security import config as security_config

    env(ZS_LOGIN_RATE_LIMIT="", AUTH_SECRET="s3cret-" * 6)
    assert auth_config.get_settings().login_rate_limit == 5
    shown = repr(security_config.get_settings())
    assert "s3cret" not in shown and "**********" in shown


def test_comma_lists_and_legacy_names(env):
    from zservice.integrations import drive, telegram

    env(TELEGRAM_ALLOWED_CHAT_IDS=" 1, ,2 ", GDRIVE_ROOT_FOLDER_ID=None)
    env(google_drive_folder_id="legacy_root_0123456789")
    assert telegram.get_settings().allowed_chat_ids == ("1", "2")
    assert drive.root_folder_id() == "legacy_root_0123456789"
    env(GDRIVE_ROOT_FOLDER_ID="new_root_0123456789")
    assert drive.root_folder_id() == "new_root_0123456789"
