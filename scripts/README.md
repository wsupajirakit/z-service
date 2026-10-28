# scripts/

Run every script **from the repository root** (they read `dash/src/symbols.ts` and
`backend/main.py` relative to it), e.g. `python3 scripts/symbols/add_symbols_core_1023.py`.

| folder | what | rule |
|--|--|--|
| `symbols/` | add / fix / check symbols and watchlists on the server (one script per batch, dated) | see `docs/ops/ADD_SYMBOLS.md`; the key comes from env `PULL_KEY` (legacy) and moves to `tools/zsvc_client.py` after deploy (runbook §3) |
| `dev/` | local development helpers (`run_dev.py` = backend + legacy dash together; `npm run serv`) | never used by the image |
| `legacy/` | one-off patches and scratch scripts of the old system, kept for the record | not run, not maintained; the structure check exempts them |

Backend one-off scripts (Mongo migration, Drive token minting) live in `backend/scripts/`.
