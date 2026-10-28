"""Gold analysis configuration: data sources, timeframes and the prompt template."""

from zservice.core.config import ZsSettings, env_field, settings_getter
from zservice.integrations.gemini import DEFAULT_MODEL

# Broker/market sources verified to serve XAUUSD through tvDatafeed.
# label = shown in the UI, exchange = the code passed to TradingView.
GOLD_SOURCES = [
    {"label": "OANDA", "exchange": "OANDA"},
    {"label": "Pepperstone", "exchange": "PEPPERSTONE"},
    {"label": "Capital.com", "exchange": "CAPITALCOM"},
    {"label": "Vantage", "exchange": "VANTAGE"},
    {"label": "IC Markets", "exchange": "ICMARKETS"},
    {"label": "Eightcap", "exchange": "EIGHTCAP"},
    {"label": "Forex.com", "exchange": "FOREXCOM"},
    {"label": "BlackBull", "exchange": "BLACKBULL"},
]
GOLD_SOURCE_EXCHANGES = {s["exchange"] for s in GOLD_SOURCES}
GOLD_TIMEFRAMES = ["15m", "1h", "4h", "1d"]
GOLD_DEFAULT_MODEL = DEFAULT_MODEL

# Cross-market symbols fed to the gold prompt for macro bias (label, symbol, exchange).
# These feed the {{dxy_level}} / {{us10y_yield}} / {{vix_level}} / {{silver_price}} slots.
GOLD_CROSS_MARKET = [
    {"key": "dxy_level", "label": "DXY", "symbol": "DXY", "exchange": "TVC"},
    {"key": "us10y_yield", "label": "US10Y", "symbol": "US10Y", "exchange": "TVC"},
    {"key": "vix_level", "label": "VIX", "symbol": "VIX", "exchange": "TVC"},
    {"key": "silver_price", "label": "Silver", "symbol": "XAGUSD", "exchange": "OANDA"},
]


class GoldSettings(ZsSettings):
    prompt_path: str = env_field(
        "GOLD_PROMPT_PATH", "", doc="Prompt template override (default trade_instruction/gold.md)."
    )


get_settings = settings_getter(GoldSettings)
