# web/src — project structure

Feature-based layout after [bulletproof-react](https://github.com/alan2207/bulletproof-react/blob/master/docs/project-structure.md),
with imports flowing one way: **shared → features → app** (enforced by `eslint.config.js`).

```
src/
├─ app/          application layer: router, query client, nav (from route staticData), route tree
├─ pages/        route views — TanStack file routes (thin: pick a feature page, set nav/title)
├─ layouts/      page shells: RootLayout, sidebar (desktop) / drawer (mobile), headers, user menu
├─ features/     one folder per feature: api.ts · schemas.ts · model.ts · components/ · index.ts
│                (a feature imports shared code and itself, never another feature)
├─ components/   shared UI: ui/ (shadcn-style primitives: card, data table, dialogs, toasts,
│                menu, tabs, switch, form classes, icons), chart/, MarkdownText
├─ hooks/        shared hooks: useLocale, useFormat, useTheme, useDocumentTitle
├─ services/     backend access: api/ (typed client, CSRF, error + server-text translation), auth/
├─ stores/       global client state: locale, theme, sidebar, toasts (server state lives in
│                TanStack Query)
├─ i18n/         translation helpers: title keys, status-enum labels, withLocale
├─ styles/       global CSS and theme tokens (CSS variables)
├─ utils/        pure helpers: formatting, validation, search, symbol lists, table logic, cookies
├─ config/       app tunables and build env (no literals in components)
├─ testing/      MSW mocks, fixtures and render helpers for tests and `npm run dev:mock`
├─ paraglide/    generated from messages/*.json (never edited)
└─ main.tsx      entry: theme, locale, router
```

Not present on purpose: `contexts/` (no React Context — server state is TanStack Query, client
state is a few tiny stores) and `assets/` (no static files bundled from src; `public/` holds
`theme-init.js`). Add them when there is real content, not as empty folders.

Size limits (ESLint): files ≤ 300 lines, functions/components ≤ 80 lines, lines ≤ 100 chars.
