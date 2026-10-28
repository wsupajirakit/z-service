"""Who may send events and how they are checked."""

import base64
import binascii
import json

from pydantic import BaseModel, Field, SecretStr, field_validator

from zservice.core.config import ZsSettings, env_field, settings_getter

MIN_SECRET_BYTES = 16


def decode_secret(secret: str) -> bytes:
    """The raw HMAC key of a whsec_ secret (empty when it is not valid base64)."""
    try:
        return base64.b64decode(secret.removeprefix("whsec_"), validate=True)
    except (binascii.Error, ValueError):
        return b""


class Sender(BaseModel):
    name: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]{0,39}$")
    secret: SecretStr | None = None  # whsec_...: checks v1 (HMAC) signatures
    public_key: str | None = None  # whpk_...: checks v1a (Ed25519) signatures

    @field_validator("secret")
    @classmethod
    def _strong_secret(cls, value: SecretStr | None) -> SecretStr | None:
        # A short HMAC key makes signatures guessable: refuse it at start-up.
        if value is not None and len(decode_secret(value.get_secret_value())) < MIN_SECRET_BYTES:
            raise ValueError(f"the whsec_ secret must decode to at least {MIN_SECRET_BYTES} bytes")
        return value


class InboundEventSettings(ZsSettings):
    senders: list[Sender] = env_field(
        "ZS_EVENT_SENDERS",
        [],
        doc='Allowed senders, JSON: [{"name": "engine", "secret": "whsec_...", '
        '"public_key": "whpk_..."}] (a secret, a public key or both).',
    )
    tolerance_seconds: int = env_field(
        "ZS_EVENT_TOLERANCE_SECONDS", 300, doc="Largest clock difference accepted.", ge=30
    )
    max_bytes: int = env_field("ZS_EVENT_MAX_BYTES", 262144, doc="Largest event body.", gt=0)
    keep_days: int = env_field("ZS_EVENT_KEEP_DAYS", 30, doc="Days events are kept.", ge=1)

    @field_validator("senders", mode="before")
    @classmethod
    def _parse(cls, value: object) -> object:
        return json.loads(value) if isinstance(value, str) else value


get_settings = settings_getter(InboundEventSettings)
