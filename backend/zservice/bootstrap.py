"""Process start-up steps that must run in a fixed order (moved from the top of main.py).

1. load_env()       — before any Settings class (zservice/core/config.py) reads the env
2. connect_store()  — Mongo ping + indexes, printed for the container log
3. start_tradingview() — library tuning + login warm-up + auth-mode report
"""

import os
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]


def load_env() -> None:
    """Load the repo-root .env.local / .env for development. On Coolify the env vars are
    injected into the process and load_dotenv never overrides them, so this is a no-op
    there. Without python-dotenv we rely on the real environment."""
    try:
        from dotenv import load_dotenv
    except Exception:
        return
    root = BACKEND_DIR / ".."
    load_dotenv(os.path.join(root, ".env.local"))  # local dev secrets (MONGO_URI, ...)
    load_dotenv(os.path.join(root, ".env"))


def connect_store() -> None:
    """Persistence is MongoDB Atlas; every DB call goes through zservice.db."""
    from zservice.db import client as db_client

    try:
        db_client.ping()
        db_client.ensure_indexes()
        print("[Startup] MongoDB connected")
    except Exception as e:
        print(f"[Startup] MongoDB connection FAILED: {e}")


def start_tradingview() -> None:
    from zservice.integrations.tradingview import client

    client.configure_library()
    client.warm_up_and_report()
