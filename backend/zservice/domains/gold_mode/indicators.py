"""Gold mode indicator math (RSI, CMF, ATR) — moved unchanged from backend/gold.py."""

import pandas as pd


# --------------------------------------------------------------------------
# indicators (self-contained; CFD volume = tick volume, flagged in metadata)
# --------------------------------------------------------------------------
def _rsi(close: pd.Series, n: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    rs = gain / loss.replace(0, pd.NA)
    return (100 - 100 / (1 + rs)).fillna(50)


def _cmf(df: pd.DataFrame, n: int) -> pd.Series:
    rng = (df["high"] - df["low"]).replace(0, pd.NA)
    mfm = ((df["close"] - df["low"]) - (df["high"] - df["close"])) / rng
    mfv = (mfm * df["volume"]).fillna(0)
    vol = df["volume"].rolling(n).sum().replace(0, pd.NA)
    return (mfv.rolling(n).sum() / vol).fillna(0)


def _atr(df: pd.DataFrame, n: int = 14) -> pd.Series:
    prev_close = df["close"].shift()
    tr = pd.concat(
        [
            df["high"] - df["low"],
            (df["high"] - prev_close).abs(),
            (df["low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.ewm(alpha=1 / n, adjust=False).mean()


def _enrich(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for n in (20, 50, 100, 200):
        out[f"ema{n}"] = out["close"].ewm(span=n, adjust=False).mean()
    out["rsi"] = _rsi(out["close"])
    direction = out["close"].diff().fillna(0)
    out["obv"] = (
        out["volume"] * direction.apply(lambda x: 1 if x > 0 else (-1 if x < 0 else 0))
    ).cumsum()
    out["cmf50"] = _cmf(out, 50)
    out["cmf20"] = _cmf(out, 20)
    out["atr14"] = _atr(out)
    tpv = ((out["high"] + out["low"] + out["close"]) / 3) * out["volume"]
    vol20 = out["volume"].rolling(20).sum().replace(0, pd.NA)
    out["vwap20"] = (tpv.rolling(20).sum() / vol20).fillna(out["close"])
    out["rvol20"] = (out["volume"] / out["volume"].rolling(20).mean().replace(0, pd.NA)).fillna(1)
    return out
