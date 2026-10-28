"""Earnings provider keys; an empty key skips that provider in the fallback chain."""

from pydantic import SecretStr

from zservice.core.config import ZsSettings, env_field, settings_getter


class EarningScanSettings(ZsSettings):
    finnhub_api_key: SecretStr = env_field(
        "FINNHUB_API_KEY", SecretStr(""), doc="Finnhub key (first in the chain)."
    )
    fmp_api_key: SecretStr = env_field(
        "FMP_API_KEY", SecretStr(""), doc="Financial Modeling Prep key."
    )
    alpha_vantage_api_key: SecretStr = env_field(
        "ALPHA_VANTAGE_API_KEY", SecretStr(""), doc="Alpha Vantage key (last in the chain)."
    )


get_settings = settings_getter(EarningScanSettings)
