# Phase 2: budget headroom, write actions, CSRF readiness (web/)

Date: 2026-10-24/25. Only files under `web/` were edited. No backend was started against a
database and no production server was called: every write in dev and tests goes to MSW.

## Status

| Item | Result |
|--|--|
| 1. Initial bundle | ✅ 118.7 → **105.0 KB gzip** (with 4 new routes and 133 new messages added). See "Budget" below. |
| 2. Watchlist | ✅ add symbol (list, symbol, name, exchange), remove (2-step confirm), rename list. |
| 2. Portfolio | ✅ add trade (buy/sell, whole shares, positive price), remove symbol (2-step confirm), rename. |
| 2. Settings (`/settings/`) | ✅ timezone (offset −720..840 + label, "use this browser's zone"), 4 destination toggles, auto-skip 1..100, TV login mode 1/2/3, token status + update (password field, cleared on success, token never shown). |
| 2. Jobs (`/dashboard/`) | ✅ `/automate/status` polling (3 s while running, 20 s otherwise, paused while the tab is hidden), start auto with the server list (`auto/start_all`) or picked symbols (`auto/start`, rows, legacy CSV mode), stop (2-step), custom automate (timeframes + symbol picker + rows + extended), TV test (verdict + log lines), single fetch (`/data`) → table + lazy candle chart. |
| 2. Export (`/export/`) | ✅ `/export/check` per list + interval; plain `<a href download>` same-origin links for `export_zip` (interval / all), `export` part 1/2, `export_formula`, `export_news`. |
| 2. Gold (`/gold/`) | ✅ config, models, on-demand price, analyze (cost confirm, markdown result), server job start (cost confirm) / stop (confirm) / status (polls only while running, Drive link only if `https:`), per-mode gold export links from `/gold/modes`. |
| 2. Radar Summary | ✅ run a round (timeframes + "new record", confirm), delete the shown round (2-step). |
| 2. History | ✅ cleanup (hours 1..720, confirm) and clear-all (confirm). |
| 2. Stock Radar / Earning Scan | ✅ scan forms; confirm step shows a paid-provider warning (Stock Radar: only in `ai` mode; `logic` mode skips the AI call, so it gets a normal confirm). |
| 2. Confirms / results | ✅ `ConfirmAction` (shared/ui): first click opens a panel that says exactly what happens; confirm is disabled again if inputs become invalid. `ActionResult` shows success or the server `detail`. Every mutation invalidates its queries (`defineAction(run, invalidates)`). |
| 3. CSRF | ✅ `shared/api/csrf.ts`: POST/PUT/DELETE send `X-ZS-CSRF` = cookie `__Host-zs_csrf` when it exists; nothing otherwise. Only `apiSend` uses it. |
| 4. MSW | ✅ stateful in-memory db (`mocks/db.ts`, reset after each test); handlers for every new endpoint, with the backend's status codes and `detail` texts (400/404/409). Smoke-checked `npm run dev:mock`: `/app/`, `/app/dashboard/`, worker → 200. |
| 4. Tests | ✅ 24 files, 68 tests (was 14/37). Each action is run against MSW with a real QueryClient (`mocks/actionHarness.ts`), checking the request effect, the invalidated keys and error `detail`; each confirm is server-rendered in its open state (`defaultOpen`) to check the text and the cost warning. No jsdom. |
| `npm run verify` | ✅ green. |

## Budget (gzip, `check-budget`)

| Step | Initial JS |
|--|--|
| Phase 1 baseline | 118.7 KB (index 98.9 + common 19.8) |
| `env.ts` without zod + `VersionBadge` lazy | 115.9 |
| zod in its own Rolldown group (`build.rolldownOptions.output.codeSplitting.groups`) | 116.3 (zod still pulled by route `validateSearch`) |
| route `validateSearch` with plain helpers (`shared/lib/search.ts`) | 109.2 |
| nav titles from an explicit map (`messageKey.ts`) — `m[key]` had put **every** message in the entry | (measured together with Phase 2 code) |
| Phase 2 pages + messages added | 106.9 |
| shell icons as inline SVG (lucide runtime was ~3 KB raw for 2 glyphs) | 105.8 |
| `ApiError`/`shouldRetry` split from `client.ts`; form limits/domain lists to `config/domain.ts` | **105.0** |

Final: `initial JS gzip 105.0 KB (limit 120.0 KB)`, CSS 2.7 KB. Largest lazy chunks: CandleChart 50.5,
markdown 27.2, watchlist 21.4, zod 6.4, dashboard 5.9 (all ≤ 60). zod is now a lazy, cache-stable
chunk that changes only on a zod upgrade.

Findings: Rolldown's default chunking merged lazy-only shared modules (zod) into the chunk the entry
imports for React; the codeSplitting group fixes that. Dynamic `m[key]` defeats tree-shaking of
Paraglide messages: never index `m` with a runtime key (a new tab adds its `nav_*` to the map in
`shared/i18n/messageKey.ts`). Side effect: lazy pages now load several tiny message chunks
(0.1–0.4 KB each); acceptable, could be grouped later with `entriesAware` groups.

## Endpoint assumptions

| Endpoint | Assumption |
|--|--|
| `POST /api/auto/start`, `/api/automate`, `/api/stock_radar/scan` | `symbols` = `[{symbol, exchange}]` (legacy sends that; OpenAPI says `object[]`). Symbols without a known exchange (from `/api/symbols`) are skipped and listed. |
| `POST /api/stock_radar/scan` | Generated type requires `model` (OpenAPI default); we send the backend default `gemini-2.5-flash` from `config/domain.ts`. Legacy sends none. |
| `POST /api/data` | Returns bar records with `datetime` "YYYY-MM-DD HH:MM:SS"; chart reads it as UTC wall clock. It also stores history, so `['history']` is invalidated. |
| `POST /api/settings/destinations` | One flag per request (legacy does this); reply has all four. |
| `POST /api/settings/tv_mode` | Also clears the server's cached login, so the token status query is invalidated too. |
| `GET /api/gold/price` | Live TradingView fetch per call → only on button click (`enabled: false`). |
| `POST /api/gold/automate/stop` | Reply `{detail: "Stop signal sent" | "No job running"}` with HTTP 200, shown as success text. |
| `GET /api/export*`, `/api/gold/export` | Plain links carry no Bearer header: they rely on the legacy `z_token` cookie (or the future HttpOnly cookie). Not verified against a real server. |
| `POST /api/radar_round/run` | 409 while a round runs; reply has the `/status` shape. |
| `DELETE /api/history` | Clears every row (no query param). |

## OpenAPI

Regenerated with the Phase 1 offline command. Same 53 paths, same methods and params; only
docstrings and `list_name` nullability (`/api/export`, `/api/export_zip`) changed from the
backend refactor. **Regenerate again after the backend refactor settles** (`gen:api` too).

## Other changes

- `shared/api/client.ts`: `apiSend(method, path, schema, {path, query, body})`, typed from OpenAPI (wrong path/body = type error).
- `shared/api/lists.ts`: symbols + watchlist queries moved from features (jobs/export/scans need them; features cannot import each other).
- `features/chart` (demo) → `shared/chart/` (`ChartPanel`, `CandleChart`, `toCandles` + test). Demo `makeCandles` removed.
- Lint: re-export specifiers (`export … from '…/shared/api/…'`) are allowed like imports.
- `lucide-react` is now unused (kept in package.json; tree-shaken to 0 bytes). Remove with `npm uninstall` when convenient.
- New deps: **none**.

## Not done / next

- No headless-Chrome pass this phase (CSP/no-violation and the mock worker in a real tab not re-measured).
- No per-row remove buttons in the virtual watchlist table: remove is a select + confirm in the "Edit lists" panel.
- Stock Radar model picker: not offered (legacy has none); the backend default is sent.
- `check-lockfile` script still open.
