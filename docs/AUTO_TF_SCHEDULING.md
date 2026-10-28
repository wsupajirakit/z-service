# Auto Automate — TF-aware fetch scheduling

**Date:** 2026-09-01 · **File touched:** `backend/main.py` (one file)

## Problem

A full `Automate All` round took **~66 minutes** and was getting slower.

`AUTO_STEPS = [("1h",True),("4h",True),("1d",False),("1w",False)]` was executed in
full on **every** round, so one round issued:

```
395 symbols x 4 timeframes = 1,580 TradingView requests
  throttle  1,580 x TV_MIN_REQUEST_INTERVAL (1.5s) = 39.5 min
  symbol gap  395 x 4 x SYMBOL_DELAY_SECONDS (1s)  = 26.3 min
                                            total  ~66 min (before network/retries/cooldowns)
```

Most of that work was wasted. A bar can only be re-read after it closes:

| TF | bar closes | re-fetched every round? | waste |
|----|-----------|--------------------------|-------|
| 1h | hourly    | needed                   | 0%    |
| 4h | 2x/day    | yes                      | ~71%  |
| 1d | 1x/day    | yes                      | ~85%  |
| 1w | 1x/week   | yes                      | ~97%  |

Re-pulling `1w` and `1d` every 15 minutes also **rewrote bars that had already
closed**, which is the source of the `1W moved mid-week` artifact the radar
health check reports daily (112 rewritten 1w bars on 2026-09-01, causing 25
symbols to change `stage` for non-market reasons).

## Change

**Symbol coverage is unchanged — all 395 symbols are still fetched every round.**
Only the *timeframe* list per round is filtered.

### 1. `SYMBOL_DELAY_SECONDS` default `1` -> `0`

The inline comment already stated that `TV_MIN_REQUEST_INTERVAL` (1.5s, enforced
globally under a lock in `_tv_wait_turn()`) is the real rate-limit guard, so this
extra per-symbol sleep was redundant double-throttling. Still overridable by env.

### 2. New `steps_due()` — fetch a TF only when its newest closed bar changed

```python
_tf_bar_key(tf, now_et)   # identity of the newest CLOSED bar
  1h -> 1h|<date>|<hour>
  4h -> 4h|<date>|<hour//4>
  1d -> 1d|<last completed session date>
  1w -> 1w|<last completed session date>
```

`_last_completed_session_date()` rolls at **16:00 ET**, so before the close the
key still points at the previous session (a daily bar is not final until 16:00).

`steps_due()` returns only the timeframes whose key changed since the last
successful fetch. `1h` always runs so a round is never empty.

**`1w` is keyed to the daily close, not the ISO week.** The weekly bar is still
forming during the week, so it is refreshed once per session to keep current-week
values live — while removing the ~28 rewrites/day that caused the artifact.

### 3. Keys persisted in Mongo (`settings.auto_last_tf_bar_key`)

`_load_tf_bar_keys()` runs at the start of `run_auto_job()`; `_save_tf_bar_keys()`
runs after each step completes. A restart therefore resumes the cadence instead of
triggering a needless full 4-TF pull. Keys are plain strings so the JSON
round-trip is lossless. Any Mongo error degrades to "fetch everything once" and is
logged — it never blocks a round.

### 4. Escape hatch

`AUTO_FORCE_ALL_TF=1` restores the previous always-fetch-all-four behaviour with
no code change.

## Result (simulated over 7 days, one round per 15 min, 04:00-20:00 ET)

```
rounds:            448
fetches per TF:    1h=448   4h=28   1d=8   1w=8
requests:          707,840 -> 194,340   (-73%)
avg round time:    ~66 min -> ~11 min   (~6x faster)
```

## Rate limiting / blocking

`TV_MIN_REQUEST_INTERVAL` was **not** lowered — request *spacing* is unchanged at
1.5s. We cut the request *count*, which makes the job both faster and gentler on
the upstream at the same time. All existing protections are untouched: global
throttle lock, 120s cooldown on repeated empty responses (`_tv_trip_cooldown`),
retry with backoff, and the extended -> non-extended session fallback.

Note: bulk automated extraction remains against TradingView's terms of service and
an account/IP can still be blocked regardless of pacing. A licensed feed
(Polygon.io, Databento, EODHD, Tiingo, Alpaca) would remove both the throughput
ceiling and that risk, since those APIs accept hundreds of symbols per request.

## Deploy note

The Auto Job snapshots its symbol list in memory at Start. After deploying, press
**หยุด Auto Run** then **Automate All** again so the new schedule and the current
symbol list both take effect (same step 4 as `ADD_SYMBOLS.md`).
