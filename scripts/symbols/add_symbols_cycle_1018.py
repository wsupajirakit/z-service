"""Next-cycle groups (midterm-election calendar evidence) — non-tech gap fill, 18 Oct 2026.

Measured on 104 group ETFs/indices, weekly 1983-2026 (stock-radar skill-automate/adhoc/thesis/NEXT_CYCLE.md):
flow/chart "accumulation" signals did NOT predict the next leader; the midterm cycle did — S&P 500 up in the
52 weeks after mid-October of every midterm year since 1970 (14/14, median +13.7%). Groups that led in that window:
semis, Nasdaq/software (already in the universe), homebuilders, gold/miners, medtech; Japan via the BOJ hiking cycle.
Stocks: Nasdaq screener cap >= $2B, not yet in App.tsx, ext200 < 25%, $vol20 >= $30M; all 30 verified on TradingView 16 Oct 2026.
  CYCLE-JPBANK-1018  MUFG SMFG MFG TAK HMC   (weekly CMF20 0.08-0.35, OBV rising, above SMA30w; BOJ at 1.25%)
  CYCLE-GOLD-1018    WPM FNV RGLD AEM B IAG SSRM FSM BTG   (royalty/streaming + majors; entry only after gold closes a week above SMA30w)
  CYCLE-HOUSING-1018 DHI PHM LEN NVR KBH MAS MHK CVCO SKY TREX BLDR   (watch-only: needs 10Y <= 4.87% and XHB weekly close > SMA30w)
  CYCLE-MEDTECH-1018 DXCM BDX GKOS SOLV PEN   (above SMA30w with positive weekly flow)

Run:  python3 add_symbols_cycle_1018.py
"""

import json
import os
import re
import ssl
import sys
import urllib.request

API_URL = "https://z-service.duckdns.org/api/watchlist"

LISTS = {
    "CYCLE-JPBANK-1018": [
        {"symbol": "MUFG", "name": "Mitsubishi UFJ Financial Group, Inc.", "exchange": "NYSE"},
        {"symbol": "SMFG", "name": "Sumitomo Mitsui Financial Group, Inc.", "exchange": "NYSE"},
        {"symbol": "MFG", "name": "Mizuho Financial Group, Inc.", "exchange": "NYSE"},
        {"symbol": "TAK", "name": "Takeda Pharmaceutical Company Limited", "exchange": "NYSE"},
        {"symbol": "HMC", "name": "Honda Motor Co., Ltd.", "exchange": "NYSE"},
    ],
    "CYCLE-GOLD-1018": [
        {"symbol": "WPM", "name": "Wheaton Precious Metals Corp.", "exchange": "NYSE"},
        {"symbol": "FNV", "name": "Franco-Nevada Corporation", "exchange": "NYSE"},
        {"symbol": "RGLD", "name": "Royal Gold, Inc.", "exchange": "NASDAQ"},
        {"symbol": "AEM", "name": "Agnico Eagle Mines Limited", "exchange": "NYSE"},
        {"symbol": "B", "name": "Barrick Mining Corporation", "exchange": "NYSE"},
        {"symbol": "IAG", "name": "IAMGOLD Corporation", "exchange": "NYSE"},
        {"symbol": "SSRM", "name": "SSR Mining Inc.", "exchange": "NASDAQ"},
        {"symbol": "FSM", "name": "Fortuna Mining Corp.", "exchange": "NYSE"},
        {"symbol": "BTG", "name": "B2Gold Corp.", "exchange": "AMEX"},
    ],
    "CYCLE-HOUSING-1018": [
        {"symbol": "DHI", "name": "D.R. Horton, Inc.", "exchange": "NYSE"},
        {"symbol": "PHM", "name": "PulteGroup, Inc.", "exchange": "NYSE"},
        {"symbol": "LEN", "name": "Lennar Corporation", "exchange": "NYSE"},
        {"symbol": "NVR", "name": "NVR, Inc.", "exchange": "NYSE"},
        {"symbol": "KBH", "name": "KB Home", "exchange": "NYSE"},
        {"symbol": "MAS", "name": "Masco Corporation", "exchange": "NYSE"},
        {"symbol": "MHK", "name": "Mohawk Industries, Inc.", "exchange": "NYSE"},
        {"symbol": "CVCO", "name": "Cavco Industries, Inc.", "exchange": "NASDAQ"},
        {"symbol": "SKY", "name": "Champion Homes, Inc.", "exchange": "NYSE"},
        {"symbol": "TREX", "name": "Trex Company, Inc.", "exchange": "NYSE"},
        {"symbol": "BLDR", "name": "Builders FirstSource, Inc.", "exchange": "NYSE"},
    ],
    "CYCLE-MEDTECH-1018": [
        {"symbol": "DXCM", "name": "DexCom, Inc.", "exchange": "NASDAQ"},
        {"symbol": "BDX", "name": "Becton, Dickinson and Company", "exchange": "NYSE"},
        {"symbol": "GKOS", "name": "Glaukos Corporation", "exchange": "NYSE"},
        {"symbol": "SOLV", "name": "Solventum Corporation", "exchange": "NYSE"},
        {"symbol": "PEN", "name": "Penumbra, Inc.", "exchange": "NYSE"},
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
