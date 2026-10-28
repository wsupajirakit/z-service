"""Cell-therapy 4-name deep dive, 6 Sep 2026 — register as a watchlist.

Source: stock-radar audit/20260906/20260906-2120_biotech-cell-therapy-4-names-fate-iova-autl-nktx.md
None of these 4 were in the 443-ticker universe before this run, so App.tsx got the
frontend entries too (dash/src/App.tsx) — this script only creates the watchlist grouping.

  BIOTECH-CELL-0906   FATE / IOVA / AUTL / NKTX — cell therapy, immune-disease pivot

Run:  PULL_KEY=xxxx python3 add_symbols_biotech_0906.py
      (falls back to the key already stored in add_symbols_0811.py)
"""

import json
import os
import re
import ssl
import sys
import urllib.request

API_URL = "https://z-service.duckdns.org/api/watchlist"

LISTS = {
    "BIOTECH-CELL-0906": [
        {"symbol": "FATE", "name": "Fate Therapeutics, Inc.", "exchange": "NASDAQ"},
        {"symbol": "IOVA", "name": "Iovance Biotherapeutics, Inc.", "exchange": "NASDAQ"},
        {"symbol": "AUTL", "name": "Autolus Therapeutics plc", "exchange": "NASDAQ"},
        {"symbol": "NKTX", "name": "Nkarta, Inc.", "exchange": "NASDAQ"},
    ],
}


def pull_key() -> str:
    key = os.environ.get("PULL_KEY")
    if key:
        return key
    here = os.path.dirname(os.path.abspath(__file__))
    prior = os.path.join(here, "add_symbols_0811.py")
    if os.path.exists(prior):
        m = re.search(r'PULL_KEY\s*=\s*"([^"]+)"', open(prior).read())
        if m:
            return m.group(1)
    sys.exit("ERROR: no pull key — set PULL_KEY=xxxx in the environment")


def main() -> None:
    key = pull_key()
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    headers = {
        "Content-Type": "application/json",
        "X-Pull-Key": key,
        "User-Agent": "Mozilla/5.0",
    }

    failed = 0
    for list_name, symbols in LISTS.items():
        print(f"\n== {list_name} ({len(symbols)} symbols)")
        for item in symbols:
            payload = {
                "symbol": item["symbol"],
                "name": item["name"],
                "exchange": item["exchange"],
                "list_name": list_name,
            }
            req = urllib.request.Request(
                f"{API_URL}?pull_key={key}",
                data=json.dumps(payload).encode("utf-8"),
                headers=headers,
                method="POST",
            )
            try:
                with urllib.request.urlopen(req, context=ctx, timeout=15):
                    print(f"  OK   {item['symbol']}")
            except Exception as exc:  # noqa: BLE001 - report and keep going
                failed += 1
                print(f"  FAIL {item['symbol']}: {exc}")

    print(f"\ndone — {failed} failure(s)")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
