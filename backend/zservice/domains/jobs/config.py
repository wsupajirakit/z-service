"""Auto job settings: autostart after boot, pacing, cross-container takeover."""

from pydantic import NonNegativeFloat, NonNegativeInt, PositiveInt

from zservice.core.config import ZsSettings, env_field, settings_getter


class JobsSettings(ZsSettings):
    autostart: bool = env_field(
        "ZS_AUTOSTART", True, doc="Start the auto job after boot with the server symbol list."
    )
    autostart_delay_s: NonNegativeFloat = env_field(
        "ZS_AUTOSTART_DELAY", 30, doc="Wait before autostart (s): TradingView session warm-up."
    )
    heartbeat_stale_s: PositiveInt = env_field(
        "ZS_JOB_HEARTBEAT_STALE_S",
        180,
        doc="Another container's job heartbeat older than this is dead; autostart takes over.",
    )
    symbol_delay_s: NonNegativeInt = env_field(
        "SYMBOL_DELAY_SECONDS",
        0,
        doc="Extra gap between symbols (s); redundant by default (the TradingView throttle "
        "spaces requests).",
    )
    force_all_tf: bool = env_field(
        "AUTO_FORCE_ALL_TF",
        False,
        doc="Legacy: fetch all four timeframes every round, closed bars or not.",
    )


get_settings = settings_getter(JobsSettings)
