"""Golden-file helper for characterization tests.

The golden files pin today's behaviour before code moves out of main.py. A test compares
the current value with the stored one; `ZS_UPDATE_GOLDEN=1 pytest ...` rewrites the files
(only do that on purpose, in its own commit, with the reason in the message).
"""

import json
import os
from pathlib import Path

GOLDEN_DIR = Path(__file__).parent / "golden"


def check(name: str, value) -> None:
    path = GOLDEN_DIR / f"{name}.json"
    rendered = json.dumps(value, indent=1, sort_keys=True, ensure_ascii=False) + "\n"
    if os.environ.get("ZS_UPDATE_GOLDEN") == "1":
        GOLDEN_DIR.mkdir(exist_ok=True)
        path.write_text(rendered, encoding="utf-8")
        return
    assert path.exists(), f"missing golden file {path.name}; run with ZS_UPDATE_GOLDEN=1"
    expected = json.loads(path.read_text(encoding="utf-8"))
    assert json.loads(rendered) == expected, f"behaviour changed vs golden/{path.name}"
