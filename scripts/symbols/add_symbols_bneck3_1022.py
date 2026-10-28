"""BNECK-3THEMES-1022 — 22 names from running the Inevitable Bottleneck Playbook on 3 themes (22 Oct 2026):
Energy & grid (TRP FTS ENB SOLS INIO KNTK AM OKE ACA) · Memory/HBM parts (ESI ACMR) · Financial tollbooths (VRSK EFX TRU FICO MORN SSNC JKHY FDS SEIC RELX FIS).
All pass SOP >=2/3 (research: stock-radar skill-automate/adhoc/runs/20261022-bneck-3themes), verified on TradingView (daily bars 22 Oct 2026, 20-day $vol >= $10M)
and Webull (listStatus 1, no PTP). Posts exchange so /api/symbols can include them.
Run:  python3 add_symbols_bneck3_1022.py
"""
import json, os, re, ssl, sys, urllib.request
API_URL = "https://z-service.duckdns.org/api/watchlist"
LISTS = {"BNECK-3THEMES-1022": [
 {
  "symbol": "ACA",
  "name": "Arcosa Inc",
  "exchange": "NYSE"
 },
 {
  "symbol": "ACMR",
  "name": "Acm Research",
  "exchange": "NASDAQ"
 },
 {
  "symbol": "AM",
  "name": "Antero Midstream Corp",
  "exchange": "NYSE"
 },
 {
  "symbol": "EFX",
  "name": "Equifax Inc",
  "exchange": "NYSE"
 },
 {
  "symbol": "ENB",
  "name": "Enbridge",
  "exchange": "NYSE"
 },
 {
  "symbol": "ESI",
  "name": "Element Solutions Inc",
  "exchange": "NYSE"
 },
 {
  "symbol": "FDS",
  "name": "Factset Resh Sys Inc",
  "exchange": "NYSE"
 },
 {
  "symbol": "FICO",
  "name": "Fair Isaac Corp",
  "exchange": "NYSE"
 },
 {
  "symbol": "FIS",
  "name": "Fidelity Natl Information Svcs",
  "exchange": "NYSE"
 },
 {
  "symbol": "FTS",
  "name": "Fortis",
  "exchange": "NYSE"
 },
 {
  "symbol": "INIO",
  "name": "INNIO Holding GmBH",
  "exchange": "NASDAQ"
 },
 {
  "symbol": "JKHY",
  "name": "Jack Henry & Associates",
  "exchange": "NASDAQ"
 },
 {
  "symbol": "KNTK",
  "name": "Kinetik Holdings Inc",
  "exchange": "NYSE"
 },
 {
  "symbol": "MORN",
  "name": "Morningstar",
  "exchange": "NASDAQ"
 },
 {
  "symbol": "OKE",
  "name": "Oneok Inc",
  "exchange": "NYSE"
 },
 {
  "symbol": "RELX",
  "name": "Relx Plc",
  "exchange": "NYSE"
 },
 {
  "symbol": "SEIC",
  "name": "Sei Invts Co",
  "exchange": "NASDAQ"
 },
 {
  "symbol": "SOLS",
  "name": "SOLSTICE ADVANCED MATLS INC",
  "exchange": "NASDAQ"
 },
 {
  "symbol": "SSNC",
  "name": "Ss&C Technologies",
  "exchange": "NASDAQ"
 },
 {
  "symbol": "TRP",
  "name": "Tc Energy Corporation",
  "exchange": "NYSE"
 },
 {
  "symbol": "TRU",
  "name": "TransUnion",
  "exchange": "NYSE"
 },
 {
  "symbol": "VRSK",
  "name": "Verisk Analytics",
  "exchange": "NASDAQ"
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
