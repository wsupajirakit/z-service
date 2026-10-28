"""Gaming & Interactive Entertainment ecosystem, 16 Sep 2026 — register as a watchlist.

Symbols covered:
- SONY: Sony Group Corporation (ADR Japan - PlayStation, Studios, Music/Anime IP)
- NTES: NetEase, Inc. (ADR China - Online gaming powerhouse, Global studios)
- TTWO: Take-Two Interactive Software, Inc. (Rockstar Games, 2K, GTA franchise)
- APP: AppLovin Corporation (AdTech engine, Mobile game monetization)
- MSFT: Microsoft Corporation (Xbox, Activision Blizzard, Bethesda, Azure gaming)
- NVDA: NVIDIA Corporation (GeForce GPUs, DLSS, RTX, Cloud gaming)
- TSM: Taiwan Semiconductor Manufacturing (Leading edge silicon foundry)
- QCOM: QUALCOMM Incorporated (Snapdragon mobile gaming silicon)
- GOOGL: Alphabet Inc. (Google Play Store, Android gaming platform)
- MU: Micron Technology, Inc. (GDDR memory, High-speed gaming DRAM)
- AAPL: Apple Inc. (Apple App Store, Apple Arcade, iOS gaming platform)
- AMZN: Amazon.com, Inc. (Twitch streaming, AWS cloud gaming infrastructure)
- AMD: Advanced Micro Devices, Inc. (Console APUs for PS5/Xbox, Radeon GPUs)
- ARM: Arm Holdings plc (Mobile gaming architecture standard)
- SE: Sea Limited (Garena, Free Fire, Southeast Asia gaming & esports)
- AKAM: Akamai Technologies, Inc. (Game patch distribution & edge CDN)
- DLB: Dolby Laboratories, Inc. (Dolby Atmos / Dolby Vision spatial audio in games)
- DELL: Dell Technologies Inc. (Alienware gaming rigs, gaming servers)
- GRVY: Gravity Co., Ltd. (Ragnarok Online franchise & publishing)

Run:  python3 add_symbols_gaming_0916.py
"""

import json
import os
import re
import ssl
import sys
import urllib.request

API_URL = "https://z-service.duckdns.org/api/watchlist"

LISTS = {
    "GAMING-0916": [
        # Game developers & publishers / IP owners
        {"symbol": "TTWO", "name": "Take-Two Interactive Software, Inc.", "exchange": "NASDAQ"},
        {"symbol": "NTES", "name": "NetEase, Inc.", "exchange": "NASDAQ"},
        {"symbol": "SONY", "name": "Sony Group Corporation", "exchange": "NYSE"},
        {"symbol": "GRVY", "name": "Gravity Co., Ltd.", "exchange": "NASDAQ"},
        {"symbol": "SE", "name": "Sea Limited", "exchange": "NYSE"},
        # AdTech / Monetization / Engines
        {"symbol": "APP", "name": "AppLovin Corporation", "exchange": "NASDAQ"},
        # Audio / Distribution / CDN infrastructure
        {"symbol": "DLB", "name": "Dolby Laboratories, Inc.", "exchange": "NYSE"},
        {"symbol": "AKAM", "name": "Akamai Technologies, Inc.", "exchange": "NASDAQ"},
        # Gaming ecosystem / Consoles / Hardware / Cloud
        {"symbol": "MSFT", "name": "Microsoft Corporation", "exchange": "NASDAQ"},
        {"symbol": "AAPL", "name": "Apple Inc.", "exchange": "NASDAQ"},
        {"symbol": "GOOGL", "name": "Alphabet Inc.", "exchange": "NASDAQ"},
        {"symbol": "AMZN", "name": "Amazon.com, Inc.", "exchange": "NASDAQ"},
        {"symbol": "DELL", "name": "Dell Technologies Inc.", "exchange": "NYSE"},
        # Silicon / GPU / Processing / Memory
        {"symbol": "NVDA", "name": "NVIDIA Corporation", "exchange": "NASDAQ"},
        {"symbol": "AMD", "name": "Advanced Micro Devices, Inc.", "exchange": "NASDAQ"},
        {"symbol": "ARM", "name": "Arm Holdings plc", "exchange": "NASDAQ"},
        {"symbol": "QCOM", "name": "QUALCOMM Incorporated", "exchange": "NASDAQ"},
        {"symbol": "TSM", "name": "Taiwan Semiconductor Manufacturing", "exchange": "NYSE"},
        {"symbol": "MU", "name": "Micron Technology, Inc.", "exchange": "NASDAQ"},
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
