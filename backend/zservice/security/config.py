"""Security settings shared by the session layer and the HTTP middleware."""

from pydantic import NonNegativeInt, PositiveInt, SecretStr, field_validator

from zservice.core.config import CommaList, ZsSettings, env_field, settings_getter


class SecuritySettings(ZsSettings):
    auth_secret: SecretStr = env_field(
        "AUTH_SECRET",
        SecretStr(""),
        doc="Signs session tokens. Required: the app refuses to start below 28 bytes.",
    )
    max_body_bytes: PositiveInt = env_field(
        "ZS_MAX_BODY_BYTES",
        2 * 1024 * 1024,
        doc="Request body cap; the largest real body (a full-universe scan) is ~100 KB.",
    )
    revocation_cache_s: NonNegativeInt = env_field(
        "ZS_REVOCATION_CACHE_S",
        15,
        doc="How stale the session revocation list may be (another container sees a logout "
        "within this time).",
    )
    forwarded_allow_ips: str = env_field(
        "FORWARDED_ALLOW_IPS",
        "",
        doc="Read by uvicorn (proxy addresses it trusts). With '*' the client address is "
        "the rightmost X-Forwarded-For entry (client_ip.py).",
    )
    cors_origins: CommaList = env_field(
        "ZS_CORS_ORIGINS",
        (),
        doc="Local development only: comma-separated origins of a dev server on another "
        "port. '*' is refused. Production is one origin and needs none.",
    )

    @field_validator("cors_origins")
    @classmethod
    def _explicit_origins(cls, origins: tuple[str, ...]) -> tuple[str, ...]:
        # With credentials, Starlette would reflect any Origin back for a wildcard.
        if "*" in origins:
            raise ValueError("ZS_CORS_ORIGINS must list origins explicitly, not '*'")
        return tuple(o.rstrip("/") for o in origins)


get_settings = settings_getter(SecuritySettings)
