"""TradingView login mode setting (moved from main.py via domains/settings).

1 = TV_USERNAME/TV_PASSWORD login · 2 = TV_AUTH_TOKEN only · 3 = classic anonymous.
Stored in the settings collection; the settings domain re-exports these helpers.
"""

from zservice.db.repos import settings as settings_repo

DEFAULT_TV_MODE = 3  # classic (anonymous)
TV_MODES = (1, 2, 3)


def get_tv_mode_setting() -> int:
    try:
        val = settings_repo.settings_get("tv_login_mode")
        if val is not None:
            return int(val)
    except Exception:  # noqa: S110 — a broken or missing DB value means the default
        pass
    return DEFAULT_TV_MODE


def set_tv_mode_setting(mode: int) -> None:
    settings_repo.settings_set("tv_login_mode", str(mode))
