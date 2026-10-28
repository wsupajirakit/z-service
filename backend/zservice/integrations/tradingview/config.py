"""TradingView credentials and request pacing.

Auth mode (Settings → tv_login_mode): 1 signs in with username + password, 2 uses the
pasted session token, 3 is anonymous.
"""

from pydantic import NonNegativeFloat, NonNegativeInt, PositiveInt, SecretStr

from zservice.core.config import ZsSettings, env_field, settings_getter


class TradingViewSettings(ZsSettings):
    username: str = env_field("TV_USERNAME", "", doc="Sign-in user (auth mode 1).")
    password: SecretStr = env_field("TV_PASSWORD", SecretStr(""), doc="Sign-in password.")
    auth_token: SecretStr = env_field(
        "TV_AUTH_TOKEN",
        SecretStr(""),
        doc="Session token (auth mode 2; also the fallback when sign-in fails).",
    )
    ws_timeout: PositiveInt = env_field(
        "TV_WS_TIMEOUT",
        15,
        doc="Websocket read timeout (s); tvdatafeed's own 5 s kills fetches TradingView only "
        "stalled while soft-throttling.",
    )
    min_request_interval: NonNegativeFloat = env_field(
        "TV_MIN_REQUEST_INTERVAL",
        1.5,
        doc="Global spacing between requests (s); bursts of ~10 trip TradingView's limit.",
    )
    cooldown_seconds: NonNegativeInt = env_field(
        "TV_COOLDOWN_SECONDS",
        120,
        doc="Pause after repeated empty responses signal a tripped limit (s).",
    )


get_settings = settings_getter(TradingViewSettings)
