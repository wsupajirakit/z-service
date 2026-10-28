"""Step 3: indicators on the closed bars, in the original order (some read earlier ones).

Each indicator keeps its own try/except fallback exactly as before: a failing indicator
becomes None/neutral instead of failing the whole fetch.
"""

import logging

import numpy as np
import pandas as pd

from . import config as md_config

log = logging.getLogger("zs.market_data")

INTRADAY = ["15m", "30m", "1h", "4h"]
IPI_ACCUMULATION_ABOVE = 50
IPI_DISTRIBUTION_BELOW = -20
IPI_MIN_RVOL = 0.3


def add_indicators(df: pd.DataFrame, interval: str) -> None:
    """All indicator columns, in place."""
    for step in (_emas, _rsi, _obv, _cmf, _vwap):
        step(df)
    _rvol(df, interval)
    for step in (_ipi, _fvg, _macd, _atr, _bollinger, _fibonacci, _extras, _ema_stack, _gap):
        step(df)


def _emas(df):
    for span in (20, 50, 100, 200):
        df[f"EMA_{span}"] = df["close"].ewm(span=span, adjust=False).mean()


def _rsi(df):
    """RSI (50 by default) with Wilder's smoothing."""
    rsi_period = md_config.get_settings().rsi_period
    delta = df["close"].diff()
    gain = delta.clip(lower=0)
    loss = -1 * delta.clip(upper=0)
    avg_gain = gain.ewm(com=rsi_period - 1, adjust=False).mean()
    avg_loss = loss.ewm(com=rsi_period - 1, adjust=False).mean()
    rs = avg_gain / avg_loss
    df["RSI"] = 100 - (100 / (1 + rs))


def _obv(df):
    try:
        obv = np.where(
            df["close"] > df["close"].shift(1),
            df["volume"],
            np.where(df["close"] < df["close"].shift(1), -df["volume"], 0),
        ).cumsum()
        df["OBV"] = obv
    except Exception:
        df["OBV"] = None


def _cmf(df):
    """CMF (50-period by default) with safe divisions."""
    try:
        cmf_period = md_config.get_settings().cmf_period
        hl = df["high"] - df["low"]
        mfm = np.where(
            hl == 0,
            0.0,
            ((df["close"] - df["low"]) - (df["high"] - df["close"])) / np.where(hl == 0, 1.0, hl),
        )
        mfm = np.clip(mfm, -1.0, 1.0)
        mfv = mfm * df["volume"]
        vol_sum = df["volume"].rolling(window=cmf_period).sum()
        cmf = np.where(
            vol_sum == 0,
            0.0,
            mfv.rolling(window=cmf_period).sum() / np.where(vol_sum == 0, 1.0, vol_sum),
        )
        df["CMF"] = np.clip(cmf, -1.0, 1.0)
    except Exception:
        df["CMF"] = None


def _vwap(df):
    """VWAP anchored per session day (cumulative fallback without a DatetimeIndex)."""
    try:
        typical_price = (df["high"] + df["low"] + df["close"]) / 3
        if isinstance(df.index, pd.DatetimeIndex):
            date_groups = df.index.date
            df["VWAP"] = (typical_price * df["volume"]).groupby(date_groups).cumsum() / df[
                "volume"
            ].groupby(date_groups).cumsum()
        else:
            df["VWAP"] = (typical_price * df["volume"]).cumsum() / df["volume"].cumsum()
    except Exception:
        df["VWAP"] = None


def _rvol(df, interval):
    """Relative volume (time-of-day slots intraday) and its deviation in %."""
    try:
        rvol_period = md_config.get_settings().rvol_period
        if interval in INTRADAY:
            df["slot"] = df.index.strftime("%H:%M")
            rvol_slot = df["volume"] / df.groupby("slot")["volume"].transform(
                lambda x: x.rolling(20, min_periods=5).mean().shift(1)
            )
            standard_rvol = df["volume"] / df["volume"].rolling(
                window=rvol_period, min_periods=1
            ).mean().shift(1)
            df["RVOL"] = rvol_slot.fillna(standard_rvol)
            df["RVOL_slot"] = df["RVOL"]
        else:
            sma_volume = df["volume"].rolling(window=rvol_period).mean()
            ratios = df["sess_ratio"] if "sess_ratio" in df.columns else 1.0
            df["RVOL"] = df["volume"] / (sma_volume * ratios)
            df["RVOL_slot"] = df["RVOL"]
        df["RVOL_Deviation"] = (df["RVOL"] - 1) * 100
    except Exception:
        df["RVOL"] = None
        df["RVOL_Deviation"] = None
        df["RVOL_slot"] = None


def _ipi(df):
    """Institutional Power Index: CMF + RVOL deviation + normalised OBV slope; only valid
    on closed RTH bars with enough volume, otherwise cleared with the reason as status."""
    try:
        obv_slope = df["OBV"].diff()
        obv_slope_window = md_config.get_settings().obv_slope_window
        norm_obv_slope = obv_slope / obv_slope.rolling(window=obv_slope_window).std()
        df["IPI"] = (df["CMF"] * 100) + (df["RVOL_Deviation"] * 0.5) + (norm_obv_slope * 50)

        rvol_check = (
            df["RVOL_slot"] if df["RVOL_slot"] is not None else pd.Series(True, index=df.index)
        )
        df["ipi_valid"] = df["is_closed_bar"] & df["in_rth"] & (rvol_check > IPI_MIN_RVOL)

        ipi, valid = df["IPI"], df["ipi_valid"] == True  # noqa: E712 — element-wise, as before
        conditions = [
            valid & (ipi.notna()) & (ipi > IPI_ACCUMULATION_ABOVE),
            valid
            & (ipi.notna())
            & (ipi >= IPI_DISTRIBUTION_BELOW)
            & (ipi <= IPI_ACCUMULATION_ABOVE),
            valid & (ipi.notna()) & (ipi < IPI_DISTRIBUTION_BELOW),
        ]
        choices = ["Institutional Accumulation", "Neutral", "Institutional Distribution"]
        default_status = np.where(
            df["IPI"].isna(), None, np.where(~df["in_rth"], "N/A (ext)", "N/A (low vol)")
        )
        default_status = np.where(~df["is_closed_bar"], "N/A (open)", default_status)
        df["IPI_Status"] = np.select(conditions, choices, default=default_status)
        df.loc[~df["ipi_valid"], "IPI"] = None
    except Exception as ipi_ex:
        print(f"Error calculating IPI: {ipi_ex}")
        df["IPI"] = None
        df["IPI_Status"] = None
        df["ipi_valid"] = False


def _fvg(df):
    """Fair value gap on the middle bar of each 3-bar window (+ bullish, - bearish)."""
    fvg = [None] * len(df)
    lows = df["low"].values
    highs = df["high"].values
    for i in range(1, len(df) - 1):
        if lows[i + 1] > highs[i - 1]:
            fvg[i] = float(lows[i + 1] - highs[i - 1])
        elif highs[i + 1] < lows[i - 1]:
            fvg[i] = float(highs[i + 1] - lows[i - 1])
    df["FVG"] = fvg


def _macd(df):
    try:
        ema_12 = df["close"].ewm(span=12, adjust=False).mean()
        ema_26 = df["close"].ewm(span=26, adjust=False).mean()
        df["MACD"] = ema_12 - ema_26
        df["MACD_Signal"] = df["MACD"].ewm(span=9, adjust=False).mean()
        df["MACD_Hist"] = df["MACD"] - df["MACD_Signal"]
    except Exception:
        df["MACD"] = None
        df["MACD_Signal"] = None
        df["MACD_Hist"] = None


def _atr(df):
    try:
        high_low = df["high"] - df["low"]
        high_cp = (df["high"] - df["close"].shift(1)).abs()
        low_cp = (df["low"] - df["close"].shift(1)).abs()
        tr = pd.concat([high_low, high_cp, low_cp], axis=1).max(axis=1)
        df["ATR"] = tr.ewm(alpha=1 / 14, adjust=False).mean()
    except Exception:
        df["ATR"] = None


def _bollinger(df):
    try:
        df["BB_Middle"] = df["close"].rolling(window=20).mean()
        bb_std = df["close"].rolling(window=20).std()
        df["BB_Upper"] = df["BB_Middle"] + 2 * bb_std
        df["BB_Lower"] = df["BB_Middle"] - 2 * bb_std
    except Exception:
        df["BB_Middle"] = None
        df["BB_Upper"] = None
        df["BB_Lower"] = None


FIB_LEVELS = (("236", 0.236), ("382", 0.382), ("500", 0.500), ("618", 0.618), ("786", 0.786))


def _fibonacci(df):
    """Retracement levels over a rolling 100-bar range (min 20 bars)."""
    try:
        df["Fib_High"] = df["high"].rolling(window=100, min_periods=20).max()
        df["Fib_Low"] = df["low"].rolling(window=100, min_periods=20).min()
        fib_diff = df["Fib_High"] - df["Fib_Low"]
        for name, ratio in FIB_LEVELS:
            df[f"Fib_{name}"] = df["Fib_High"] - ratio * fib_diff
    except Exception:
        df["Fib_High"] = None
        df["Fib_Low"] = None
        for name, _ in FIB_LEVELS:
            df[f"Fib_{name}"] = None


def _extras(df):
    df["atr14"] = df["ATR"]
    df["dollar_volume"] = df["close"] * df["volume"]
    df["split_adjusted"] = True
    df["last_split"] = "N/A"


def _ema_stack(df):
    try:
        ema20, ema50, ema100, ema200 = df["EMA_20"], df["EMA_50"], df["EMA_100"], df["EMA_200"]
        conditions_ema = [
            (ema20 > ema50) & (ema50 > ema100) & (ema100 > ema200),
            (ema20 < ema50) & (ema50 < ema100) & (ema100 < ema200),
        ]
        df["ema_stack"] = np.select(conditions_ema, ["bull", "bear"], default="mixed")
    except Exception:
        df["ema_stack"] = "mixed"


def _gap(df):
    """Opening gap % on the first bar of each day."""
    try:
        dates = pd.Series(df.index.date, index=df.index)
        first_bar_mask = dates != dates.shift(1)
        prev_close = df["close"].shift(1)
        gap_pct = ((df["open"] - prev_close) / prev_close * 100.0).fillna(0.0)
        df["gap_flag"] = np.where(first_bar_mask, gap_pct, 0.0)
    except Exception:
        df["gap_flag"] = 0.0
