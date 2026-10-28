#!/usr/bin/env python3
"""Check every pin in the backend locks (image + dev tools) against the OSV advisory database.

No install needed (stdlib only): one POST to https://api.osv.dev/v1/querybatch. Exits 1
when any pinned version has a known advisory, printing the ids and the fixed versions.
npm trees are covered by `npm audit` in web/ and dash/.

    python3 tools/osv_audit.py [path/to/a.lock ...]   (default: both backend locks)
"""

import json
import re
import sys
import urllib.request
from pathlib import Path

OSV = "https://api.osv.dev/v1"
PIN = re.compile(r"^([A-Za-z0-9_.\-]+)==([^\s\\]+)", re.M)


def _post(url: str, body: dict) -> dict:
    req = urllib.request.Request(  # noqa: S310 — fixed https OSV endpoint
        url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=60) as resp:  # noqa: S310
        return json.load(resp)


def _fixed_versions(vuln_id: str) -> list[str]:
    with urllib.request.urlopen(f"{OSV}/vulns/{vuln_id}", timeout=30) as resp:  # noqa: S310
        data = json.load(resp)
    return [
        event["fixed"]
        for affected in data.get("affected", [])
        for rng in affected.get("ranges", [])
        for event in rng.get("events", [])
        if event.get("fixed")
    ]


def main(locks: list[Path]) -> int:
    pins = sorted({pin for lock in locks for pin in PIN.findall(lock.read_text())})
    queries = [{"package": {"name": n, "ecosystem": "PyPI"}, "version": v} for n, v in pins]
    results = _post(f"{OSV}/querybatch", {"queries": queries})["results"]
    hits = [(pins[i], r["vulns"]) for i, r in enumerate(results) if r.get("vulns")]
    print(f"{len(pins)} pinned packages, {len(hits)} with known advisories")
    for (name, version), vulns in hits:
        for vuln in vulns:
            print(f"  {name}=={version}: {vuln['id']} fixed in {_fixed_versions(vuln['id'])}")
    return 1 if hits else 0


if __name__ == "__main__":
    backend = Path(__file__).resolve().parents[1] / "backend"
    defaults = [backend / "requirements.lock", backend / "requirements-dev.lock"]
    sys.exit(main([Path(a) for a in sys.argv[1:]] or defaults))
