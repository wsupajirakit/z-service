"""FOCUS-GROUPS-1021 — 49 names for focus_list groups space/techpart/finance (21 Oct 2026): next-trend / hidden gems, tech + non-tech,
chosen on FA + real products + earnings record + CEO/insiders + tailwind/story + chart (research: skill-automate/adhoc/runs/20261020-wl19-research in stock-radar).
  ✅ ATI CLH EXLS PAY PGY WAY CVSA RDNT YPF AIT ALRM DXPE EMBJ G NU   🟡 INTA PDFS WIX BAP DOCS DOV UI CLOV DIOD HXL
All 25 verified on TradingView (daily bars 20 Oct 2026) and Webull (listStatus 1, no PTP). Posts exchange so /api/symbols can include them.
Run:  python3 add_symbols_wl19_1020.py
"""
import json, os, re, ssl, sys, urllib.request
API_URL = "https://z-service.duckdns.org/api/watchlist"
LISTS = {"FOCUS-GROUPS-1021": [
    {"symbol": "RCAT", "name": "Red Cat Holdings  Inc.", "exchange": "NASDAQ"},
    {"symbol": "ONDS", "name": "Ondas Inc.", "exchange": "NASDAQ"},
    {"symbol": "UMAC", "name": "Unusual Machines  Inc.", "exchange": "AMEX"},
    {"symbol": "VOYG", "name": "Voyager Technologies  Inc.", "exchange": "NYSE"},
    {"symbol": "FLY", "name": "Firefly Aerospace Inc.", "exchange": "NASDAQ"},
    {"symbol": "ECHO", "name": "EchoStar Corporation", "exchange": "NASDAQ"},
    {"symbol": "VSEC", "name": "VSE Corporation", "exchange": "NASDAQ"},
    {"symbol": "CDRE", "name": "Cadre Holdings  Inc.", "exchange": "NYSE"},
    {"symbol": "HIMX", "name": "Himax Technologies  Inc.", "exchange": "NASDAQ"},
    {"symbol": "INDI", "name": "indie Semiconductor  Inc.", "exchange": "NASDAQ"},
    {"symbol": "CEVA", "name": "CEVA  Inc.", "exchange": "NASDAQ"},
    {"symbol": "KOPN", "name": "Kopin Corporation", "exchange": "NASDAQ"},
    {"symbol": "NVEC", "name": "NVE Corporation", "exchange": "NASDAQ"},
    {"symbol": "MA", "name": "Mastercard Incorporated", "exchange": "NYSE"},
    {"symbol": "ICE", "name": "Intercontinental Exchange  Inc.", "exchange": "NYSE"},
    {"symbol": "CBOE", "name": "Cboe Global Markets  Inc.", "exchange": "CBOE"},
    {"symbol": "MSCI", "name": "MSCI Inc.", "exchange": "NYSE"},
    {"symbol": "BLK", "name": "BlackRock  Inc.", "exchange": "NYSE"},
    {"symbol": "TROW", "name": "T. Rowe Price Group  Inc.", "exchange": "NASDAQ"},
    {"symbol": "AMP", "name": "Ameriprise Financial  Inc.", "exchange": "NYSE"},
    {"symbol": "RJF", "name": "Raymond James Financial  Inc.", "exchange": "NYSE"},
    {"symbol": "LPLA", "name": "LPL Financial Holdings Inc.", "exchange": "NASDAQ"},
    {"symbol": "EVR", "name": "Evercore Inc.", "exchange": "NYSE"},
    {"symbol": "HLI", "name": "Houlihan Lokey  Inc.", "exchange": "NYSE"},
    {"symbol": "OWL", "name": "Blue Owl Capital Inc.", "exchange": "NYSE"},
    {"symbol": "CG", "name": "The Carlyle Group Inc.", "exchange": "NASDAQ"},
    {"symbol": "TPG", "name": "TPG Inc.", "exchange": "NASDAQ"},
    {"symbol": "BAM", "name": "Brookfield Asset Management Ltd.", "exchange": "NYSE"},
    {"symbol": "ALL", "name": "The Allstate Corporation", "exchange": "NYSE"},
    {"symbol": "AIG", "name": "American International Group  Inc.", "exchange": "NYSE"},
    {"symbol": "HIG", "name": "The Hartford Insurance Group  Inc.", "exchange": "NYSE"},
    {"symbol": "WRB", "name": "W. R. Berkley Corporation", "exchange": "NYSE"},
    {"symbol": "CINF", "name": "Cincinnati Financial Corporation", "exchange": "NASDAQ"},
    {"symbol": "AFL", "name": "Aflac Incorporated", "exchange": "NYSE"},
    {"symbol": "PRU", "name": "Prudential Financial  Inc.", "exchange": "NYSE"},
    {"symbol": "PNC", "name": "The PNC Financial Services Group  Inc.", "exchange": "NYSE"},
    {"symbol": "USB", "name": "U.S. Bancorp", "exchange": "NYSE"},
    {"symbol": "TFC", "name": "Truist Financial Corporation", "exchange": "NYSE"},
    {"symbol": "MTB", "name": "M&T Bank Corporation", "exchange": "NYSE"},
    {"symbol": "HBAN", "name": "Huntington Bancshares Incorporated", "exchange": "NASDAQ"},
    {"symbol": "RF", "name": "Regions Financial Corporation", "exchange": "NYSE"},
    {"symbol": "KEY", "name": "KeyCorp", "exchange": "NYSE"},
    {"symbol": "CFG", "name": "Citizens Financial Group  Inc.", "exchange": "NYSE"},
    {"symbol": "COF", "name": "Capital One Financial Corporation", "exchange": "NYSE"},
    {"symbol": "PYPL", "name": "PayPal Holdings  Inc.", "exchange": "NASDAQ"},
    {"symbol": "AFRM", "name": "Affirm Holdings  Inc.", "exchange": "NASDAQ"},
    {"symbol": "TW", "name": "Tradeweb Markets Inc.", "exchange": "NASDAQ"},
    {"symbol": "MKTX", "name": "MarketAxess Holdings Inc.", "exchange": "NASDAQ"},
    {"symbol": "FUTU", "name": "Futu Holdings Limited", "exchange": "NASDAQ"},
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
