# z-service — Market Data Service

z-service is the data backbone of a stock research stack. It pulls price bars for about
850 US stocks and ETFs on four timeframes (1 hour, 4 hours, 1 day, 1 week) from TradingView,
computes the indicators the research needs, keeps the history in MongoDB, and serves it to
scripts, reports and other services through one API and a web console.

It was built so that every consumer — a screening script, a written report, an analysis
engine — reads the **same snapshot of the same data**, refreshed on a schedule, instead of
each one fetching and computing its own.

## What it does

- **Fetches only what changed.** The scheduler tracks the newest closed bar of every
  timeframe and asks for new bars only. A full round over all symbols dropped from about 66
  to about 11 minutes, and bars that have already closed are never rewritten.
- **Computes the indicators once.** EMA 20/50/100/200, RSI, Chaikin money flow, OBV, VWAP,
  relative volume, fair value gaps and an institutional-pressure index (IPI) that combines
  money flow, volume and OBV into "accumulation / distribution / neutral".
- **Exports that scripts can trust.** Multi-timeframe CSV files split into parts, a formula
  sheet, and a one-call ZIP of everything. Recently listed stocks with a short history are
  kept and flagged rather than silently dropped, so every consumer sees the same universe.
- **Runs the screening engine on the server.** The research engine runs inside the service
  and produces a "radar summary" round on demand; a parity test keeps it identical to the
  original scripts.
- **Follows the market clock.** NYSE holidays, regular and extended sessions and the
  daylight-saving changes come from the exchange calendar, never from hard-coded times.
- **Talks to other systems.** Inbound events (CloudEvents over Standard Webhooks, signed with
  HMAC or Ed25519) are stored once per delivery, so senders can retry safely; results can go
  to Telegram and Google Drive; a gold mode produces data sets and AI analysis for XAUUSD.

## The console

A web console in English and Thai, light and dark, covering every part of the service:

| Page | What it is for |
| --- | --- |
| Dashboard | Start a fetch (one symbol, a watchlist or everything), watch the automatic rounds live |
| Gold | Live XAUUSD price, AI entry analysis, and data sets for four trading styles |
| Radar / Radar Summary | Screening rounds: stages, triggers, trade plans and the market regime |
| Earning Scan | Upcoming earnings and EPS history for chosen symbols |
| Watchlists | Themed lists of symbols, each with its own identity, in a full-screen list/detail view |
| Portfolio | Trades per portfolio with positions computed on the server |
| History | Every stored fetch by symbol or by round, with an interactive chart and indicator table |
| Export | The CSV/ZIP exports and automated multi-timeframe jobs |

## Security

- **People** sign in with a password (PBKDF2, 600,000 rounds); sessions are signed tokens
  that can be revoked on sign-out or password change, carried in `__Host-` cookies with CSRF
  protection.
- **Machines** use scoped keys — only a SHA-256 hash of each key is stored, every key has a
  list of what it may call (anything else is denied), and requests are rate-limited.
- **The perimeter** has strict security headers, a request-size limit, a per-client limit
  on sign-in attempts and on wrong keys, and configuration that is validated at start-up:
  a wrong value stops the service instead of running with a silent default.

## Architecture

```
TradingView ──► fetch scheduler ──► indicators ──► MongoDB
                                                     │
              scripts ◄── exports / API (FastAPI) ◄──┤
              reports ◄── radar engine ◄─────────────┤
      other services ──► signed inbound events ──────┘
              people ──► web console (React)
```

The backend is organised by domain — watchlists, portfolio, radar rounds, earnings scan,
gold, exports, history, jobs, settings — each in its own module with its own typed settings.

| Part | Folder |
| --- | --- |
| API, scheduler and domains (Python, FastAPI) | `backend/zservice` |
| Screening engine run by the service | `backend/radar_engine` |
| Main console (React 19, Vite, HeroUI, Tailwind) | `dash` |
| Second console at `/app/` (React, TanStack Router/Query) | `web` |
| Maintenance scripts (symbols, watchlists) | `scripts`, `tools` |
| Operations and design notes | `docs` |

**Stack:** Python 3.12 · FastAPI · pandas · MongoDB · pydantic-settings · React 19 · Vite ·
TypeScript · HeroUI · TanStack · lightweight-charts · Docker.

## Running it

The image builds both consoles and the API, and serves everything on port 9999:

```bash
docker build -t zservice .
docker run -p 9999:9999 --env-file .env zservice
# health check: http://localhost:9999/api/healthz
```

Every setting is listed in [docs/config-reference.md](docs/config-reference.md) with its
type, default and limits. The essentials are `MONGO_URI` (the database), `AUTH_SECRET`
(signs sessions, at least 28 characters) and the TradingView sign-in. Deployment steps are
in [docs/runbook-deploy.md](docs/runbook-deploy.md).

For development:

```bash
cd backend && python -m venv venv && venv/bin/pip install -r requirements.lock
venv/bin/uvicorn main:app --port 9999 --reload     # API
cd dash && npm ci && npm run dev                    # main console
```

## Quality

Every change goes through the same gate: ruff (lint and format), size limits per module,
the full pytest suite (about 290 tests, including security and parity tests), TypeScript
type checks, ESLint with zero warnings, the console builds and a dependency advisory audit.
