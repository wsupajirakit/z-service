from pydantic import BaseModel, Field

from zservice.core.schemas import Exchange, ListName, Symbol


class WatchlistAdd(BaseModel):
    symbol: Symbol
    name: str = Field(max_length=200)
    list_name: ListName = "Default"
    # NASDAQ / NYSE / AMEX ... — lets /api/symbols include DB-only names
    exchange: Exchange | None = None
