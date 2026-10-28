"""Sign-in settings: first-run registration and the brute-force windows."""

from pydantic import PositiveInt

from zservice.core.config import ZsSettings, env_field, settings_getter


class AuthSettings(ZsSettings):
    allow_register: bool = env_field(
        "ZS_ALLOW_REGISTER",
        False,
        doc="Open registration while no user exists (first run only). Never in production: "
        "a wiped user collection must not let anyone claim the account.",
    )
    login_rate_limit: PositiveInt = env_field(
        "ZS_LOGIN_RATE_LIMIT", 5, doc="Sign-in attempts per IP + username per window."
    )
    login_ip_rate_limit: PositiveInt = env_field(
        "ZS_LOGIN_IP_RATE_LIMIT",
        20,
        doc="Sign-in attempts per IP per window (needs FORWARDED_ALLOW_IPS behind a proxy).",
    )
    login_rate_window_s: PositiveInt = env_field(
        "ZS_LOGIN_RATE_WINDOW_S", 60, doc="Sign-in rate-limit window (seconds)."
    )


get_settings = settings_getter(AuthSettings)
