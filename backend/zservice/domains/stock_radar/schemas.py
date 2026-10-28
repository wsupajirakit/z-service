from typing import Annotated

from pydantic import BaseModel, Field

from zservice.core.schemas import SymbolList, Timeframes
from zservice.integrations.gemini import DEFAULT_MODEL, ModelName

# The formulas are pasted into the Gemini prompt, so they bound its size (and cost).
MAX_FORMULAS = 50
FORMULA_MAX = 4000


class StockRadarRequest(BaseModel):
    symbols: SymbolList
    formulas: list[Annotated[str, Field(max_length=FORMULA_MAX)]] = Field(max_length=MAX_FORMULAS)
    timeframes: Timeframes
    extended_session: bool = False
    analysis_mode: str = Field(default="ai", max_length=16)  # "ai" or "logic"
    model: ModelName = DEFAULT_MODEL
