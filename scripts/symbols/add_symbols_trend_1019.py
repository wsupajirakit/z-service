"""Global megatrends (what the world is short of) — gap fill, 19 Oct 2026.

Researched demand evidence (web, Oct 2026) then filled only the value-chain names missing from App.tsx:
  TREND-POWER-1019    SO D XEL PEG EXC PCG EIX FSLR AYI DY CARR   AI power: data-centre electricity 485 TWh (2025) -> ~950 TWh 2030 (IEA);
                                                                   US demand +2%/yr, half from data centres; transformers 2-3y lead time, ~30% short
  TREND-WATER-1019    AWK WTRG ECL VLTO PNR WTS FELE BMI ITT       AI/fab water + aging pipes; Xylem raised 2026 on data-centre demand; Ecolab buys CoolIT
  TREND-FOOD-1019     NTR CF MOS CTVA AGCO LNN                     Gulf = 35-40% of traded urea; Hormuz cut exports; CF sees nitrogen tight into 2027
  TREND-LNG-1019      VG EXE BKR HAL                               Qatar (~20% of LNG) offline since March, repairs 3-5 years; US exporters at max capacity
  TREND-AGING-1019    WELL VTR VKTX HIMS                           boomers turn 80 from 2026; senior-housing starts -73% vs 2021; Welltower SHOP NOI +20%
  TREND-MINERALS-1019 SCCO TECK SQM LAC USAR                       copper mine growth 1.6% vs AI/EV demand; China rare-earth pause ends 27 Nov 2026
  TREND-DEFENSE-1019  LDOS BAH ESLT KRMN TXT BA                    NATO 5% of GDP by 2035; European orders ~2x deliveries (backlogs growing)
  TREND-SPACE-1019    VSAT LUNR
  TREND-INDIA-1019    IBN HDB INFY MMYT RDY                        India GDP +7% 2026-27 (IMF Oct 2026), record FDI, China+1
Measured on 10y daily bars: only ECL VLTO WTS CTVA WELL SCCO TECK pass the trend gate (above rising EMA200, ext200 < 25%,
RS120 > 0, $vol >= $30M); the rest are watch-only. Dropped CQP (illiquid, LNG already tracked), WIT (illiquid), SATS (delisted).
All 52 verified on TradingView 16 Oct 2026.

Run:  python3 add_symbols_trend_1019.py
"""

import json
import os
import re
import ssl
import sys
import urllib.request

API_URL = "https://z-service.duckdns.org/api/watchlist"

LISTS = {
    "TREND-POWER-1019": [
        {"symbol": "SO", "name": "The Southern Company", "exchange": "NYSE"},
        {"symbol": "D", "name": "Dominion Energy, Inc.", "exchange": "NYSE"},
        {"symbol": "XEL", "name": "Xcel Energy Inc.", "exchange": "NASDAQ"},
        {"symbol": "PEG", "name": "Public Service Enterprise Group Incorporated", "exchange": "NYSE"},
        {"symbol": "EXC", "name": "Exelon Corporation", "exchange": "NASDAQ"},
        {"symbol": "PCG", "name": "PG&E Corporation", "exchange": "NYSE"},
        {"symbol": "EIX", "name": "Edison International", "exchange": "NYSE"},
        {"symbol": "FSLR", "name": "First Solar, Inc.", "exchange": "NASDAQ"},
        {"symbol": "AYI", "name": "Acuity Inc.", "exchange": "NYSE"},
        {"symbol": "DY", "name": "Dycom Industries, Inc.", "exchange": "NYSE"},
        {"symbol": "CARR", "name": "Carrier Global Corporation", "exchange": "NYSE"},
    ],
    "TREND-WATER-1019": [
        {"symbol": "AWK", "name": "American Water Works Company, Inc.", "exchange": "NYSE"},
        {"symbol": "WTRG", "name": "Essential Utilities, Inc.", "exchange": "NYSE"},
        {"symbol": "ECL", "name": "Ecolab Inc.", "exchange": "NYSE"},
        {"symbol": "VLTO", "name": "Veralto Corporation", "exchange": "NYSE"},
        {"symbol": "PNR", "name": "Pentair plc", "exchange": "NYSE"},
        {"symbol": "WTS", "name": "Watts Water Technologies, Inc.", "exchange": "NYSE"},
        {"symbol": "FELE", "name": "Franklin Electric Co., Inc.", "exchange": "NASDAQ"},
        {"symbol": "BMI", "name": "Badger Meter, Inc.", "exchange": "NYSE"},
        {"symbol": "ITT", "name": "ITT Inc.", "exchange": "NYSE"},
    ],
    "TREND-FOOD-1019": [
        {"symbol": "NTR", "name": "Nutrien Ltd.", "exchange": "NYSE"},
        {"symbol": "CF", "name": "CF Industries Holdings, Inc.", "exchange": "NYSE"},
        {"symbol": "MOS", "name": "The Mosaic Company", "exchange": "NYSE"},
        {"symbol": "CTVA", "name": "Corteva, Inc.", "exchange": "NYSE"},
        {"symbol": "AGCO", "name": "AGCO Corporation", "exchange": "NYSE"},
        {"symbol": "LNN", "name": "Lindsay Corporation", "exchange": "NYSE"},
    ],
    "TREND-LNG-1019": [
        {"symbol": "VG", "name": "Venture Global, Inc.", "exchange": "NYSE"},
        {"symbol": "EXE", "name": "Expand Energy Corporation", "exchange": "NASDAQ"},
        {"symbol": "BKR", "name": "Baker Hughes Company", "exchange": "NASDAQ"},
        {"symbol": "HAL", "name": "Halliburton Company", "exchange": "NYSE"},
    ],
    "TREND-AGING-1019": [
        {"symbol": "WELL", "name": "Welltower Inc.", "exchange": "NYSE"},
        {"symbol": "VTR", "name": "Ventas, Inc.", "exchange": "NYSE"},
        {"symbol": "VKTX", "name": "Viking Therapeutics, Inc.", "exchange": "NASDAQ"},
        {"symbol": "HIMS", "name": "Hims & Hers Health, Inc.", "exchange": "NYSE"},
    ],
    "TREND-MINERALS-1019": [
        {"symbol": "SCCO", "name": "Southern Copper Corporation", "exchange": "NYSE"},
        {"symbol": "TECK", "name": "Teck Resources Limited", "exchange": "NYSE"},
        {"symbol": "SQM", "name": "Sociedad Química y Minera de Chile S.A.", "exchange": "NYSE"},
        {"symbol": "LAC", "name": "Lithium Americas Corp.", "exchange": "NYSE"},
        {"symbol": "USAR", "name": "USA Rare Earth, Inc.", "exchange": "NASDAQ"},
    ],
    "TREND-DEFENSE-1019": [
        {"symbol": "LDOS", "name": "Leidos Holdings, Inc.", "exchange": "NYSE"},
        {"symbol": "BAH", "name": "Booz Allen Hamilton Holding Corporation", "exchange": "NYSE"},
        {"symbol": "ESLT", "name": "Elbit Systems Ltd.", "exchange": "NASDAQ"},
        {"symbol": "KRMN", "name": "Karman Holdings Inc.", "exchange": "NYSE"},
        {"symbol": "TXT", "name": "Textron Inc.", "exchange": "NYSE"},
        {"symbol": "BA", "name": "The Boeing Company", "exchange": "NYSE"},
    ],
    "TREND-SPACE-1019": [
        {"symbol": "VSAT", "name": "Viasat, Inc.", "exchange": "NASDAQ"},
        {"symbol": "LUNR", "name": "Intuitive Machines, Inc.", "exchange": "NASDAQ"},
    ],
    "TREND-INDIA-1019": [
        {"symbol": "IBN", "name": "ICICI Bank Limited", "exchange": "NYSE"},
        {"symbol": "HDB", "name": "HDFC Bank Limited", "exchange": "NYSE"},
        {"symbol": "INFY", "name": "Infosys Limited", "exchange": "NYSE"},
        {"symbol": "MMYT", "name": "MakeMyTrip Limited", "exchange": "NASDAQ"},
        {"symbol": "RDY", "name": "Dr. Reddy’s Laboratories Limited", "exchange": "NYSE"},
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
