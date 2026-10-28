"""Where the built frontends are served from."""

from pydantic import field_validator

from zservice.core.config import ZsSettings, env_field, settings_getter


class WebSettings(ZsSettings):
    app_base: str = env_field(
        "APP_BASE", "/app/", doc="Base path of the web UI; must match its build (Dockerfile)."
    )
    frontend_dir: str = env_field(
        "FRONTEND_DIR",
        "static",
        doc="Built frontends: the legacy dashboard at /, the web UI under APP_BASE.",
    )

    @field_validator("app_base")
    @classmethod
    def _slashes(cls, base: str) -> str:
        if not (base.startswith("/") and base.endswith("/")):
            raise ValueError("APP_BASE must start and end with '/', e.g. /app/")
        return base


get_settings = settings_getter(WebSettings)
