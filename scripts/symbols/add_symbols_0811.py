import urllib.request
import json
import ssl
import sys

API_URL = "https://z-service.duckdns.org/api/watchlist"
PULL_KEY = "viigdjjbduugdg4glieig5vljg"
LIST_NAME = "HG-0811-top"

SYMBOLS = [
    {"symbol": "DLO", "name": "dLocal Limited", "exchange": "NASDAQ"},
    {"symbol": "GLBE", "name": "Global-e Online Ltd.", "exchange": "NASDAQ"},
    {"symbol": "TSEM", "name": "Tower Semiconductor Ltd.", "exchange": "NASDAQ"},
    {"symbol": "PENG", "name": "Penguin Solutions, Inc.", "exchange": "NASDAQ"},
    {"symbol": "ECG", "name": "Everus Construction Group, Inc.", "exchange": "NYSE"},
    {"symbol": "NPK", "name": "National Presto Industries, Inc.", "exchange": "NYSE"},
    {"symbol": "TPC", "name": "Tutor Perini Corporation", "exchange": "NYSE"},
    {"symbol": "TATT", "name": "TAT Technologies Ltd.", "exchange": "NASDAQ"},
    {"symbol": "SM", "name": "SM Energy Company", "exchange": "NYSE"},
    {"symbol": "VIST", "name": "Vista Energy, S.A.B. de C.V.", "exchange": "NYSE"},
    {"symbol": "TDW", "name": "Tidewater Inc.", "exchange": "NYSE"},
    {"symbol": "TGB", "name": "Trekor Metals Limited", "exchange": "AMEX"},
    {"symbol": "CSTM", "name": "Constellium SE", "exchange": "NYSE"},
    {"symbol": "KRYS", "name": "Krystal Biotech, Inc.", "exchange": "NASDAQ"},
    {"symbol": "CORT", "name": "Corcept Therapeutics Incorporated", "exchange": "NASDAQ"},
    {"symbol": "PAHC", "name": "Phibro Animal Health Corporation", "exchange": "NASDAQ"},
    {"symbol": "MMSI", "name": "Merit Medical Systems, Inc.", "exchange": "NASDAQ"},
    {"symbol": "ASIC", "name": "Ategrity Specialty Insurance Company Holdings", "exchange": "NYSE"},
    {"symbol": "HG", "name": "Hamilton Insurance Group, Ltd.", "exchange": "NYSE"},
    {"symbol": "AX", "name": "Axos Financial, Inc.", "exchange": "NYSE"},
]

def main():
    target_url = f"{API_URL}?pull_key={PULL_KEY}"
    print(f"Target API: {API_URL}")
    print(f"List Name: {LIST_NAME}")
    print("-" * 50)
    
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    headers = {
        "Content-Type": "application/json",
        "X-Pull-Key": PULL_KEY,
        "User-Agent": "Mozilla/5.0"
    }

    success_count = 0
    for item in SYMBOLS:
        payload = {
            "symbol": item["symbol"],
            "name": item["name"],
            "list_name": LIST_NAME,
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(target_url, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
                if resp.status in (200, 201):
                    print(f"✅ [OK] Added {item['symbol']} ({item['name']})")
                    success_count += 1
                else:
                    print(f"⚠️ [HTTP {resp.status}] {item['symbol']}")
        except Exception as e:
            print(f"❌ [FAIL] {item['symbol']}: {e}")

    print("-" * 50)
    print(f"Finished: Added {success_count}/{len(SYMBOLS)} symbols to watchlist '{LIST_NAME}'.")

if __name__ == "__main__":
    main()
