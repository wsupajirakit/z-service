"""Indicator look-back periods (bars). The CSV export prints cmf_period in its header."""

from pydantic import PositiveInt

from zservice.core.config import ZsSettings, env_field, settings_getter


class IndicatorSettings(ZsSettings):
    rsi_period: PositiveInt = env_field("RSI_PERIOD", 50, doc="RSI period (Wilder smoothing).")
    cmf_period: PositiveInt = env_field("CMF_PERIOD", 50, doc="Chaikin money flow period.")
    rvol_period: PositiveInt = env_field("RVOL_PERIOD", 50, doc="Relative volume look-back.")
    obv_slope_window: PositiveInt = env_field("OBV_SLOPE_WINDOW", 50, doc="OBV slope look-back.")


get_settings = settings_getter(IndicatorSettings)
