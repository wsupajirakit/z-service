"""WL19-NEXT-TREND-1020 — 25 names that were NEVER in the csv universe (20 Oct 2026): next-trend / hidden gems, tech + non-tech,
chosen on FA + real products + earnings record + CEO/insiders + tailwind/story + chart (research: skill-automate/adhoc/runs/20261020-wl19-research in stock-radar).
  ✅ ATI CLH EXLS PAY PGY WAY CVSA RDNT YPF AIT ALRM DXPE EMBJ G NU   🟡 INTA PDFS WIX BAP DOCS DOV UI CLOV DIOD HXL
All 25 verified on TradingView (daily bars 20 Oct 2026) and Webull (listStatus 1, no PTP). Posts exchange so /api/symbols can include them.
Run:  python3 add_symbols_wl19_1020.py
"""
import json, os, re, ssl, sys, urllib.request
API_URL = "https://z-service.duckdns.org/api/watchlist"
LISTS = {"WL19-NEXT-TREND-1020": [
    {"symbol": "ATI", "name": "ATI Inc.", "exchange": "NYSE"},
    {"symbol": "CLH", "name": "Clean Harbors  Inc.", "exchange": "NYSE"},
    {"symbol": "EXLS", "name": "ExlService Holdings  Inc.", "exchange": "NASDAQ"},
    {"symbol": "PAY", "name": "Paymentus Holdings  Inc.", "exchange": "NYSE"},
    {"symbol": "PGY", "name": "Pagaya Technologies Ltd.", "exchange": "NASDAQ"},
    {"symbol": "WAY", "name": "Waystar Holding Corp.", "exchange": "NASDAQ"},
    {"symbol": "CVSA", "name": "Covista Inc.", "exchange": "NYSE"},
    {"symbol": "INTA", "name": "Intapp  Inc.", "exchange": "NASDAQ"},
    {"symbol": "RDNT", "name": "RadNet  Inc.", "exchange": "NASDAQ"},
    {"symbol": "YPF", "name": "YPF Sociedad Anónima", "exchange": "NYSE"},
    {"symbol": "AIT", "name": "Applied Industrial Technologies  Inc.", "exchange": "NYSE"},
    {"symbol": "ALRM", "name": "Alarm.com Holdings  Inc.", "exchange": "NASDAQ"},
    {"symbol": "DXPE", "name": "DXP Enterprises  Inc.", "exchange": "NASDAQ"},
    {"symbol": "EMBJ", "name": "Embraer S.A.", "exchange": "NYSE"},
    {"symbol": "G", "name": "Genpact Limited", "exchange": "NYSE"},
    {"symbol": "NU", "name": "Nu Holdings Ltd.", "exchange": "NYSE"},
    {"symbol": "PDFS", "name": "PDF Solutions  Inc.", "exchange": "NASDAQ"},
    {"symbol": "WIX", "name": "Wix.com Ltd.", "exchange": "NASDAQ"},
    {"symbol": "BAP", "name": "Credicorp Ltd.", "exchange": "NYSE"},
    {"symbol": "DOCS", "name": "Doximity  Inc.", "exchange": "NYSE"},
    {"symbol": "DOV", "name": "Dover Corporation", "exchange": "NYSE"},
    {"symbol": "UI", "name": "Ubiquiti Inc.", "exchange": "NYSE"},
    {"symbol": "CLOV", "name": "Clover Health Investments  Corp.", "exchange": "NASDAQ"},
    {"symbol": "DIOD", "name": "Diodes Incorporated", "exchange": "NASDAQ"},
    {"symbol": "HXL", "name": "Hexcel Corporation", "exchange": "NYSE"},
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
