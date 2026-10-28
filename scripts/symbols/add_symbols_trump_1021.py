"""TRUMP-MIDTERM-1021 — 21 names from the two-scenario midterm screen (Trump pivot vs Trump loses House, 21 Oct 2026):
not-rotten FA + currently suppressed + scenario evidence (research: skill-automate/adhoc/runs/20261021-trump-midterm in stock-radar).
All 21 verified on TradingView (daily bars 20 Oct 2026) and Webull (listStatus 1, no PTP). Posts exchange so /api/symbols can include them.
Run:  python3 add_symbols_trump_1021.py
"""
import json, os, re, ssl, sys, urllib.request
API_URL = "https://z-service.duckdns.org/api/watchlist"
LISTS = {
 "TRUMP-MIDTERM-1021": [
  {
   "symbol": "AZN",
   "name": "AstraZeneca PLC",
   "exchange": "NYSE"
  },
  {
   "symbol": "CCL",
   "name": "Carnival Corporation Ltd.",
   "exchange": "NYSE"
  },
  {
   "symbol": "CHRW",
   "name": "C.H. Robinson Worldwide  Inc.",
   "exchange": "NASDAQ"
  },
  {
   "symbol": "CNH",
   "name": "CNH Industrial N.V.",
   "exchange": "NYSE"
  },
  {
   "symbol": "CVS",
   "name": "CVS Health Corporation",
   "exchange": "NYSE"
  },
  {
   "symbol": "DECK",
   "name": "Deckers Outdoor Corporation",
   "exchange": "NYSE"
  },
  {
   "symbol": "EXPE",
   "name": "Expedia Group  Inc.",
   "exchange": "NASDAQ"
  },
  {
   "symbol": "FDX",
   "name": "FedEx Corporation",
   "exchange": "NYSE"
  },
  {
   "symbol": "HD",
   "name": "The Home Depot  Inc.",
   "exchange": "NYSE"
  },
  {
   "symbol": "KNX",
   "name": "Knight-Swift Transportation Holdings Inc.",
   "exchange": "NYSE"
  },
  {
   "symbol": "NXT",
   "name": "Nextpower Inc.",
   "exchange": "NASDAQ"
  },
  {
   "symbol": "ODFL",
   "name": "Old Dominion Freight Line  Inc.",
   "exchange": "NASDAQ"
  },
  {
   "symbol": "ONON",
   "name": "On Holding AG",
   "exchange": "NYSE"
  },
  {
   "symbol": "PJT",
   "name": "PJT Partners Inc.",
   "exchange": "NYSE"
  },
  {
   "symbol": "SAIA",
   "name": "Saia  Inc.",
   "exchange": "NASDAQ"
  },
  {
   "symbol": "TGT",
   "name": "Target Corporation",
   "exchange": "NYSE"
  },
  {
   "symbol": "TJX",
   "name": "The TJX Companies  Inc.",
   "exchange": "NYSE"
  },
  {
   "symbol": "UHS",
   "name": "Universal Health Services  Inc.",
   "exchange": "NYSE"
  },
  {
   "symbol": "ULTA",
   "name": "Ulta Beauty  Inc.",
   "exchange": "NASDAQ"
  },
  {
   "symbol": "URI",
   "name": "United Rentals  Inc.",
   "exchange": "NYSE"
  },
  {
   "symbol": "VIK",
   "name": "Viking Holdings Ltd",
   "exchange": "NYSE"
  }
 ]
}


def pull_key():
    key = os.environ.get("PULL_KEY")
    if key: return key
    here = os.path.dirname(os.path.abspath(__file__)); prior = os.path.join(here, "add_symbols_0811.py")
    if os.path.exists(prior):
        m = re.search(r'PULL_KEY\s*=\s*"([^"]+)"', open(prior).read())
        if m: return m.group(1)
    sys.exit("ERROR: no pull key")

def main():
    key = pull_key(); ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
    headers = {"Content-Type": "application/json", "X-Pull-Key": key, "User-Agent": "Mozilla/5.0"}; failed = 0
    for list_name, symbols in LISTS.items():
        print(f"\n== {list_name} ({len(symbols)} symbols)")
        for item in symbols:
            payload = {"symbol": item["symbol"], "name": item["name"], "exchange": item["exchange"], "list_name": list_name}
            req = urllib.request.Request(f"{API_URL}?pull_key={key}", data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
            try:
                with urllib.request.urlopen(req, context=ctx, timeout=15): print(f"  OK   {item['symbol']}")
            except Exception as exc:
                failed += 1; print(f"  FAIL {item['symbol']}: {exc}")
    print(f"\ndone — {failed} failure(s)"); sys.exit(1 if failed else 0)

if __name__ == "__main__": main()
