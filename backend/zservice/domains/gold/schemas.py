from pydantic import BaseModel, Field

from zservice.core.schemas import Exchange
from zservice.integrations.gemini import ModelName

from .config import GOLD_DEFAULT_MODEL


class GoldAnalyzeRequest(BaseModel):
    exchange: Exchange = "OANDA"
    model: ModelName = GOLD_DEFAULT_MODEL
    rows: int = Field(default=60, ge=1, le=1000)  # bars per timeframe fed to the model
    # optional risk-per-trade for position sizing
    risk_percent: float | None = Field(default=None, ge=0, le=100)
