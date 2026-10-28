"""The gold analysis: market inputs + news + indicator snapshots -> prompt -> Gemini."""

from datetime import UTC, datetime

from zservice.core.errors import ApiError
from zservice.integrations import gemini
from zservice.integrations.gemini import call_gemini as _call_gemini
from zservice.integrations.news import fetch_all_news

from .config import GOLD_SOURCE_EXCHANGES, GOLD_SOURCES, GOLD_TIMEFRAMES
from .indicators import _gold_indicator_snapshots
from .inputs import change_24h, fetch_cross_market, fetch_timeframes
from .prompt import fib_snapshot, fmt_num, render_prompt
from .prompt import load_gold_prompt_template as _load_gold_prompt_template
from .schemas import GoldAnalyzeRequest
from .state import gold_stop_event

MAX_NEWS_LINES = 40
NO_CALENDAR = "N/A (no economic calendar in the system)"


def _gold_analyze_core(req: GoldAnalyzeRequest) -> dict:
    _validate(req)
    tf_blocks, tf_data, latest_price = fetch_timeframes(req.exchange, req.rows)
    cross = fetch_cross_market()
    news = fetch_all_news()
    news_lines = [f"- ({n['source']}) {n['title']}" for n in news[:MAX_NEWS_LINES]]
    news_lines = news_lines or ["- (no news available)"]
    snaps = _gold_indicator_snapshots(tf_data)
    source_label = next(
        (s["label"] for s in GOLD_SOURCES if s["exchange"] == req.exchange), req.exchange
    )
    fills = {
        "source_label": source_label,
        "current_price": latest_price if latest_price is not None else "N/A",
        "price_change_24h": change_24h(tf_data.get("1h")),
        **_cross_fills(cross),
        # Technical snapshots (computed where available, N/A otherwise).
        "ema_snapshot": snaps["ema"],
        "momentum_snapshot": snaps["momentum"],
        "volume_snapshot": snaps["volume"],
        "volatility_snapshot": snaps["volatility"],
        "fib_snapshot": fib_snapshot(tf_data),
        # Context.
        "timeframe": " / ".join(GOLD_TIMEFRAMES),
        "user_direction_interest": "N/A",
        "risk_percent": getattr(req, "risk_percent", None) or "N/A",
        "recent_news": "\n".join(news_lines),
        "upcoming_events": NO_CALENDAR,
        # Legacy slots (still supported if a template uses them).
        "tf_blocks": "\n".join(tf_blocks),
        "news_lines": "\n".join(news_lines),
    }
    prompt = render_prompt(_load_gold_prompt_template(), fills, tf_blocks)
    if gold_stop_event.is_set():
        raise Exception("Stopped by user")

    return {
        "exchange": req.exchange,
        "source_label": source_label,
        "model": req.model,
        "latest_price": latest_price,
        "timeframes": GOLD_TIMEFRAMES,
        "cross_market": cross,
        "snapshots": snaps,  # per-TF indicator snapshots (for CSV export)
        "news_count": len(news),
        "tf_blocks": tf_blocks,  # kept for the CSV export (input data)
        "news_lines": news_lines,  # kept for the CSV export (input data)
        "analysis": _call_gemini(req.model, prompt),
        "generated_at": datetime.now(UTC).isoformat(),
    }


def _validate(req: GoldAnalyzeRequest) -> None:
    if not gemini.configured():
        raise ApiError(400, "ai.no_api_key", "GEMINI_API_KEY is not set on the server.")
    if req.exchange not in GOLD_SOURCE_EXCHANGES:
        allowed = sorted(GOLD_SOURCE_EXCHANGES)
        raise ApiError(
            400,
            "gold.unsupported_source",
            f"Unsupported source. Use one of: {allowed}",
            params={"allowed": ", ".join(allowed)},
        )


def _cross_fills(cross: dict) -> dict:
    silver = cross.get("silver_price")
    silver_text = "N/A"
    if silver is not None and silver != "N/A":
        silver_text = f"{fmt_num(silver)} (change {cross.get('silver_price_change', 'N/A')})"
    return {
        "dxy_level": fmt_num(cross.get("dxy_level")),
        "dxy_change": cross.get("dxy_level_change", "N/A"),
        "us10y_yield": fmt_num(cross.get("us10y_yield")),
        "us10y_change": cross.get("us10y_yield_change", "N/A"),
        "vix_level": fmt_num(cross.get("vix_level")),
        "silver_price": silver_text,
    }
