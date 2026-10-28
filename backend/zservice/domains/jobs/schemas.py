from pydantic import BaseModel

from zservice.core.schemas import Bars, SymbolList, Timeframes


class AutomateRequest(BaseModel):
    timeframes: Timeframes
    symbols: SymbolList  # [{"symbol": "BTCUSDT", "exchange": "BINANCE"}, ...]
    extended_session: bool | None = None  # None = use EXTENDED_DEFAULT per timeframe
    rows: Bars = 80


class AutoRequest(BaseModel):
    symbols: SymbolList
    rows: Bars = 80
    # csv mode: False = default (only timeframes whose bar just closed) · True = legacy
    # (all 4 timeframes every round)
    force_all_tf: bool = False
