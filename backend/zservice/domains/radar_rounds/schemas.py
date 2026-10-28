from pydantic import BaseModel, Field

from zservice.core.schemas import NAME_MAX, Timeframes


class RoundRequest(BaseModel):
    # Independent timeframe choice: each TF is fetched from TradingView on its
    # own schedule, so a round may legitimately cover only the fresh ones.
    # None/empty = every timeframe that has data.
    timeframes: Timeframes | None = None
    list_name: str | None = Field(default=None, max_length=NAME_MAX)
    # Save as a new round even when the data has not changed (a clashing stamp gets
    # _v2, _v3, ...).
    new_record: bool = False
