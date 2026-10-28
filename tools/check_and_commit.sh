#!/usr/bin/env bash
# Gate for every commit on this branch: lint, format, structure limits, pytest (plus the
# parity group when radar/export code changed) must pass, otherwise nothing is committed.
#   tools/check_and_commit.sh "<commit message>" [paths to add...]
set -euo pipefail
usage() { sed -n '2,4p' "$0" | sed 's/^# \{0,1\}//'; }
# The first argument is the message: refuse a flag or a blank one, so `--help` (or a
# forgotten message) prints the usage instead of committing.
if [ $# -eq 0 ] || [ -z "${1// /}" ] || [ "${1#-}" != "$1" ]; then
  usage
  exit 2
fi
cd "$(git rev-parse --show-toplevel)"
msg="$1"; shift
backend/venv/bin/ruff check .
backend/venv/bin/ruff format --check .
python3 tools/check_structure.py
python3 tools/check_notes.py
python3 tools/check_private.py
# Default run: every test except the opt-in groups (parity / live / mongo, see tests/conftest.py).
(cd backend && MONGO_URI= nice -n 15 venv/bin/python -m pytest -q)
# Digest parity with stock-radar (~70 s): only when code that can change a radar round moved.
# ZS_REQUIRE_PARITY=1 turns a missing reference set into a failure, not a skip.
parity_paths=(backend/radar_engine backend/zservice/domains/exports
              backend/zservice/domains/radar_rounds backend/tests/radar)
if [ -n "$(git status --porcelain -- "${parity_paths[@]}")" ]; then
  (cd backend && MONGO_URI= ZS_RUN_PARITY=1 ZS_REQUIRE_PARITY=1 OMP_NUM_THREADS=1 \
    nice -n 15 venv/bin/python -m pytest -q -m parity)
fi
# Mongo integration tests run when a local test server is configured (never production).
if [ -n "${ZS_TEST_MONGO_URI:-}" ]; then
  (cd backend && MONGO_URI= nice -n 15 venv/bin/python -m pytest -q -m mongo)
fi
paths=("${@:-backend}")
git add -- "${paths[@]}"
# Commit only these paths, never whatever else happens to be staged (a parallel worker
# may be using the same index).
git commit -q -m "$msg" -- "${paths[@]}"
git push -q
git log --oneline -1
