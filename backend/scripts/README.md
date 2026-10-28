# backend/scripts

Operator tools that are **not** part of the running service (the Docker image copies only
`backend/*.py`, `zservice/` and `radar_engine/`, so nothing here ships).

| file | use |
|--|--|
| `mint_drive_token.py` | mint a new Google Drive OAuth refresh token (`cd backend && venv/bin/python scripts/mint_drive_token.py`) |
| `legacy/` | SQLite-era one-offs and scratch probes kept for history: `migrate_sqlite_to_mongo.py`, `migrate_db.py`, `inspect_db.py`, `analyze.py`, `test_failed.py`, `test_retry.py`. Not maintained; may need paths adjusted before use. |
