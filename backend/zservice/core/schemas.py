"""Request models and bounded types shared by several domains (field names are part of the
public API).

Every client-supplied size is bounded here or in the domain schema: list lengths, string
lengths and bar counts. FastAPI answers 422 for anything outside the bounds, before a
route can spend TradingView, Gemini or Mongo work on it.
"""

from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field

SYMBOL_MAX = 32  # e.g. BRK.B, BTCUSDT, 2330, XAUUSD
EXCHANGE_MAX = 32  # e.g. NYSE ARCA, CAPITALCOM
NAME_MAX = 64  # watchlist / portfolio names
MAX_SYMBOLS = 5000  # the server universe is ~900 today
MAX_BARS = 5000  # TradingView serves at most 5,000 bars per request

Symbol = Annotated[str, Field(min_length=1, max_length=SYMBOL_MAX)]
Exchange = Annotated[str, Field(max_length=EXCHANGE_MAX)]
ListName = Annotated[str, Field(min_length=1, max_length=NAME_MAX)]
Timeframes = Annotated[list[Annotated[str, Field(max_length=8)]], Field(max_length=8)]
Bars = Annotated[int, Field(ge=1, le=MAX_BARS)]


class SymbolRef(BaseModel):
    """One {"symbol", "exchange"} entry. Extra keys (e.g. a display name) are kept, but the
    two the server uses must be plain bounded strings — a dict such as {"$ne": null} can
    never reach a Mongo filter."""

    model_config = ConfigDict(extra="allow")

    symbol: Symbol
    exchange: Exchange | None = None


def _as_dicts(refs: list[SymbolRef]) -> list[dict]:
    return [ref.model_dump() for ref in refs]


# Validated as SymbolRef, handed to the routes as plain dicts (the job runner and the scans
# read them with .get()).
SymbolList = Annotated[list[SymbolRef], Field(max_length=MAX_SYMBOLS), AfterValidator(_as_dicts)]


class RenameRequest(BaseModel):
    new_name: ListName


def clamp(value: int, low: int, high: int) -> int:
    """Clamp a `limit`-style query parameter instead of rejecting it (old callers keep
    working; pymongo would read 0 or a negative value as "no limit")."""
    return max(low, min(int(value), high))
