# Configuration reference

Generated from the Settings classes by `tools/config_reference.py`; do not edit by hand.
Every variable the backend reads is listed here. A blank value means the default, and a
malformed one stops the boot with the variable named. Production values are set in
Coolify (docs/runbook-deploy.md); secrets are never printed.

## RoundsSettings (`radar_engine.rounds.config`)

Round settings: the timeframes the screen understands, retention, staleness limits.

| Variable | Type | Default | Description |
|---|---|---|---|
| `RADAR_KEEP_ROUNDS` | int > 0 | `30` | Radar rounds kept; older ones are pruned after a run. |

## RuntimeSettings (`zservice.core.runtime`)

Process-wide runtime settings: where the app may write, and whether /docs is served.

| Variable | Type | Default | Description |
|---|---|---|---|
| `ZS_STATE_DIR` | str | — | Writable directory for automate.log and the TradingView token cache. The image sets an app-owned one (the code is read-only for the app user). |
| `ZS_DOCS` | bool | `true` | Serve /docs and /openapi.json (behind the session gate). |

## MongoSettings (`zservice.db.config`)

MongoDB connection settings.

| Variable | Type | Default | Description |
|---|---|---|---|
| `MONGO_URI` | secret | — | Connection string (mongodb+srv://…); unset = every DB call fails. |
| `MONGO_DB` | str | `zservice` | Database name. |

## AuthSettings (`zservice.domains.auth.config`)

Sign-in settings: first-run registration and the brute-force windows.

| Variable | Type | Default | Description |
|---|---|---|---|
| `ZS_ALLOW_REGISTER` | bool | `false` | Open registration while no user exists (first run only). Never in production: a wiped user collection must not let anyone claim the account. |
| `ZS_LOGIN_RATE_LIMIT` | int > 0 | `5` | Sign-in attempts per IP + username per window. |
| `ZS_LOGIN_IP_RATE_LIMIT` | int > 0 | `20` | Sign-in attempts per IP per window (needs FORWARDED_ALLOW_IPS behind a proxy). |
| `ZS_LOGIN_RATE_WINDOW_S` | int > 0 | `60` | Sign-in rate-limit window (seconds). |

## EarningScanSettings (`zservice.domains.earning_scan.config`)

Earnings provider keys; an empty key skips that provider in the fallback chain.

| Variable | Type | Default | Description |
|---|---|---|---|
| `FINNHUB_API_KEY` | secret | — | Finnhub key (first in the chain). |
| `FMP_API_KEY` | secret | — | Financial Modeling Prep key. |
| `ALPHA_VANTAGE_API_KEY` | secret | — | Alpha Vantage key (last in the chain). |

## GoldSettings (`zservice.domains.gold.config`)

Gold analysis configuration: data sources, timeframes and the prompt template.

| Variable | Type | Default | Description |
|---|---|---|---|
| `GOLD_PROMPT_PATH` | str | — | Prompt template override (default trade_instruction/gold.md). |

## InboundEventSettings (`zservice.domains.inbound_events.config`)

Who may send events and how they are checked.

| Variable | Type | Default | Description |
|---|---|---|---|
| `ZS_EVENT_SENDERS` |  | `[]` | Allowed senders, JSON: [{"name": "engine", "secret": "whsec_...", "public_key": "whpk_..."}] (a secret, a public key or both). |
| `ZS_EVENT_TOLERANCE_SECONDS` | int ≥ 30 | `300` | Largest clock difference accepted. |
| `ZS_EVENT_MAX_BYTES` | int > 0 | `262144` | Largest event body. |
| `ZS_EVENT_KEEP_DAYS` | int ≥ 1 | `30` | Days events are kept. |

## JobsSettings (`zservice.domains.jobs.config`)

Auto job settings: autostart after boot, pacing, cross-container takeover.

| Variable | Type | Default | Description |
|---|---|---|---|
| `ZS_AUTOSTART` | bool | `true` | Start the auto job after boot with the server symbol list. |
| `ZS_AUTOSTART_DELAY` | float ≥ 0 | `30` | Wait before autostart (s): TradingView session warm-up. |
| `ZS_JOB_HEARTBEAT_STALE_S` | int > 0 | `180` | Another container's job heartbeat older than this is dead; autostart takes over. |
| `SYMBOL_DELAY_SECONDS` | int ≥ 0 | `0` | Extra gap between symbols (s); redundant by default (the TradingView throttle spaces requests). |
| `AUTO_FORCE_ALL_TF` | bool | `false` | Legacy: fetch all four timeframes every round, closed bars or not. |

## IndicatorSettings (`zservice.domains.market_data.config`)

Indicator look-back periods (bars). The CSV export prints cmf_period in its header.

| Variable | Type | Default | Description |
|---|---|---|---|
| `RSI_PERIOD` | int > 0 | `50` | RSI period (Wilder smoothing). |
| `CMF_PERIOD` | int > 0 | `50` | Chaikin money flow period. |
| `RVOL_PERIOD` | int > 0 | `50` | Relative volume look-back. |
| `OBV_SLOPE_WINDOW` | int > 0 | `50` | OBV slope look-back. |

## SymbolsSettings (`zservice.domains.symbols.config`)

Where build_meta.py wrote the server symbol list and the build metadata.

| Variable | Type | Default | Description |
|---|---|---|---|
| `SYMBOLS_FILE` | str | — | Server symbol list written at build time (backend/symbols.json). |
| `VERSION_FILE` | str | — | Build metadata for /api/version (backend/VERSION.json). |
| `SOURCE_COMMIT` | str | — | Commit being run, set by the hosting panel at run time (Coolify does); /api/version shows it when the build did not record one. |

## DriveSettings (`zservice.integrations.drive`)

Google Drive (OAuth, user-owned quota).

| Variable | Type | Default | Description |
|---|---|---|---|
| `GDRIVE_ROOT_FOLDER_ID` (legacy `google_drive_folder_id`) | str | — | Every Drive read and write stays inside this folder tree. |
| `GOOGLE_OAUTH_CLIENT_ID` | str | — | OAuth client id. |
| `GOOGLE_OAUTH_CLIENT_SECRET` | secret | — | OAuth client secret. |
| `GOOGLE_OAUTH_REFRESH_TOKEN` | secret | — | Refresh token granted with the drive.file scope. |

## GeminiSettings (`zservice.integrations.gemini`)

Google Gemini generateContent client (GEMINI_API_KEY, Coolify env).

| Variable | Type | Default | Description |
|---|---|---|---|
| `GEMINI_API_KEY` | secret | — | Gemini key (gold analysis, AI scans). |

## TelegramSettings (`zservice.integrations.telegram`)

Telegram notifications to the allowed chats (TELEGRAM_* settings below).

| Variable | Type | Default | Description |
|---|---|---|---|
| `TELEGRAM_BOT_TOKEN` | secret | — | Bot token; unset = notifications skipped. |
| `TELEGRAM_ALLOWED_CHAT_IDS` | comma list | — | Comma-separated chat ids that get notifications. |

## TradingViewSettings (`zservice.integrations.tradingview.config`)

TradingView credentials and request pacing.

| Variable | Type | Default | Description |
|---|---|---|---|
| `TV_USERNAME` | str | — | Sign-in user (auth mode 1). |
| `TV_PASSWORD` | secret | — | Sign-in password. |
| `TV_AUTH_TOKEN` | secret | — | Session token (auth mode 2; also the fallback when sign-in fails). |
| `TV_WS_TIMEOUT` | int > 0 | `15` | Websocket read timeout (s); tvdatafeed's own 5 s kills fetches TradingView only stalled while soft-throttling. |
| `TV_MIN_REQUEST_INTERVAL` | float ≥ 0 | `1.5` | Global spacing between requests (s); bursts of ~10 trip TradingView's limit. |
| `TV_COOLDOWN_SECONDS` | int ≥ 0 | `120` | Pause after repeated empty responses signal a tripped limit (s). |

## SecuritySettings (`zservice.security.config`)

Security settings shared by the session layer and the HTTP middleware.

| Variable | Type | Default | Description |
|---|---|---|---|
| `AUTH_SECRET` | secret | — | Signs session tokens. Required: the app refuses to start below 28 bytes. |
| `ZS_MAX_BODY_BYTES` | int > 0 | `2097152` | Request body cap; the largest real body (a full-universe scan) is ~100 KB. |
| `ZS_REVOCATION_CACHE_S` | int ≥ 0 | `15` | How stale the session revocation list may be (another container sees a logout within this time). |
| `FORWARDED_ALLOW_IPS` | str | — | Read by uvicorn (proxy addresses it trusts). With '*' the client address is the rightmost X-Forwarded-For entry (client_ip.py). |
| `ZS_CORS_ORIGINS` | comma list | — | Local development only: comma-separated origins of a dev server on another port. '*' is refused. Production is one origin and needs none. |

## MachineSettings (`zservice.security.machine.config`)

Machine-key settings (plan B3): the key registry, its rate limit and audit ring.

| Variable | Type | Default | Description |
|---|---|---|---|
| `ZS_API_KEYS` | secret | — | Scoped machine keys: JSON list of {id, scopes, sha256, expires} (keys.py). |
| `PULL_KEY` | secret | — | Legacy single key of the old scripts, limited to LEGACY_SCOPES; unset to retire. |
| `ZS_MACHINE_RATE_LIMIT` | int > 0 | `300` | Requests per key per window. |
| `ZS_MACHINE_RATE_WINDOW_S` | int > 0 | `60` | Machine rate-limit window (seconds). |
| `ZS_AUDIT_RING_SIZE` | int > 0 | `2000` | Machine access decisions kept in memory. |

## WebSettings (`zservice.web.config`)

Where the built frontends are served from.

| Variable | Type | Default | Description |
|---|---|---|---|
| `APP_BASE` | str | `/app/` | Base path of the web UI; must match its build (Dockerfile). |
| `FRONTEND_DIR` | str | `static` | Built frontends: the legacy dashboard at /, the web UI under APP_BASE. |
