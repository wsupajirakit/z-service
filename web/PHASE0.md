# Phase 0: spike and verify (web/)

Date: 2026-10-24. The app lives in `web/` (the old UI is `dash/` = legacy). Nothing outside `web/` was changed.
Every result below lists the command that was run and what it printed.

## Summary

| # | Item | Result |
|--|--|--|
| 1 | Paraglide JS 2 + Vite 8 | ✅ Works. Switching the locale at runtime with no reload works (`setLocale(l, { reload: false })` plus a small store and a `withLocale()` page wrapper). All 3 locales ship in the bundle (about 2.4 KB gzip for 17 keys). See the supply-chain note: plugins are loaded from a CDN by default. |
| 2 | TanStack Table v9 | ✅ Use 9.3.1. Stable since 2026-08-04; 7 open issues since then, 0 labelled bug. Sorting plus react-virtual works on 1,000 rows (20 rows in the DOM). No fallback to 8.x needed. |
| 3 | Router trailing slash | ✅ `createRouter({ trailingSlash: 'always' })`. Links render as `/app/watchlist/`. |
| 4 | Route shells on Starlette | ✅ `/app/` 200 · `/app/watchlist` 307 → `/app/watchlist/` 200 · asset 200 · missing 404 |
| 5 | CSP in headless Chrome | ✅ after one fix. lightweight-charts injects an inline `<style>` for its attribution logo, and CSP blocks it. Fix: `layout.attributionLogo: false` plus our own attribution link. After the fix there are 0 violations. Tailwind works under `style-src 'self'`. |
| 6 | Markdown → React | Recommend **markdown-to-jsx 9.10.3** with `disableParsingRawHTML: true`: 0 dependencies, SLSA provenance, 32 KB gzip. The alternative, react-markdown 10.1.0, has 0 advisories but 81 transitive packages and is 40 KB gzip. |
| 7 | npm audit | `found 0 vulnerabilities`. `npm audit signatures`: 126 packages have verified attestations. Lockfile: 328 entries, all from registry.npmjs.org, 0 git deps, 0 `hasInstallScript`. |

`npm run verify` passes. Initial JS is **108.3 KB gzip** (limit 120). CSS is **2.3 KB gzip** (limit 15). The largest lazy chunk is the chart at 50.7 KB (limit 60).

---

## Setup facts

- `web/.npmrc` was created before the first install: `min-release-age=7`, `allow-git=none`, `ignore-scripts=true`,
  `save-exact=true`, `engine-strict=true`.
- The cooldown works. `npm view vite version` returns 8.3.5, but the install resolved **8.3.4**, because 8.3.5 is newer than 7 days.
  8.3.4 still meets the ≥ 8.3.3 floor. Router 1.170.45 and plugin 1.168.47 are also one patch behind latest for the same reason.
- No package needed an install script. `grep -c '"hasInstallScript": true' package-lock.json` returned 0.
- Local Node is 26.8.1 and npm is 11.19.0. `engines.node` is `>=24.11.0`, so the Docker `node:24-slim` stage is fine.
  Scripts are `.ts` files run directly by Node (native type stripping), so no tsx or ts-node is needed.

### Packages added beyond the brief (and why)

| Package | Why |
|--|--|
| `@inlang/plugin-message-format` 4.5.4 (dev) | Paraglide's default `settings.json` loads its plugins **from jsDelivr at compile time**: remote code that sits outside the lockfile. Installing the plugin from npm and pointing `modules` at `./node_modules/...` keeps the build offline and pinned. |
| `@stylistic/eslint-plugin` 5.10.0 (dev) | Hard 100-column limit (`@stylistic/max-len`). Core `max-len` is deprecated and goes away in ESLint 11. Prettier was not chosen because its `printWidth` is a target, not a limit (strings and comments can exceed it), and it would add a formatter. |
| `@types/react`, `@types/react-dom`, `@types/node`, `@eslint/js`, `globals` (dev) | Type definitions and ESLint flat-config basics, needed by tsc and eslint. |

### Lint gates (fail `verify`)

- `@stylistic/max-len` 100, strings, URLs and comments included. Checked: a 139-character line gives `error This line has a length of 139. Maximum allowed is 100`.
- `max-lines` 300 and `max-lines-per-function` 120 (blank lines and comments skipped).
- `no-restricted-syntax`: bans `dangerouslySetInnerHTML` and `innerHTML`/`outerHTML` assignment.
- `@typescript-eslint/no-explicit-any` set to error.
- `eslint . --max-warnings=0`.

---

## 1. Paraglide JS 2.29.0 with Vite 8.3.4

**Works:** `paraglideVitePlugin(...)` compiles `messages/{th,en,it}.json`. The build log shows `✔ [paraglide-js] Compilation complete (message-modules)`.
`tsc -b` type-checks keys, because a wrong key is a compile error (`emitTsDeclarations: true`).

**Runtime switch without reload.** Measured in headless Chrome with the selftest build (see §5 for the method):

```
"initialLocale":"en"                                  (browser preferred language)
before (after switching to th): intro "แอปทดลองระยะ 0", counter "ตัวนับ (...): 2"
after  (switch to en):    intro "Phase 0 spike app", counter "Counter (...): 2", lang "en", sameDocument: true
afterIt (switch to it):   intro "App prototipo fase 0", nav "HomeLista di osservazioneRiepilogo radar"
```

`sameDocument: true` means a `window` marker survived the switch, so there was no reload. Counter state (2) also survived.

**Caveat found:** `setLocale(l, { reload: false })` plus re-rendering the root is **not enough**. TanStack Router memoizes route matches,
so in the first run the nav switched to Italian but the page text stayed in English. `router.invalidate()` did not help either (measured).
Fix: `src/shared/i18n/withLocale.tsx` wraps each route component (`component: withLocale(Page)`) and subscribes it to the locale store.
The page then re-renders in place and keeps its state. The cost is one wrapper per route. Components under the page re-render normally
(no `memo` and no React Compiler here). Fallback if this ever breaks: `key={locale}` on the router subtree. That remounts, so local state is lost,
but the query cache and the document stay.

**Size per locale:** the default `message-modules` output puts **all locales in every message module**
(`th_x`, `en_x` and `it_x` in one file), so all 3 locales ship. That contradicts the plan's claim that only the chosen locale loads.
Measured: messages plus runtime = 5.7 KB raw / **2.4 KB gzip** for 17 keys × 3 locales.
Raw text per locale: th 527 B (Thai is about 3 bytes/char in UTF-8), en 236 B, it 274 B.
At legacy scale (a few hundred keys) expect roughly 10–15 KB gzip for all three, which fits the 120 KB budget.
Paraglide's per-locale build (`experimentalStaticLocale`) would cut this, but switching would then need a document navigation, so it is not recommended.

**Supply-chain note:** without our change, `paraglide-js compile` imports `https://cdn.jsdelivr.net/npm/@inlang/plugin-message-format@.../dist/index.js` at build time.
Also, a failed plugin import is only a **WARN**: compile still reports success and emits an empty message set.
`tsc -b` catches that, because every `m.*` becomes a type error. `verify` runs `gen:i18n` and then `tsc -b` for this reason.

Strategy: `['localStorage', 'preferredLanguage', 'baseLocale']`, key `app.locale`, base locale `th`, matching plan §7.1.
The options live in one file, `i18n.config.ts`, shared by `vite.config.ts` and `scripts/gen-i18n.ts`.

## 2. TanStack Table 9.3.1 + react-virtual 3.14.21

- Stability, checked on the npm registry and GitHub API: 9.0.0 was released 2026-08-04, followed by 9.0.1 … 9.2.8 and 9.3.1 (2026-10-12).
  `dist-tags.latest` is 9.3.1. `search/issues` returned 7 open issues created since 2026-08-03 and 0 open issues labelled `bug`.
  The latest release notes are patch-level (tree-shaking, `AppCell` typing).
- The v9 API is different from v8. You must register features: `tableFeatures({ rowSortingFeature, sortedRowModel: createSortedRowModel(), sortFns: {...} })`,
  then `useTable({ features, columns, data })` and `<table.FlexRender cell={cell} />`. The package ships agent docs in `node_modules/@tanstack/react-table/skills/`
  (including `migrate-v8-to-v9`). A headless `constructTable` (used in unit tests) needs
  `coreReactivityFeature: storeReactivityBindings()` from `@tanstack/table-core/store-reactivity-bindings`.
  Without it you get `TypeError: Cannot read properties of undefined (reading 'wrapExternalAtoms')`. Seen and fixed.
- Unit test (`src/features/watchlist/model.test.ts`) sorts 1,000 rows by price descending and passes.
- Browser (headless Chrome, `/app/watchlist/`): `rowsInDom: 20` of `"1000 rows"`. Clicking the Price header changed the first cell from `0.08` to `499.92` (desc),
  and a second click changed it back to `0.08` (asc).
- Lint: `react-hooks/incompatible-library` warns on `useVirtualizer` (React Compiler only). It is disabled on that one line with a reason, because there is no compiler here.
- Size: the watchlist route chunk (table + virtual + feature) is 18.9 KB gzip and loads lazily.
- **Decision: use v9.3.1. Do not fall back to 8.x.**

## 3. TanStack Router 1.170.45: trailing slash

- Option: `createRouter({ trailingSlash: 'always' })`. Values are `'always' | 'never' | 'preserve'`, default `'never'`
  (from `router-core/dist/esm/router.d.ts`: "'always' will add a trailing slash if not present").
- Observed in Chrome: nav hrefs are `["/app/","/app/watchlist/","/app/radar-summary/"]`.
- Note: `routeTree.gen.ts` `fullPaths` stay without the slash (`'/watchlist'`). `emit-route-shells` normalizes them.
- `basepath` is set from `import.meta.env.BASE_URL`, which equals `APP_BASE`.

## 4. Route shells on Starlette StaticFiles

The base path comes from env: `APP_BASE`, validated by zod in `build-env.ts` (must match `^/([a-z0-9-]+/)*$`, default `/app/`).
The same value feeds Vite `base`, the router `basepath` (via `BASE_URL`) and `emit-route-shells`.
`APP_API_BASE` (default `/api/`) is injected through `define` and validated again at boot with `zod/mini`.

Setup: `dist/` copied to `<tmp>/static/app/`, a dummy `<tmp>/static/index.html` added, then served with the backend venv
(starlette 1.3.1, uvicorn 0.49.0) using `app.mount('/', StaticFiles(directory=<tmp>/static, html=True))` on a free 127.0.0.1 port.

| Request | Status |
|--|--|
| `/app/` | 200 text/html |
| `/app/watchlist` | **307** → `http://127.0.0.1:<port>/app/watchlist/` |
| `/app/watchlist` (follow, `curl -L`) | 200, 1 hop |
| `/app/watchlist/` | 200 text/html (shell) |
| `/app/radar-summary/` | 200 text/html (shell) |
| `/app/assets/index-<hash>.js` | 200 text/javascript |
| `/app/theme-init.js` | 200 text/javascript |
| `/app/missing/` | 404 text/plain (there is no 404.html at the root) |
| `/app/nope.js` | 404 |
| `/` (legacy) | 200 |

Note: the 307 `Location` is absolute and built from the request scheme and host. Behind Coolify's TLS proxy, uvicorn needs
`--proxy-headers` + `FORWARDED_ALLOW_IPS`, or the redirect goes to `http://`. This is already listed in plan §4.2.
Because links always end in `/`, users only hit the redirect when they type the URL by hand.

## 5. CSP in headless Chrome

Method: Chrome 155 from `/Applications`, `--headless=new --user-data-dir=<fresh mktemp dir in /tmp> --enable-logging=stderr --virtual-time-budget=8000 --dump-dom`,
run against the Starlette server. No existing profile and no remote-debugging port were used.
The page under test was built with `vite build --mode selftest`. `src/app/selftest.ts` is imported only when `MODE === 'selftest'`.
Production `dist/` does not contain it: `grep -l "securitypolicyviolation\|selftest" dist/assets/*.js` returned exit 1.
The probe listens for `securitypolicyviolation`, drives the UI, and writes JSON into `<pre id="selftest">`, which `--dump-dom` captures.

- **First run, `/app/radar-summary/`:** `"violations":["style-src-elem blocked=inline"]`, and the Chrome log shows
  `Applying inline style violates ... 'style-src 'self'' ... source: .../DemoChart-*.js`.
  Cause: lightweight-charts 5.2.1 creates a `<style>` element (CSS for `a#tv-attr-logo`) when `layout.attributionLogo` is true (the default).
  The chart itself still drew (7 canvases).
- **Fix applied:** `createChart(el, { autoSize: true, layout: { attributionLogo: false } })`, plus our own
  "Charting by TradingView" link (message key `chart_attribution`, 3 locales) under the chart.
  This keeps attribution without the inline style. It also avoids the library logo link, which puts the page hostname and path in a `utm_source` query.
- **After fix:** `"violations":[]` on `/app/`, `/app/watchlist/` and `/app/radar-summary/`, and no CSP lines in the Chrome log. Chart: `chartCanvases: 7`.
  Theme switch through `applyOptions`: dark sets body bg `rgb(11, 15, 23)` and light sets `rgb(255, 255, 255)`.
- **Tailwind:** a single external stylesheet (`cssLinks: 1`). `header` computes `display: flex`, so the utility classes apply under `style-src 'self'`.
  React `style={{...}}` (the virtual rows) is set through CSSOM and is not blocked: 0 violations on `/app/watchlist/`.
- `public/theme-init.js` loads synchronously in `<head>` as `<script src="/app/theme-init.js">`, with no inline script.
  Vite prints an informational note ("can't be bundled without type=module"), which is expected for a `public/` file.

## 6. Markdown → React elements (not wired in)

| | markdown-to-jsx | react-markdown | marked-react |
|--|--|--|--|
| Latest (npm) | 9.10.3 (2026-09-15) | 10.1.0 (2025-03-07) | 4.0.0 (2026-03) |
| GitHub advisories | 2, both fixed long ago: GHSA-4wx3-54gh-9fr9 (medium, < 7.4.0), GHSA-ccrp-c664-8p4j (high, < 6.11.4) | 0 | 0 |
| Transitive packages | **0** | 81 (unified/remark/rehype) | 2 (`marked`, `html-entities`) |
| npm provenance | SLSA v1 ✅ | none | — |
| Bundle (Vite lib build, react external) | 110 KB raw / **32.2 KB gzip** | 159 KB / 40.2 KB gzip | 85 KB / 28.5 KB gzip |
| Raw HTML in markdown | parsed into React elements by default → **must set `disableParsingRawHTML: true`** | dropped by default (unless rehype-raw); `urlTransform` blocks `javascript:` by default | — |

**Recommendation: markdown-to-jsx 9.10.3.** It has no dependencies, which matters given the TanStack malware history, and it has provenance and is the smaller of the two mature options.
Wrap it once in `src/shared/lib/markdown.tsx` with `options={{ disableParsingRawHTML: true }}` and a URL sanitizer, and lint-ban direct imports elsewhere.
Lazy-load it only on routes that show AI reports. If the team prefers safe-by-default over dependency count, react-markdown 10.1.0 is the alternative (+8 KB gzip, +81 packages).
Measured in an isolated temp project (same `.npmrc`, 0 install scripts) with `vite build` lib mode.

## 7. npm audit and locked versions

`npm audit` printed `found 0 vulnerabilities`. `npm audit signatures` printed `126 packages have verified attestations`.
Lockfile: 328 `resolved` entries, all `https://registry.npmjs.org`, and 0 others.

| Package | Locked |
|--|--|
| react / react-dom | 19.3.1 |
| vite | 8.3.4 |
| @vitejs/plugin-react | 6.1.2 |
| @tanstack/react-router | 1.170.45 |
| @tanstack/router-plugin | 1.168.47 |
| @tanstack/react-query | 5.104.3 |
| @tanstack/react-table / table-core | 9.3.1 |
| @tanstack/react-virtual | 3.14.21 |
| zod | 4.6.7 |
| tailwindcss / @tailwindcss/vite | 4.3.3 |
| @inlang/paraglide-js | 2.29.0 |
| @inlang/plugin-message-format | 4.5.4 |
| lightweight-charts | 5.2.1 |
| lucide-react | 1.59.0 |
| typescript | 6.0.3 |
| eslint / @eslint/js | 10.13.0 / 10.0.1 |
| typescript-eslint | 8.71.2 |
| eslint-plugin-react-hooks | 7.1.1 |
| @stylistic/eslint-plugin | 5.10.0 |
| vitest | 5.0.5 |
| @types/react / @types/node | 19.3.0 / 24.19.2 |

Still to do (later phase, plan F1): a `check-lockfile` script that fails on git deps and on the known-malware TanStack versions (CVE-2026-45321).

---

## `npm run verify`

`check-i18n → gen:i18n → tsc -b → eslint --max-warnings=0 → vitest → vite build → emit-route-shells → check-budget`
(i18n and generation run first because `tsc -b` needs the generated `src/paraglide/`).

Last run: all steps pass.

```
check-i18n OK: 17 keys x 3 locales
Tests  4 passed (4)
shell /app/radar-summary/ -> dist/radar-summary/index.html
shell /app/watchlist/ -> dist/watchlist/index.html
emit-route-shells: 2 shells for 3 routes
initial     3.3 KB  assets/jsx-runtime-*.js
initial   104.9 KB  assets/index-*.js
lazy       50.7 KB  assets/DemoChart-*.js
lazy       18.9 KB  assets/watchlist-*.js
initial JS gzip 108.3 KB (limit 120.0 KB)
CSS gzip        2.3 KB (limit 15.0 KB)
check-budget OK
```

Negative checks:
- With `nav_home` removed from it.json and `{count}` changed to `{n}`, check-i18n prints `missing "nav_home" in it` and `placeholders differ for "watchlist_rows"` and exits 1.
- A 139-character line fails `@stylistic/max-len`.

**Budget finding:** full `zod` 4 in the entry chunk cost 22.4 KB gzip and pushed initial JS to 126 KB (over budget).
Per-package split: react-dom 64.0, router 24.8, zod 22.4, query-core + react-query 10.4, paraglide 2.4, history 1.9.
Switching the client to **`zod/mini`** brought initial JS to 106–108 KB. Recommendation: the frontend uses `zod/mini` everywhere (`features/*/schemas.ts` too).
Full `zod` stays for Node-side build scripts only.

## Layout

```
web/
├─ .npmrc  package.json  package-lock.json  index.html  PHASE0.md
├─ build-env.ts        # APP_BASE / APP_API_BASE, zod-validated (build side)
├─ i18n.config.ts      # Paraglide options shared by vite + gen-i18n
├─ vite.config.ts  vitest.config.ts  eslint.config.js  tsconfig*.json
├─ project.inlang/settings.json   messages/{th,en,it}.json   public/theme-init.js
├─ scripts/  check-budget.ts  check-i18n.ts  emit-route-shells.ts  gen-i18n.ts  route-list.ts
└─ src/
   ├─ main.tsx  routeTree.gen.ts (generated, commit it)  paraglide/ (generated, gitignored)
   ├─ app/       router.ts  nav.ts (nav from route tree staticData)  routeMeta.ts  queryClient.ts  selftest.ts
   ├─ routes/    __root.tsx  index.tsx  watchlist.tsx  radar-summary.tsx
   ├─ features/  watchlist/{model,columns,components}  chart/{model,chartTheme,components}
   └─ shared/    api/client.ts  config/env.ts  i18n/  theme/  ui/  (lib/ is empty, for markdown later)
```
