#!/usr/bin/env bash
# Re-sync the formula library from stock-radar (the ONLY source of truth).
# Copies the whole file — never patch lib.py by hand, or the two systems drift.
#
#   ./radar_engine/sync_lib.sh              # copy + verify
#   SRC=/other/path/radar_lib.py ./sync_lib.sh
set -euo pipefail

SRC="${SRC:-$HOME/stock-radar/.claude/skills/us-stock-fund-manager/scripts/radar_lib.py}"
DST="$(cd "$(dirname "$0")" && pwd)/lib.py"

[ -f "$SRC" ] || { echo "source not found: $SRC" >&2; exit 1; }

if cmp -s "$SRC" "$DST"; then
    echo "already in sync ($(wc -l < "$DST" | tr -d ' ') lines)"
    exit 0
fi

cp "$SRC" "$DST"
cmp -s "$SRC" "$DST" || { echo "copy verification FAILED" >&2; exit 1; }
echo "synced: $SRC -> $DST  ($(wc -l < "$DST" | tr -d ' ') lines)"
echo "now run:  ZS_RUN_PARITY=1 venv/bin/python -m pytest -m parity   # digest parity check"
