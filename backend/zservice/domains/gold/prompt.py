"""Gold prompt: the editable template (trade_instruction/gold.md) and how it is filled.

Looked up next to main.py (the Docker image copies it to /app/trade_instruction), then the
repo's .claude/trade_instruction (local dev), then the working directory.
"""

import os
from pathlib import Path

from . import config as gold_config
from .config import GOLD_TIMEFRAMES

FIB_LEVELS = (
    ("23.6%", "Fib_236"), ("38.2%", "Fib_382"), ("50.0%", "Fib_500"), ("61.8%", "Fib_618"),
    ("78.6%", "Fib_786"),
)  # fmt: skip
PRICE_HISTORY_HEADING = "\n\n---\n## Multi-timeframe price history (cite real price levels)\n"

BACKEND_DIR = Path(__file__).resolve().parents[3]  # the folder main.py lives in


def load_gold_prompt_template() -> str:
    candidates = [
        gold_config.get_settings().prompt_path,
        str(BACKEND_DIR / "trade_instruction" / "gold.md"),
        str(BACKEND_DIR / ".." / ".claude" / "trade_instruction" / "gold.md"),
        "trade_instruction/gold.md",
    ]
    for p in candidates:
        if p and os.path.isfile(p):
            with open(p, encoding="utf-8") as f:
                return f.read()
    return ""  # caller falls back to a built-in prompt


def fmt_num(v, nd=2) -> str:
    return f"{v:.{nd}f}" if isinstance(v, (int, float)) else "N/A"


def fib_snapshot(tf_data: dict) -> str:
    """Latest Fibonacci retracement levels per timeframe, one line each."""
    lines = []
    for tf in GOLD_TIMEFRAMES:
        bars = tf_data.get(tf) or []
        b = bars[-1] if bars else {}
        if b.get("Fib_High") is None or b.get("Fib_Low") is None:
            lines.append(f"{tf}: N/A")
            continue
        levels = ", ".join(f"{label}: {fmt_num(b.get(key))}" for label, key in FIB_LEVELS)
        lines.append(
            f"{tf}: High {fmt_num(b['Fib_High'])} | Low {fmt_num(b['Fib_Low'])} | Levels ({levels})"
        )
    return "\n".join(lines)


def render_prompt(template: str, fills: dict, tf_blocks: list[str]) -> str:
    """Fill the {{slot}}s of the template and append the full multi-TF bars (the
    snapshots hold only the latest values; the model needs exact levels to cite).
    Without a template a built-in short prompt keeps the feature working."""
    if not template:
        return (
            f"You are a professional gold (XAUUSD) trader. Give a short-term analysis.\n"
            f"MARKET SOURCE: {fills['source_label']} | price ~{fills['current_price']}\n"
            f"DXY={fills['dxy_level']} US10Y={fills['us10y_yield']} VIX={fills['vix_level']} "
            f"Silver={fills['silver_price']}\n\n"
            f"{fills['tf_blocks']}\n\nNews:\n{fills['news_lines']}\n\n"
            "Answer in English: overview, bias (LONG/SHORT/WAIT), trade plan "
            "(Entry/SL/TP/RR), risks"
        )
    prompt = template
    for k, v in fills.items():
        prompt = prompt.replace("{{" + k + "}}", str(v))
    return prompt + PRICE_HISTORY_HEADING + "\n".join(tf_blocks)
