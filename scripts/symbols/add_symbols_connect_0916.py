"""Connectivity, High-Speed Interconnect, Analog/Silicon & Foundational IP, 16 Sep 2026.

Symbols covered:
Group 1 (Networking, Analog, Automotive chips, Silicon materials, Fiber optics):
- ANET: Arista Networks, Inc. (NYSE)
- NXPI: NXP Semiconductors N.V. (NASDAQ)
- ADI: Analog Devices, Inc. (NASDAQ)
- TXN: Texas Instruments Incorporated (NASDAQ)
- ENTG: Entegris, Inc. (NASDAQ)
- GLW: Corning Incorporated (NYSE)

Group 2 (High-speed interconnect, Optical DSP, Retimers & SerDes):
- MTSI: MACOM Technology Solutions Holdings, Inc. (NASDAQ)
- MRVL: Marvell Technology, Inc. (NASDAQ)
- CRDO: Credo Technology Group Holding Ltd (NASDAQ)
- ALAB: Astera Labs, Inc. (NASDAQ)

Group 3 (Digital infrastructure, Wireless/5G & Semiconductor IP licensing):
- VRSN: VeriSign, Inc. (NASDAQ)
- IDCC: InterDigital, Inc. (NASDAQ)
- ADEA: Adeia Inc. (NASDAQ)

Run:  python3 add_symbols_connect_0916.py
"""

import json
import os
import re
import ssl
import sys
import urllib.request

API_URL = "https://z-service.duckdns.org/api/watchlist"

LISTS = {
    "CONNECT-IP-0916": [
        # Group 1: Networking switches, Analog/Auto silicon, Fab materials, Optics
        {"symbol": "ANET", "name": "Arista Networks, Inc.", "exchange": "NYSE"},
        {"symbol": "NXPI", "name": "NXP Semiconductors N.V.", "exchange": "NASDAQ"},
        {"symbol": "ADI", "name": "Analog Devices, Inc.", "exchange": "NASDAQ"},
        {"symbol": "TXN", "name": "Texas Instruments Incorporated", "exchange": "NASDAQ"},
        {"symbol": "ENTG", "name": "Entegris, Inc.", "exchange": "NASDAQ"},
        {"symbol": "GLW", "name": "Corning Incorporated", "exchange": "NYSE"},
        # Group 2: Optical components, DSP, Connectivity, Retimers
        {"symbol": "MTSI", "name": "MACOM Technology Solutions Holdings, Inc.", "exchange": "NASDAQ"},
        {"symbol": "MRVL", "name": "Marvell Technology, Inc.", "exchange": "NASDAQ"},
        {"symbol": "CRDO", "name": "Credo Technology Group Holding Ltd", "exchange": "NASDAQ"},
        {"symbol": "ALAB", "name": "Astera Labs, Inc.", "exchange": "NASDAQ"},
        # Group 3: Core infrastructure, Wireless & Semi IP licensing
        {"symbol": "VRSN", "name": "VeriSign, Inc.", "exchange": "NASDAQ"},
        {"symbol": "IDCC", "name": "InterDigital, Inc.", "exchange": "NASDAQ"},
        {"symbol": "ADEA", "name": "Adeia Inc.", "exchange": "NASDAQ"},
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
