from pydantic import BaseModel, Field

from zservice.core.schemas import Bars, Exchange, Symbol


class DataRequest(BaseModel):
    symbol: Symbol
    exchange: Exchange
    interval: str = Field(max_length=8)
    extended_session: bool = False
    rows: Bars = 40
