"""PHYSICAL-AI-1022 — 6 names from the Physical AI / robotics thesis check (22 Oct 2026): real robotics/automation products outside the 817 universe,
found by a Yahoo industry screen (662 US stocks, 21 robot-BoM industries) + business-description scoring + fact-check agent (research in stock-radar
skill-automate/adhoc/runs/20261022-physical-ai). VPG (force/strain sensors, humanoid nomination) · HSAI (lidar incl. robotics) · PRCT (surgical robot)
· GMED (ExcelsiusGPS robot) · LECO (robotic welding cells) · BDC (industrial automation networking).
All 6 verified on TradingView (daily bars 21 Oct 2026) and Webull (listStatus 1, no PTP). Posts exchange so /api/symbols can include them.
Run:  python3 add_symbols_physai_1022.py
"""
import json, os, re, ssl, sys, urllib.request
API_URL = "https://z-service.duckdns.org/api/watchlist"
LISTS = {"PHYSICAL-AI-1022": [
 {
  "symbol": "BDC",
  "name": "Belden Inc.",
  "exchange": "NYSE"
 },
 {
  "symbol": "GMED",
  "name": "Globus Medical  Inc.",
  "exchange": "NYSE"
 },
 {
  "symbol": "HSAI",
  "name": "Hesai Group",
  "exchange": "NASDAQ"
 },
 {
  "symbol": "LECO",
  "name": "Lincoln Electric Holdings  Inc.",
  "exchange": "NASDAQ"
 },
 {
  "symbol": "PRCT",
  "name": "PROCEPT BioRobotics Corporation",
  "exchange": "NASDAQ"
 },
 {
  "symbol": "VPG",
  "name": "Vishay Precision Group  Inc.",
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
