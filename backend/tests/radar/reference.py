"""The stock-radar reference set the parity tests run against, plus fakes for the two
outside dependencies of a round (radar_engine/rounds/deps.py).

Reference set (produced by stock-radar's run.sh):
    ~/stock-radar/csv_archive/<stamp>/                          the 9 CSV files
    ~/stock-radar/{history,report_archive}/<stamp>/digest.md    the expected digest
A snapshot moves from history/ to report_archive/ when stock-radar archives it, so both
are searched (the fallback lib.read_archive_digest uses). stock-radar keeps raw CSV dirs
for 3 days only, so the newest set with a digest is used unless RADAR_REF_STAMP is set.
"""

import glob
import os
from datetime import timedelta, timezone
from typing import ClassVar

SR = os.environ.get("STOCK_RADAR_DIR", os.path.expanduser("~/stock-radar"))
# The one digest line that legitimately differs: it prints the mtime of the CSV files,
# and ours are freshly written temp copies.
VOLATILE = "newest mtime"
CSV_SET_FILES = 9


def _digest_path(stamp: str) -> str:
    candidates = (
        os.path.join(SR, "history", stamp, "digest.md"),
        os.path.join(SR, "report_archive", stamp, "digest.md"),
    )
    return next((p for p in candidates if os.path.exists(p)), "")


def _pick_stamp() -> str:
    if os.environ.get("RADAR_REF_STAMP"):
        return os.environ["RADAR_REF_STAMP"]
    root = os.path.join(SR, "csv_archive")
    if not os.path.isdir(root):
        return ""
    stamps = sorted(d for d in os.listdir(root) if os.path.isdir(os.path.join(root, d)))
    ready = (
        d
        for d in reversed(stamps)
        if _digest_path(d) and len(os.listdir(os.path.join(root, d))) >= CSV_SET_FILES
    )
    return next(ready, "")


STAMP = _pick_stamp()
REF_CSV = os.path.join(SR, "csv_archive", STAMP) if STAMP else ""
REF_DIGEST = _digest_path(STAMP) if STAMP else ""


def available() -> bool:
    return bool(STAMP) and os.path.isdir(REF_CSV) and os.path.exists(REF_DIGEST)


class FakeApp:
    """The app side of rounds.deps (clock + CSV builders), serving the reference files."""

    # 1W deliberately older than the rest, to exercise the stale-spread warning.
    TS: ClassVar[dict[str, str]] = {
        "1w": "2026-08-12T10:20:00+07:00",
        "1d": "2026-08-12T20:15:00+07:00",
        "4h": "2026-08-12T20:16:00+07:00",
        "1h": "2026-08-12T20:17:00+07:00",
    }

    def current_tz(self):
        return timezone(timedelta(minutes=420))

    def fetch_export_rows(self, interval, list_name=None):
        if not glob.glob(os.path.join(REF_CSV, f"ztrade_export_{interval}_part1*.csv")):
            return []
        # Only `timestamp` is read by the round; the bytes come from the files.
        row = {"timestamp": self.TS[interval], "result_json": "[]", "exchange": "NASDAQ"}
        return [{"symbol": f"S{i}", **row} for i in range(200)]

    def build_export_csv_bytes(self, interval, part=1, list_name=None, rows=None):
        with open(os.path.join(REF_CSV, f"ztrade_export_{interval}_part{part}.csv"), "rb") as f:
            return f.read()

    def build_formula_csv_bytes(self):
        with open(os.path.join(REF_CSV, "ztrade_formula.csv"), "rb") as f:
            return f.read()


class FakeStore:
    """The radar_round_* repo functions a round uses, in memory."""

    def __init__(self, docs: dict | None = None):
        self.docs = dict(docs or {})

    def radar_round_add(self, doc):
        if doc["stamp"] in self.docs:
            raise AssertionError("duplicate stamp inserted")
        self.docs[doc["stamp"]] = dict(doc)
        return doc["stamp"]

    def radar_round_get(self, stamp):
        return self.docs.get(stamp)

    def radar_round_find_fingerprint(self, fingerprint):
        return next((d for d in self.docs.values() if d["fingerprint"] == fingerprint), None)

    def radar_round_delete(self, stamp):
        return self.docs.pop(stamp, None) is not None

    def radar_round_prune(self, keep):
        return []


def digest_lines(text: str) -> list[str]:
    """Comparable digest lines: drop the CSV-mtime line (our copies are fresh) and the
    whole Portfolio section — the server round is computed with port_path=None on purpose,
    so real positions never reach the server."""
    out, skipping = [], False
    for line in text.splitlines():
        if line.startswith("## "):
            skipping = line.startswith("## Portfolio")
        if skipping or VOLATILE in line:
            continue
        out.append(line)
    return out
