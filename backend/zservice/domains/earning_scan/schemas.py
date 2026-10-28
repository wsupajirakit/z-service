from pydantic import BaseModel, Field

from zservice.core.schemas import Symbol

# Each symbol costs up to three provider calls (Finnhub -> FMP -> Alpha Vantage).
MAX_EARNING_SYMBOLS = 1000


class EarningScanRequest(BaseModel):
    symbols: list[Symbol] = Field(max_length=MAX_EARNING_SYMBOLS)
