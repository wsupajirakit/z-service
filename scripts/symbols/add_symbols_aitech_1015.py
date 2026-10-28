"""AI / tech value-chain gap fill, 15 Oct 2026 — after a web sweep of next-AI trends and supply-chain bottlenecks.

Finding: the radar universe already covers almost the whole AI chain (GPU/ASIC, HBM/storage, semicap, packaging,
optics, power/cooling, neoclouds). Real gaps were few; speculative AI (quantum, drones, small robotics, space smallcaps)
is in broken downtrends and was NOT added. Measured on TradingView daily bars (tvDatafeed, 14 Oct 2026).
  AI-TECH-1015  (core: above rising EMA200, ext200 < 25%, RS120 vs SPY > 0)
      CSCO  AI networking (Silicon One; Nvidia pluggable-optics partner)  · SAP  enterprise/agentic platform  · U  Unity (AI ads)
  AI-WATCH-1015 (watch-only: extended, too new, or bellwether with a broken trend)
      SKHY SK hynix ADR (HBM leader; Nasdaq since 10 Jul 2026, <200 bars) · NTAP AI storage (ext 41) · SMTC AI copper/optics (ext 29)
      TWLO agentic voice/comms (ext 40) · TSLA physical-AI bellwether (robotaxi; flat trend) · ORCL AI-cloud capex bellwether
      (broken -59% from high, FCF stress) · UMC mature-node foundry · JCI data-center chillers · SEI on-site turbine power

Run:  python3 add_symbols_aitech_1015.py
"""

import json
import os
import re
import ssl
import sys
import urllib.request

API_URL = "https://z-service.duckdns.org/api/watchlist"

LISTS = {
    "AI-TECH-1015": [
        {"symbol": "CSCO", "name": "Cisco Systems, Inc.", "exchange": "NASDAQ"},
        {"symbol": "SAP", "name": "SAP SE", "exchange": "NYSE"},
        {"symbol": "U", "name": "Unity Software Inc.", "exchange": "NYSE"},
    ],
    "AI-WATCH-1015": [
        {"symbol": "SKHY", "name": "SK hynix Inc. (ADR)", "exchange": "NASDAQ"},
        {"symbol": "NTAP", "name": "NetApp, Inc.", "exchange": "NASDAQ"},
        {"symbol": "SMTC", "name": "Semtech Corporation", "exchange": "NASDAQ"},
        {"symbol": "TWLO", "name": "Twilio Inc.", "exchange": "NYSE"},
        {"symbol": "TSLA", "name": "Tesla, Inc.", "exchange": "NASDAQ"},
        {"symbol": "ORCL", "name": "Oracle Corporation", "exchange": "NYSE"},
        {"symbol": "UMC", "name": "United Microelectronics Corporation", "exchange": "NYSE"},
        {"symbol": "JCI", "name": "Johnson Controls International plc", "exchange": "NYSE"},
        {"symbol": "SEI", "name": "Solaris Energy Infrastructure, Inc.", "exchange": "NYSE"},
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
    headers = {"Content-Type": "application/json", "X-Pull-Key": key, "User-Agent": "Mozilla/5.0"}
    failed = 0
    for list_name, symbols in LISTS.items():
        print(f"\n== {list_name} ({len(symbols)} symbols)")
        for item in symbols:
            payload = {"symbol": item["symbol"], "name": item["name"], "exchange": item["exchange"], "list_name": list_name}
            req = urllib.request.Request(f"{API_URL}?pull_key={key}", data=json.dumps(payload).encode("utf-8"),
                                         headers=headers, method="POST")
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
