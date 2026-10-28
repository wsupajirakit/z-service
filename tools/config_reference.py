#!/usr/bin/env python3
"""Write docs/config-reference.md from the backend Settings classes (--check: fail when the
file is stale instead). Run with the backend venv: backend/venv/bin/python tools/config_reference.py
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "config-reference.md"
sys.path.insert(0, str(ROOT / "backend"))

from zservice import bootstrap  # noqa: E402

bootstrap.load_env = lambda: None  # the reference lists defaults, never local values

from zservice.core import config_docs  # noqa: E402


def main() -> int:
    text = config_docs.render(config_docs.discover())
    if "--check" in sys.argv:
        stale = not DOC.exists() or DOC.read_text(encoding="utf-8") != text
        print(f"{DOC.relative_to(ROOT)}: {'stale' if stale else 'current'}")
        return 1 if stale else 0
    DOC.write_text(text, encoding="utf-8")
    print(f"wrote {DOC.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
