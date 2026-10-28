"""48 symbols the radar was blind to, 8 Sep 2026.

Three groups, all found missing while writing
  stock-radar audit/20260908/20260908-1806_radar-full-premarket-oil-shock-fed-hike-first-session-after-labor-day.md

  SECTOR-ETF-GAPS-0908  XLE/XLP/XLY/XLI/XLK/IYT/XHB/LQD — the screen had NO ETF to
                        measure energy, staples, discretionary, industrials, tech,
                        transports, homebuilders or investment-grade credit. Energy
                        was the #1 macro driver on 8 Sep and we could not read it.
  OUTRADAR-0907         30 out-of-radar bottleneck/backbone/niche names (13 sectors)
  DCCHAIN-0907          10 AI-datacenter supply-chain names (8 lanes)

Both gangs were screened entirely from web data because none of the 40 were in the
443-ticker universe, so every entry/SL in that report is an approximation. This
script closes that gap.

Run:  PULL_KEY=xxxx python3 add_symbols_0908.py
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
    "SECTOR-ETF-GAPS-0908": [
        {"symbol": "XLE", "name": "Energy Select Sector SPDR Fund", "exchange": "AMEX"},
        {"symbol": "XLP", "name": "Consumer Staples Select Sector SPDR Fund", "exchange": "AMEX"},
        {"symbol": "XLY", "name": "Consumer Discretionary Select Sector SPDR Fund", "exchange": "AMEX"},
        {"symbol": "XLI", "name": "Industrial Select Sector SPDR Fund", "exchange": "AMEX"},
        {"symbol": "XLK", "name": "Technology Select Sector SPDR Fund", "exchange": "AMEX"},
        {"symbol": "IYT", "name": "iShares U.S. Transportation ETF", "exchange": "AMEX"},
        {"symbol": "XHB", "name": "SPDR S&P Homebuilders ETF", "exchange": "AMEX"},
        {"symbol": "LQD", "name": "iShares iBoxx $ Investment Grade Corporate Bond ETF", "exchange": "AMEX"},
    ],
    "OUTRADAR-0907": [
        {"symbol": "DOX", "name": "Amdocs Limited", "exchange": "NASDAQ"},
        {"symbol": "TRS", "name": "TriMas Corporation", "exchange": "NASDAQ"},
        {"symbol": "CXT", "name": "Crane NXT, Co.", "exchange": "NYSE"},
        {"symbol": "BCPC", "name": "Balchem Corporation", "exchange": "NASDAQ"},
        {"symbol": "JJSF", "name": "J & J Snack Foods Corp.", "exchange": "NASDAQ"},
        {"symbol": "TBBK", "name": "The Bancorp, Inc.", "exchange": "NASDAQ"},
        {"symbol": "VTOL", "name": "Bristow Group Inc.", "exchange": "NYSE"},
        {"symbol": "EPAC", "name": "Enerpac Tool Group Corp.", "exchange": "NYSE"},
        {"symbol": "HLIO", "name": "Helios Technologies, Inc.", "exchange": "NYSE"},
        {"symbol": "VCYT", "name": "Veracyte, Inc.", "exchange": "NASDAQ"},
        {"symbol": "WTM", "name": "White Mountains Insurance Group, Ltd.", "exchange": "NYSE"},
        {"symbol": "DORM", "name": "Dorman Products, Inc.", "exchange": "NASDAQ"},
        {"symbol": "NTCT", "name": "NetScout Systems, Inc.", "exchange": "NASDAQ"},
        {"symbol": "LMAT", "name": "LeMaitre Vascular, Inc.", "exchange": "NASDAQ"},
        {"symbol": "DSGX", "name": "The Descartes Systems Group Inc.", "exchange": "NASDAQ"},
        {"symbol": "IIIN", "name": "Insteel Industries, Inc.", "exchange": "NASDAQ"},
        {"symbol": "NFG", "name": "National Fuel Gas Company", "exchange": "NYSE"},
        {"symbol": "VERX", "name": "Vertex, Inc.", "exchange": "NASDAQ"},
        {"symbol": "IOSP", "name": "Innospec Inc.", "exchange": "NASDAQ"},
        {"symbol": "MIAX", "name": "Miami International Holdings, Inc.", "exchange": "NYSE"},
        {"symbol": "AIN", "name": "Albany International Corp.", "exchange": "NYSE"},
        {"symbol": "USAC", "name": "USA Compression Partners, LP", "exchange": "NYSE"},
        {"symbol": "OSIS", "name": "OSI Systems, Inc.", "exchange": "NASDAQ"},
        {"symbol": "NPO", "name": "Enpro Inc.", "exchange": "NYSE"},
        {"symbol": "LFUS", "name": "Littelfuse, Inc.", "exchange": "NASDAQ"},
        {"symbol": "SXI", "name": "Standex International Corporation", "exchange": "NYSE"},
        {"symbol": "ICUI", "name": "ICU Medical, Inc.", "exchange": "NASDAQ"},
        {"symbol": "SKYW", "name": "SkyWest, Inc.", "exchange": "NASDAQ"},
        {"symbol": "CTOS", "name": "Custom Truck One Source, Inc.", "exchange": "NYSE"},
        {"symbol": "AIR", "name": "AAR Corp.", "exchange": "NYSE"},
    ],
    "DCCHAIN-0907": [
        {"symbol": "APG", "name": "APi Group Corporation", "exchange": "NYSE"},
        {"symbol": "CMC", "name": "Commercial Metals Company", "exchange": "NYSE"},
        {"symbol": "ATMU", "name": "Atmus Filtration Technologies Inc.", "exchange": "NYSE"},
        {"symbol": "MEC", "name": "Mayville Engineering Company, Inc.", "exchange": "NYSE"},
        {"symbol": "IEX", "name": "IDEX Corporation", "exchange": "NYSE"},
        {"symbol": "GFS", "name": "GlobalFoundries Inc.", "exchange": "NASDAQ"},
        {"symbol": "FTV", "name": "Fortive Corporation", "exchange": "NYSE"},
        {"symbol": "BKH", "name": "Black Hills Corporation", "exchange": "NYSE"},
        {"symbol": "TEX", "name": "Terex Corporation", "exchange": "NYSE"},
        {"symbol": "SWX", "name": "Southwest Gas Holdings, Inc.", "exchange": "NYSE"},
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
