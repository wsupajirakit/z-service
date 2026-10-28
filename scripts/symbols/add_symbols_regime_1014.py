"""Regime-rotation gap fill, 14 Oct 2026 — names the radar universe never had, picked for the current tape.

Why: credit risk-off (HYG < 200D ~25 wks) · US10Y 5.29% · CPI Sep hot 3.7% · WTI ~$96 / Brent ~$105 with Hormuz attacks ·
money rotating INTO energy, healthcare, staples, insurers; OUT of credit, small caps, homebuilders. The universe had
0 staples, 0 refiners, 0 tankers and no CVX/COP/EOG, so the screens could not see the rotation.
Every name below was measured on TradingView daily bars (tvDatafeed, 14 Oct 2026): $vol >= $30M, close above a rising
EMA200, and checked against a web news/earnings sweep.
  REGIME-ROTATE-1014 (core: ext200 < 25%, RS120 vs SPY > 0 or a measured catalyst)
  REGIME-WATCH-1014  (watch-only: extended leaders ext200 >= 25% (VLO MPC FRO HUM) — wait for a base, never chase;
                      COST = strongest staples money flow but RS120 < SPY — watch for the turn)

Run:  python3 add_symbols_regime_1014.py
"""

import json
import os
import re
import ssl
import sys
import urllib.request

API_URL = "https://z-service.duckdns.org/api/watchlist"

LISTS = {
    "REGIME-ROTATE-1014": [
        # Energy — defensive integrated / E&P at 52w highs, LNG + gas logistics, product tankers
        {"symbol": "CVX", "name": "Chevron Corporation", "exchange": "NYSE"},
        {"symbol": "COP", "name": "ConocoPhillips", "exchange": "NYSE"},
        {"symbol": "EOG", "name": "EOG Resources, Inc.", "exchange": "NYSE"},
        {"symbol": "LNG", "name": "Cheniere Energy, Inc.", "exchange": "NYSE"},
        {"symbol": "TRGP", "name": "Targa Resources Corp.", "exchange": "NYSE"},
        {"symbol": "STNG", "name": "Scorpio Tankers Inc.", "exchange": "NYSE"},
        # Healthcare — managed care, large-cap biopharma leaders
        {"symbol": "ELV", "name": "Elevance Health, Inc.", "exchange": "NYSE"},
        {"symbol": "AMGN", "name": "Amgen Inc.", "exchange": "NASDAQ"},
        {"symbol": "GILD", "name": "Gilead Sciences, Inc.", "exchange": "NASDAQ"},
        {"symbol": "PFE", "name": "Pfizer Inc.", "exchange": "NYSE"},
        # Insurers — float income from higher yields
        {"symbol": "MET", "name": "MetLife, Inc.", "exchange": "NYSE"},
        {"symbol": "TRV", "name": "The Travelers Companies, Inc.", "exchange": "NYSE"},
        # Staples — pricing power leaders (universe had zero staples)
        {"symbol": "KO", "name": "The Coca-Cola Company", "exchange": "NYSE"},
        {"symbol": "PM", "name": "Philip Morris International Inc.", "exchange": "NYSE"},
        {"symbol": "PG", "name": "The Procter & Gamble Company", "exchange": "NYSE"},
        # Food inflation / government services (Middle East, budgets)
        {"symbol": "ADM", "name": "Archer-Daniels-Midland Company", "exchange": "NYSE"},
        {"symbol": "SAIC", "name": "Science Applications International Corporation", "exchange": "NASDAQ"},
        {"symbol": "CACI", "name": "CACI International Inc", "exchange": "NYSE"},
    ],
    "REGIME-WATCH-1014": [
        {"symbol": "VLO", "name": "Valero Energy Corporation", "exchange": "NYSE"},
        {"symbol": "MPC", "name": "Marathon Petroleum Corporation", "exchange": "NYSE"},
        {"symbol": "FRO", "name": "Frontline plc", "exchange": "NYSE"},
        {"symbol": "HUM", "name": "Humana Inc.", "exchange": "NYSE"},
        {"symbol": "COST", "name": "Costco Wholesale Corporation", "exchange": "NASDAQ"},
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
