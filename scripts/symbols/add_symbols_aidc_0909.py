"""16 AI-datacenter names the radar was blind to, 9 Sep 2026.

Why this list exists
--------------------
On 8 Sep 2026 the AI-datacenter complex ripped and the screen produced ZERO
candidates.  The post-mortem is in

  stock-radar audit/20260909/20260909-0210_why-we-missed-the-ai-rip-gate-audit.md

Checking the 15 requested names against the 502-ticker universe showed
4 were simply absent (CRWV, APLD, IREN, GLW).  Widening the check to the whole
AI-datacenter chain found something worse: the ENTIRE neocloud / GPU-rental lane
was missing - 0 of 10 names present.  That lane is where the move started.

The DCCHAIN-0907 gang does not cover this.  Its brief was explicitly
"out of radar, the company itself still quiet", which by construction selects
names that do NOT move on a day the theme reprices.  This list is the loud
counterpart that was never built.

  AIDC-LOUD-0909   neocloud/GPU rental . optics . power+SMR . servers . towers

Run:  PULL_KEY=xxxx python3 add_symbols_aidc_0909.py
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
    "AIDC-LOUD-0909": [
        # neocloud / GPU rental - the lane that was 0/10 present
        {"symbol": "CRWV", "name": "CoreWeave, Inc.", "exchange": "NASDAQ"},
        {"symbol": "IREN", "name": "IREN Limited", "exchange": "NASDAQ"},
        {"symbol": "APLD", "name": "Applied Digital Corporation", "exchange": "NASDAQ"},
        {"symbol": "CIFR", "name": "Cipher Mining Inc.", "exchange": "NASDAQ"},
        {"symbol": "WULF", "name": "TeraWulf Inc.", "exchange": "NASDAQ"},
        {"symbol": "CORZ", "name": "Core Scientific, Inc.", "exchange": "NASDAQ"},
        {"symbol": "HUT", "name": "Hut 8 Corp.", "exchange": "NASDAQ"},
        {"symbol": "RIOT", "name": "Riot Platforms, Inc.", "exchange": "NASDAQ"},
        {"symbol": "MARA", "name": "MARA Holdings, Inc.", "exchange": "NASDAQ"},
        {"symbol": "GLXY", "name": "Galaxy Digital Inc.", "exchange": "NASDAQ"},
        # optics / interconnect
        {"symbol": "GLW", "name": "Corning Incorporated", "exchange": "NYSE"},
        {"symbol": "POET", "name": "POET Technologies Inc.", "exchange": "NASDAQ"},
        # power / SMR
        {"symbol": "SMR", "name": "NuScale Power Corporation", "exchange": "NYSE"},
        # servers
        {"symbol": "SMCI", "name": "Super Micro Computer, Inc.", "exchange": "NASDAQ"},
        {"symbol": "HPE", "name": "Hewlett Packard Enterprise Company", "exchange": "NYSE"},
        # towers / colo adjacency
        {"symbol": "AMT", "name": "American Tower Corporation", "exchange": "NYSE"},
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
    sys.exit("ERROR: no pull key - set PULL_KEY=xxxx in the environment")


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

    print(f"\ndone - {failed} failure(s)")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
