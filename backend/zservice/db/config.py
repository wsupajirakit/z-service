"""MongoDB connection settings."""

from pydantic import SecretStr

from zservice.core.config import ZsSettings, env_field, settings_getter


class MongoSettings(ZsSettings):
    uri: SecretStr | None = env_field(
        "MONGO_URI", None, doc="Connection string (mongodb+srv://…); unset = every DB call fails."
    )
    db: str = env_field("MONGO_DB", "zservice", doc="Database name.")


get_settings = settings_getter(MongoSettings)
