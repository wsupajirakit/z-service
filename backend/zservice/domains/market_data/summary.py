"""Compact text block of recent bars for LLM prompts (shared by gold and the stock radar
scan; moved unchanged from main.py)."""


def summarize_bars(result_list: list, tf: str) -> str:
    """Compress a timeframe's bars into a compact text block for the LLM prompt.
    Sends the latest ~30 bars (enough context without blowing the token budget)."""
    bars = result_list[-30:]
    lines = [
        f"[{tf}] latest {len(bars)} bars (oldest→newest): datetime | O H L C | vol | EMA20/50/200 "
        "| RSI | CMF | IPI(status) | FVG"
    ]
    for b in bars:

        def f(v, nd=2):
            return f"{v:.{nd}f}" if isinstance(v, (int, float)) else "-"

        lines.append(
            f"{b.get('datetime')} | {f(b.get('open'))} {f(b.get('high'))} {f(b.get('low'))} "
            f"{f(b.get('close'))} | "
            f"{f(b.get('volume'), 0)} | "
            f"{f(b.get('EMA_20'))}/{f(b.get('EMA_50'))}/{f(b.get('EMA_200'))} | "
            f"{f(b.get('RSI'), 1)} | {f(b.get('CMF'), 3)} | "
            f"{f(b.get('IPI'), 1)}({b.get('IPI_Status') or '-'}) | {f(b.get('FVG'))}"
        )
    return "\n".join(lines)
