"""Ticker hygiene, 19 Oct 2026 — every equity in App.tsx must be live on TradingView AND tradable in the supported US brokers
(Dime! / Webull). Checked all 700 equities against the Webull public ticker search; fixes:
  PSTG -> P     Pure Storage renamed Everpure (NYSE: P); Webull no longer lists PSTG (TradingView still serves the old series)
  CSWI -> CSW   CSW Industrials moved to NYSE as CSW; CSWI returned no bars (never reached the CSV)
  ROLL removed  old RBC Bearings ticker, no bars; the live ticker RBC is already in TECH-WATCH-1018
  INDA          exchange NASDAQ -> AMEX (Cboe-listed ETF; TradingView serves it under AMEX/CBOE, NASDAQ returned nothing)
App.tsx is edited directly; this script fixes the Mongo watchlist (CSWI lives in HG-0824-top).
Run:  python3 fix_tickers_1019.py
"""
import json, os, re, ssl, sys, urllib.request

API_URL = "https://z-service.duckdns.org/api/watchlist"


def pull_key() -> str:
    key = os.environ.get("PULL_KEY")
    if key:
        return key
    prior = os.path.join(os.path.dirname(os.path.abspath(__file__)), "add_symbols_0811.py")
    m = re.search(r'PULL_KEY\s*=\s*"([^"]+)"', open(prior).read()) if os.path.exists(prior) else None
    if m:
        return m.group(1)
    sys.exit("ERROR: no pull key — set PULL_KEY=xxxx in the environment")


def call(method, url, key, payload=None):
    ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(f"{url}?pull_key={key}", method=method,
                                 data=json.dumps(payload).encode() if payload else None,
                                 headers={"Content-Type": "application/json", "X-Pull-Key": key, "User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, context=ctx, timeout=15) as r:
        return r.status


def main() -> None:
    key = pull_key()
    print("DELETE HG-0824-top/CSWI", call("DELETE", f"{API_URL}/HG-0824-top/CSWI", key))
    print("POST   HG-0824-top/CSW ", call("POST", API_URL, key, {"symbol": "CSW", "name": "CSW Industrials, Inc.", "exchange": "NYSE", "list_name": "HG-0824-top"}))


if __name__ == "__main__":
    main()
