"""Standalone gold-trading data routes (XAUUSD @ IC Markets by default).

Design goals (docs/gold-mode-design.md):
- Fully separate from the stock automate/export flow: own TvDatafeed instance,
  own indicator math, own news fetch, no reads/writes to Mongo history.
- On-demand fresh fetch per request with a per-mode TTL cache (the stock rounds
  are far too slow/stale for minute timeframes).
- Auth: nothing here — the app-wide middleware (zservice/security/middleware.py) already
  gates every /api/* route with the same session / machine key.

Every ZIP embeds gold_formula.csv: an instruction block telling the analyst AI
exactly what to return (bias per TF, order type BUY/SELL LIMIT/STOP or NO-TRADE,
entry/SL/TP1/TP2 + R:R, invalidation, TA summary, companion/indices impact,
news) plus a reading guide (tick-volume caveat, correlations) and latest news.

Known issue kept as-is (plan B16): this mode has its own TvDatafeed instance (shared across
threads, tvdatafeed's own login) and bypasses the global TradingView throttle.
"""
