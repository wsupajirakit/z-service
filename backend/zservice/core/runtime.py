"""Process-wide runtime settings: where the app may write, and whether /docs is served."""

from zservice.core.config import ZsSettings, env_field, settings_getter


class RuntimeSettings(ZsSettings):
    state_dir: str = env_field(
        "ZS_STATE_DIR",
        "",
        doc="Writable directory for automate.log and the TradingView token cache. The image "
        "sets an app-owned one (the code is read-only for the app user).",
    )
    docs: bool = env_field(
        "ZS_DOCS", True, doc="Serve /docs and /openapi.json (behind the session gate)."
    )


get_settings = settings_getter(RuntimeSettings)
