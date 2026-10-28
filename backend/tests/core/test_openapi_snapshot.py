"""web/openapi/openapi.json (the source of the web's API types) matches the backend app."""

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]


def test_openapi_snapshot_is_current():
    out = subprocess.run(
        [sys.executable, "tools/export_openapi.py", "--check"],
        cwd=REPO,
        capture_output=True,
        text=True,
    )
    assert out.returncode == 0, (
        f"{out.stdout}{out.stderr}\nrun: backend/venv/bin/python tools/export_openapi.py "
        "&& (cd web && npm run gen:api)"
    )
