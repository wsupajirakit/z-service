"""PHYSICAL-AI-SOP-1022 — 3 names from running the "Inevitable Bottleneck Playbook" SOP on the Physical AI theme (22 Oct 2026):
OII (subsea robots ROV/AUV + mobile robots, 31% of revenue, passes all 3 gates) · GPC (Motion Industries = #1 NA bearings/power-transmission/automation
distribution, 37% of revenue, distribution chokepoint) · ULS (UL 3300 / ISO 13482 robot safety certification, OSHA NRTL = regulatory tollbooth).
Research: stock-radar skill-automate/adhoc/runs/20261022-physical-ai (research_new_names.md, new_names.csv). Verified TradingView + Webull.
Run:  python3 add_symbols_physai_sop_1022.py
"""
import json, os, re, ssl, sys, urllib.request
API_URL = "https://z-service.duckdns.org/api/watchlist"
LISTS = {"PHYSICAL-AI-SOP-1022": [
 {
  "symbol": "GPC",
  "name": "Genuine Parts Company",
  "exchange": "NYSE"
 },
 {
  "symbol": "OII",
  "name": "Oceaneering International  Inc.",
  "exchange": "NYSE"
 },
 {
  "symbol": "ULS",
  "name": "UL Solutions Inc.",
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
