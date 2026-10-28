"""FLEX-9 multi-dimension screen, 3 Sep 2026 — register the two result lists as watchlists.

Source: stock-radar audit/20260903/20260903-1530_flex9-multidim-screen-top5-short-top5-medium.md
58 agents screened 38 tickers on TA + earnings + news + macro + micro + sector rotation
+ CEO + moat, then an independent refuter attacked every leader.

  FLEX9-0903-mid    top 5 medium-term (1-6 months), GTC limit entries only
  FLEX9-0903-short  top 5 short-term  (days-weeks) — none cleared the bar outright;
                    each carries a precondition, see the report

Every symbol here is already in dash/src/App.tsx, so no frontend change is needed for
the fetch universe — this only creates the watchlist groupings used by list filtering
and by `load_all.sh LIST_NAME=...`.

Run:  PULL_KEY=xxxx python3 add_symbols_flex9_0903.py
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
    # rank: name, entry level, stop, target — full reasoning lives in the audit report
    "FLEX9-0903-mid": [
        {"symbol": "MRK", "name": "Merck & Co., Inc.", "exchange": "NYSE"},
        {"symbol": "VRTX", "name": "Vertex Pharmaceuticals Incorporated", "exchange": "NASDAQ"},
        {"symbol": "ABBV", "name": "AbbVie Inc.", "exchange": "NYSE"},
        {"symbol": "GLBE", "name": "Global-e Online Ltd.", "exchange": "NASDAQ"},
        {"symbol": "BIIB", "name": "Biogen Inc.", "exchange": "NASDAQ"},
    ],
    "FLEX9-0903-short": [
        {"symbol": "GLBE", "name": "Global-e Online Ltd.", "exchange": "NASDAQ"},
        {"symbol": "AU", "name": "AngloGold Ashanti PLC", "exchange": "NYSE"},
        {"symbol": "HBM", "name": "Hudbay Minerals Inc.", "exchange": "NYSE"},
        {"symbol": "NPK", "name": "National Presto Industries, Inc.", "exchange": "NYSE"},
        {"symbol": "HG", "name": "Hamilton Insurance Group, Ltd.", "exchange": "NYSE"},
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
