from pydantic import BaseModel, Field

from zservice.core.schemas import ListName, Symbol

_MAGNITUDE = 1_000_000_000


class PortfolioAdd(BaseModel):
    symbol: Symbol
    quantity: int = Field(ge=-_MAGNITUDE, le=_MAGNITUDE)
    buy_price: float = Field(ge=0, le=_MAGNITUDE)
    action: str = Field(default="buy", max_length=8)
    port_name: ListName = "Default"
