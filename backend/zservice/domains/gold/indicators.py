"""Per-timeframe indicator snapshot strings for the gold prompt, from each latest bar.

Uses only indicators the backend computes (EMA/RSI/CMF/IPI/FVG/volume/MACD/ATR/BB).
"""

from .config import GOLD_TIMEFRAMES
from .prompt import fmt_num as g

SNAPSHOTS = ("ema", "momentum", "volume", "volatility")


def _gold_indicator_snapshots(tf_data: dict) -> dict:
    """{snapshot: one line per timeframe}; a timeframe without bars is 'N/A' everywhere."""
    lines = {name: [] for name in SNAPSHOTS}
    for tf in GOLD_TIMEFRAMES:
        bars = tf_data.get(tf) or []
        b = bars[-1] if bars else None
        for name, build in zip(SNAPSHOTS, (_ema, _momentum, _volume, _volatility), strict=True):
            lines[name].append(f"{tf}: {build(b) if b is not None else 'N/A'}")
    return {name: "\n".join(rows) for name, rows in lines.items()}


def _ema(b: dict) -> str:
    close = b.get("close")
    e20, e50, e200 = b.get("EMA_20"), b.get("EMA_50"), b.get("EMA_200")
    pos = [
        f"{'>' if close > ev else '<'}EMA{lbl}"
        for lbl, ev in (("20", e20), ("50", e50), ("200", e200))
        if isinstance(close, (int, float)) and isinstance(ev, (int, float))
    ]
    return f"close {g(close)} {' '.join(pos) or 'N/A'} (EMA {g(e20)}/{g(e50)}/{g(e200)})"


def _momentum(b: dict) -> str:
    macd = "MACD N/A"
    if b.get("MACD") is not None:
        macd = (
            f"MACD {g(b['MACD'])} (Signal {g(b.get('MACD_Signal'))} | Hist {g(b.get('MACD_Hist'))})"
        )
    return (
        f"RSI {g(b.get('RSI'), 1)} | CMF {g(b.get('CMF'), 3)} | IPI "
        f"{g(b.get('IPI'), 1)}({b.get('IPI_Status') or '-'}) | {macd}"
    )


def _volume(b: dict) -> str:
    return (
        f"vol {g(b.get('volume'), 0)} | RVOL {g(b.get('RVOL'), 2)} | RVOL_Dev "
        f"{g(b.get('RVOL_Deviation'), 1)}%"
    )


def _volatility(b: dict) -> str:
    atr = f"ATR {g(b['ATR'])}" if b.get("ATR") is not None else "ATR N/A"
    bb = "Bollinger N/A"
    if b.get("BB_Middle") is not None:
        bb = (
            f"Bollinger (Middle {g(b['BB_Middle'])} | Upper {g(b.get('BB_Upper'))}"
            f" | Lower {g(b.get('BB_Lower'))})"
        )
    return f"FVG {g(b.get('FVG'))} | {atr} | {bb}"
