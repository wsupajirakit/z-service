"""Step 4: put the still-forming last bar back after the indicators, with indicators blank
(they must never be computed on an unfinished bar) and its session fields filled."""

import pandas as pd

from zservice.market.sessions import check_in_rth, get_bar_session_type, get_weekly_sess_ratio

from .sessions_tag import RTH_MINUTES

INDICATOR_COLUMNS = [
    "EMA_20",
    "EMA_50",
    "EMA_100",
    "EMA_200",
    "RSI",
    "OBV",
    "CMF",
    "VWAP",
    "FVG",
    "RVOL",
    "RVOL_Deviation",
    "IPI",
    "IPI_Status",
    "MACD",
    "MACD_Signal",
    "MACD_Hist",
    "ATR",
    "BB_Middle",
    "BB_Upper",
    "BB_Lower",
    "Fib_High",
    "Fib_Low",
    "Fib_236",
    "Fib_382",
    "Fib_500",
    "Fib_618",
    "Fib_786",
    "atr14",
    "ema_stack",
]


def append_open_bar(df: pd.DataFrame, open_bar_row, interval: str, us_stock: bool, sched):
    if open_bar_row is None:
        return df
    open_bar_index = open_bar_row.index[0]
    for col in INDICATOR_COLUMNS:
        open_bar_row[col] = None
    open_bar_row["is_closed_bar"] = False
    open_bar_row["ipi_valid"] = False
    open_bar_row["dollar_volume"] = open_bar_row["close"] * open_bar_row["volume"]
    open_bar_row["split_adjusted"] = True
    open_bar_row["last_split"] = "N/A"
    open_bar_row["gap_flag"] = 0.0

    if "sess_ratio" in df.columns:
        open_bar_row["sess_ratio"] = _open_bar_ratio(open_bar_index, interval, us_stock, sched)
    if "in_rth" in df.columns:
        open_bar_row["in_rth"] = check_in_rth(open_bar_index, sched, us_stock)
    if "session" in df.columns:
        open_bar_row["session"] = get_bar_session_type(open_bar_index, sched, us_stock, interval)
    return pd.concat([df, open_bar_row])


def _open_bar_ratio(open_bar_index, interval: str, us_stock: bool, sched) -> float:
    if interval == "1d" and us_stock and sched is not None:
        t_date = open_bar_index.floor("D")
        if t_date in sched.index:
            day = sched.loc[t_date]
            mins = (day["market_close"] - day["market_open"]).total_seconds() / 60.0
            return mins / RTH_MINUTES
        return 1.0
    if interval == "1w" and us_stock and sched is not None:
        return get_weekly_sess_ratio(open_bar_index, sched)
    return 1.0
