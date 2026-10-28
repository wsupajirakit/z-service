"""THESIS-BADNEWS-1022 — 5 new names from the "bad news priced in" thesis (22 Oct 2026): long decline + valuation near 5-year lows
+ real accumulation (Form 4 open-market insider buys / executed buybacks / activist) + 4-year fundamentals never bad (revenue never down, operating
income and FCF positive every year). ROP BR (tech) · COO ZTS FISV (non-tech). Research: stock-radar skill-automate/adhoc/runs/20261022-badnews-priced.
Verified on TradingView (daily bars 21 Oct 2026) and Webull (listStatus 1, no PTP).
Run:  python3 add_symbols_thesis_badnews_1022.py
"""
import json, os, re, ssl, sys, urllib.request
API_URL = "https://z-service.duckdns.org/api/watchlist"
LISTS = {"THESIS-BADNEWS-1022": [
 {
  "symbol": "BR",
  "name": "Broadridge Financial Solutions  Inc.",
  "exchange": "NYSE"
 },
 {
  "symbol": "COO",
  "name": "The Cooper Companies  Inc.",
  "exchange": "NASDAQ"
 },
 {
  "symbol": "FISV",
  "name": "Fiserv  Inc.",
  "exchange": "NASDAQ"
 },
 {
  "symbol": "ROP",
  "name": "Roper Technologies  Inc.",
  "exchange": "NASDAQ"
 },
 {
  "symbol": "ZTS",
  "name": "Zoetis Inc.",
  "exchange": "NYSE"
 }
]}

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
