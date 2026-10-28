"""Machine-key settings (plan B3): the key registry, its rate limit and audit ring."""

from pydantic import PositiveInt, SecretStr

from zservice.core.config import ZsSettings, env_field, settings_getter


class MachineSettings(ZsSettings):
    api_keys: SecretStr = env_field(
        "ZS_API_KEYS",
        SecretStr(""),
        doc="Scoped machine keys: JSON list of {id, scopes, sha256, expires} (keys.py).",
    )
    pull_key: SecretStr = env_field(
        "PULL_KEY",
        SecretStr(""),
        doc="Legacy single key of the old scripts, limited to LEGACY_SCOPES; unset to retire.",
    )
    rate_limit: PositiveInt = env_field(
        "ZS_MACHINE_RATE_LIMIT", 300, doc="Requests per key per window."
    )
    rate_window_s: PositiveInt = env_field(
        "ZS_MACHINE_RATE_WINDOW_S", 60, doc="Machine rate-limit window (seconds)."
    )
    audit_ring_size: PositiveInt = env_field(
        "ZS_AUDIT_RING_SIZE", 2000, doc="Machine access decisions kept in memory."
    )


get_settings = settings_getter(MachineSettings)
