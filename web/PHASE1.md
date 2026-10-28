# Phase 1: shared layer, shell, read-only pages (web/)

Date: 2026-10-24. Nothing outside `web/` was changed. No backend was started against a database
and no production server was called: every request in dev and tests goes to MSW.

## Status

| Item | Result |
|--|--|
| API client | ✅ `src/shared/api/client.ts`: native fetch, same-origin, `credentials: 'include'`, JSON, `ApiError` (status + server `detail`), zod/mini parse at the boundary, 401 → `session.onUnauthorized()` → `/login`. Paths/params typed from OpenAPI. |
| OpenAPI types | ✅ `openapi/openapi.json` generated offline (command below). `npm run gen:api` → `src/shared/api/openapi.gen.ts` (generated, lint-ignored). |
| Response schemas | ✅ zod/mini `looseObject` per endpoint in `features/*/schemas.ts` + `shared/api/common.ts` (version, timezone). |
| Query client | ✅ `src/app/queryClient.ts`, defaults from `src/shared/config/app.ts` (staleTime static 5 min / list 30 s / status 5 s; no background polling; no retry on 4xx). Radar status polls every 5 s only while `status === 'running'`. |
| Session | ✅ `src/shared/auth/session.ts`: `checkSession()` via `/api/version`, `logout()` mirrors legacy `dash/src/auth.ts` (removes `z_token` from localStorage + cookie, goes to `/login`). The legacy Bearer header is isolated in `legacyAuthHeaders()`; delete it when the HttpOnly cookie lands. |
| Shell | ✅ nav from route `staticData`, language switcher (names from `Intl.DisplayNames`), theme switcher, version badge, legacy-UI link, logout. |
| Pages | ✅ Overview (`/api/symbols` + `/api/version`), Watchlist (grouped counts, search, list filter, virtual + sortable table), Portfolio, History (`?id=` detail), Radar Summary (`?stamp=`; status, tf_status, list, digest markdown), Stock Radar history, Earning Scan history. |
| Markdown | ✅ `src/shared/lib/markdown.tsx` is the only importer of markdown-to-jsx (lint-enforced), `disableParsingRawHTML: true`. Test checks `<b>` in a digest stays text. |
| Format | ✅ `src/shared/lib/format.ts` + `useFormat()`: Intl by selected locale; wall clock from `/api/settings/timezone` offset (not the browser zone), label appended. |
| MSW | ✅ `src/mocks/{fixtures,handlers,browser,testServer}.ts`. `npm run dev:mock` (`vite --mode mock`): the `msw/vite` plugin in `worker-only` mode serves `/app/mockServiceWorker.js` in mock mode only. Smoke-checked: `/app/` 200, worker 200. Production `dist/` has no worker and no MSW code. |
| Tests | ✅ 11 files, 29 tests: client against MSW (path params, 404 detail, bad body, 401), formatters in 3 locales, schema + model + one server-render test per page. |
| `npm run verify` | ✅ green, see sizes below. |

## OpenAPI document (offline)

```
cd backend && env MONGO_URI= ZS_AUTOSTART=0 TV_USERNAME= TV_PASSWORD= TV_AUTH_TOKEN= \
  venv/bin/python -c "import json,main; print(json.dumps(main.app.openapi()))" \
  | grep -v '^\[' > ../web/openapi/openapi.json
cd ../web && nice -n 15 npm run gen:api
```

Stdout carried 3 `[store]/[Startup]/[frontend]` lines (Mongo not configured), filtered out. 55 paths.
Re-run both commands whenever the backend routes change (the parent's refactor may move routes).

`apiGet()` takes paths relative to the API base (`'history/{history_id}'`), so no `/api/` literal exists
outside `src/shared/api`. A wrong path or param name is a type error.

## New dependencies

| Package | Version | Kind | Why |
|--|--|--|--|
| `markdown-to-jsx` | 9.10.3 | runtime | Chosen in Phase 0 (0 deps, provenance). Lazy chunk 27.2 KB gzip. |
| `msw` | 3.0.3 | dev | Mocks for `dev:mock` and tests (no backend, no DB). |
| `openapi-typescript` | 7.13.0 | dev | Request/param types from OpenAPI. Its peer is `typescript ^5`; we use 6.0.3, so `package.json` has `overrides: { "openapi-typescript": { "typescript": "$typescript" } }`. Generation works with TS 6 (output type-checks). |

`openapi-fetch` was **not** added: the client needs its own zod parse, 401 handling and error type
anyway, and a 25-line typed wrapper over the generated `paths` costs 0 KB in the initial bundle
(the budget has 1.3 KB left). `npm audit`: 0 vulnerabilities. Lockfile: all entries from
registry.npmjs.org; the only `hasInstallScript` entry is `fsevents` (optional, from vite; already in Phase 0;
scripts are ignored anyway).

## Lint gates added

- `zod` (full) and `markdown-to-jsx` imports banned in `src/` (except the wrapper).
- `/api/` string or template literals banned outside `src/shared/api` (import specifiers allowed).
- Hex / `rgb()` color literals banned outside the theme CSS.
- Features must not import other features (relative-path regex per folder depth).
- `src/shared/api/openapi.gen.ts` is lint-ignored (generated, 2,900 lines).

## Fixes to Phase 0 files

- `scripts/route-list.ts`: `fullPaths` is a multi-line `| '/a'` union once there are several routes;
  the old one-line regex found 1 route and emitted 0 shells. Now 6 shells for 7 routes.
- `useLocale`: added `getServerSnapshot` (needed by the server-render tests).
- `vite.config.ts` is now a function of `mode`; `vitest.config.ts` calls it.
- Removed the Phase 0 demo home (counter) and demo watchlist rows. The demo chart feature is kept but no route uses it.

## `npm run verify` sizes (gzip)

```
initial    98.9 KB  index
initial    19.8 KB  common   (zod/mini core, query hooks, shared modules, messages)
lazy       27.2 KB  markdown
lazy       19.4 KB  watchlist (table + virtual)
lazy     0.3–1.8 KB each other page
initial JS gzip 118.7 KB (limit 120.0 KB)
CSS gzip         2.5 KB (limit 15.0 KB)
```

**Risk: the initial budget has 1.3 KB left.** Rolldown put modules shared by several lazy routes
(zod/mini schemas code, `QueryState`, messages) into a `common` chunk the entry imports. Next step
before adding pages: inspect `common` (e.g. `rolldown` `advancedChunks` groups so lazy-only shared code
stays lazy) and measure messages size (76 keys x 3 locales now).

## Response shapes I was unsure about (all schemas are permissive)

| Endpoint | Assumption |
|--|--|
| `GET /api/history/{id}` | Array of bar records with open-ended keys (pandas `to_dict('records')`); rendered as a generic table. |
| `GET /api/radar_round/list` | `warnings` is an array of unknown (rendered as text); every meta field nullable/optional. |
| `GET /api/radar_round/{stamp}` | `full` and `packs` are opaque; only `digest_md` and meta are shown. No packs tables yet. |
| `GET /api/radar_round/status` | `error` may be present on failure; `phase`/`message` nullable. |
| `GET /api/stock_radar/history` | `formulas` entries may be strings or objects with `name`. |
| `GET /api/earning_scan/history` | Quarter numbers may be numbers or numeric strings (Alpha Vantage); history newest first. |
| `GET /api/version` | Fields from `VERSION.json` (`version`, `commit`, `build_time`) plus the job fields. |

## Not done / next

- No browser (headless Chrome) pass this phase: CSP/no-violation and the MSW worker in a real tab were not re-measured.
- `check-lockfile` script (Phase 0 note) still open.
- Write actions (POST/PUT/DELETE, CSRF header) are Phase 4.
