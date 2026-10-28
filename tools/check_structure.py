#!/usr/bin/env python3
"""Fail when backend Python grows past the size rules (plan §17.1), the way ESLint's
max-lines / max-lines-per-function already guard web/.

  file      <= 300 lines (blank lines and comments count: the file is what you scroll)
  function  <= 60 lines (decorators to last line)
  routes    an `async def` route must await something: FastAPI runs plain `def` routes in a
            threadpool, but blocking calls inside an async route stall the whole event loop
            (fastapi-best-practices, "sync vs async routes")
  config    app code (zservice/, radar_engine/) never reads os.environ / os.getenv: each
            domain declares its variables in a Settings class (zservice/core/config.py)

Exempt, with the reason: radar_engine/lib.py is a verbatim stock-radar copy, and
scripts/legacy/ holds one-off scripts of the old system. Anything else over the limit
fails the commit gate. Run: python3 tools/check_structure.py
"""

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "backend"
MAX_FILE_LINES = 300
MAX_FUNCTION_LINES = 60
SCAN = ("zservice", "radar_engine", "tests", "scripts")
EXEMPT = {
    "radar_engine/lib.py": "verbatim stock-radar copy (sync_lib.sh); never edited here",
}
# One-off scripts of the old system, kept for the record and never run by the app.
EXEMPT_DIRS = ("scripts/legacy/",)
APP_CODE = ("zservice/", "radar_engine/")
_ENV_READS = {"environ", "getenv", "getenvb"}


def _python_files() -> list[Path]:
    files = [p for d in SCAN for p in (ROOT / d).rglob("*.py")]
    files += [p for p in ROOT.glob("*.py")]
    return sorted(p for p in files if "fixtures" not in p.parts)


def check(path: Path) -> list[str]:
    rel = path.relative_to(ROOT).as_posix()
    if rel in EXEMPT or rel.startswith(EXEMPT_DIRS):
        return []
    source = path.read_text(encoding="utf-8")
    problems = []
    lines = source.count("\n") + (0 if source.endswith("\n") else 1)
    if lines > MAX_FILE_LINES:
        problems.append(f"{rel}: {lines} lines > {MAX_FILE_LINES}")
    app_code = rel.startswith(APP_CODE)
    for node in ast.walk(ast.parse(source)):
        if app_code and _reads_env(node):
            problems.append(f"{rel}:{node.lineno} reads the environment; use a Settings class")
        if isinstance(node, ast.AsyncFunctionDef) and _is_route(node) and not _awaits(node):
            problems.append(f"{rel}:{node.lineno} async route {node.name}() never awaits")
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            first = min([node.lineno, *(d.lineno for d in node.decorator_list)])
            size = node.end_lineno - first + 1
            if size > MAX_FUNCTION_LINES:
                problems.append(
                    f"{rel}:{node.lineno} {node.name}() {size} lines > {MAX_FUNCTION_LINES}"
                )
    return problems


def _reads_env(node: ast.AST) -> bool:
    if isinstance(node, ast.Attribute):
        return (
            node.attr in _ENV_READS and isinstance(node.value, ast.Name) and node.value.id == "os"
        )
    if isinstance(node, ast.ImportFrom) and node.module == "os":
        return any(alias.name in _ENV_READS for alias in node.names)
    return False


def _is_route(node: ast.AsyncFunctionDef) -> bool:
    return any("router." in ast.unparse(d) or "app." in ast.unparse(d) for d in node.decorator_list)


def _awaits(node: ast.AsyncFunctionDef) -> bool:
    return any(isinstance(n, (ast.Await, ast.AsyncFor, ast.AsyncWith)) for n in ast.walk(node))


def main() -> int:
    problems = [p for f in _python_files() for p in check(f)]
    for p in problems:
        print(p)
    print(f"check_structure: {len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
