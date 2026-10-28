"""Tech + tech supply chain + robotics/components + software + hidden parts + next trend — gap fill, 18 Oct 2026.

Source: Nasdaq screener (all US listings, cap >= $2B, price >= $5) minus names already in App.tsx / the radar CSV
-> 410 tech / hidden-part candidates outside the universe. Measured on 10y daily bars (Yahoo; closes cross-checked
against TradingView 16 Oct 2026, all 77 symbols return bars on the exchange below).
  TECH-CORE-1018  (32 · above rising EMA200, 0 <= ext200 < 25%, RS120 vs SPY > 0, $vol20 >= $30M)
      software / AI / security / data:  FROG TENB NTNX MANH SAIL S WK FRSH TDC NICE FIVN TEM BB(QNX embedded OS) SPSC DBX BRZE ASAN CCC MGNI
      hardware, supply chain, hidden parts: FFIV HPQ SWKS SYNA PI(RAIN RFID) ARW AVT SNX(IT distribution) RAL(sensors/test)
                                            MTRN(advanced materials) DCO(aero electronics) XMTR(AI manufacturing marketplace) MSI
  TECH-WATCH-1018 (45 · watch-only)
      extended leaders (ext200 >= 25 = no chase): PTC SHOP NTSK APPN RNG DOCU BOX
      software bellwethers in broken trends:      ADBE ADSK HUBS TOST CHKP
      robotics / motion / sensors / hidden parts:  KEYS PH ST GTES RBC ALGM AMBA LSCC STM SLAB VSH OLED VIAV IPGP WWD LOAR DGII PRLB MXL ROG
      autonomy:                                    AUR MBLY AXON
      next trend / new listings (<250 bars):       SPCX CBRS Q(Qnity, DuPont electronics spin) HONA FPS QNT ARXS(A&D/semi components) MDA IONQ JOBY
Skipped: P (Everpure = Pure Storage renamed; same price series as PSTG already in the universe) · SKHY (already in App.tsx).

Run:  python3 add_symbols_tech_1018.py
"""

import json
import os
import re
import ssl
import sys
import urllib.request

API_URL = "https://z-service.duckdns.org/api/watchlist"

LISTS = {
    "TECH-CORE-1018": [
        {"symbol": "FROG", "name": "JFrog Ltd.", "exchange": "NASDAQ"},
        {"symbol": "TENB", "name": "Tenable Holdings, Inc.", "exchange": "NASDAQ"},
        {"symbol": "NTNX", "name": "Nutanix, Inc.", "exchange": "NASDAQ"},
        {"symbol": "MANH", "name": "Manhattan Associates, Inc.", "exchange": "NASDAQ"},
        {"symbol": "SAIL", "name": "SailPoint, Inc.", "exchange": "NASDAQ"},
        {"symbol": "S", "name": "SentinelOne, Inc.", "exchange": "NYSE"},
        {"symbol": "WK", "name": "Workiva Inc.", "exchange": "NYSE"},
        {"symbol": "FRSH", "name": "Freshworks Inc.", "exchange": "NASDAQ"},
        {"symbol": "TDC", "name": "Teradata Corporation", "exchange": "NYSE"},
        {"symbol": "NICE", "name": "NICE Ltd.", "exchange": "NASDAQ"},
        {"symbol": "FIVN", "name": "Five9, Inc.", "exchange": "NASDAQ"},
        {"symbol": "TEM", "name": "Tempus AI, Inc.", "exchange": "NASDAQ"},
        {"symbol": "BB", "name": "BlackBerry Limited", "exchange": "NYSE"},
        {"symbol": "SPSC", "name": "SPS Commerce, Inc.", "exchange": "NASDAQ"},
        {"symbol": "DBX", "name": "Dropbox, Inc.", "exchange": "NASDAQ"},
        {"symbol": "BRZE", "name": "Braze, Inc.", "exchange": "NASDAQ"},
        {"symbol": "ASAN", "name": "Asana, Inc.", "exchange": "NYSE"},
        {"symbol": "CCC", "name": "CCC Intelligent Solutions Holdings Inc.", "exchange": "NASDAQ"},
        {"symbol": "MGNI", "name": "Magnite, Inc.", "exchange": "NASDAQ"},
        {"symbol": "FFIV", "name": "F5, Inc.", "exchange": "NASDAQ"},
        {"symbol": "HPQ", "name": "HP Inc.", "exchange": "NYSE"},
        {"symbol": "SWKS", "name": "Skyworks Solutions, Inc.", "exchange": "NASDAQ"},
        {"symbol": "SYNA", "name": "Synaptics Incorporated", "exchange": "NASDAQ"},
        {"symbol": "PI", "name": "Impinj, Inc.", "exchange": "NASDAQ"},
        {"symbol": "ARW", "name": "Arrow Electronics, Inc.", "exchange": "NYSE"},
        {"symbol": "AVT", "name": "Avnet, Inc.", "exchange": "NASDAQ"},
        {"symbol": "SNX", "name": "TD SYNNEX Corporation", "exchange": "NYSE"},
        {"symbol": "RAL", "name": "Ralliant Corporation", "exchange": "NYSE"},
        {"symbol": "MTRN", "name": "Materion Corporation", "exchange": "NYSE"},
        {"symbol": "DCO", "name": "Ducommun Incorporated", "exchange": "NYSE"},
        {"symbol": "XMTR", "name": "Xometry, Inc.", "exchange": "NASDAQ"},
        {"symbol": "MSI", "name": "Motorola Solutions, Inc.", "exchange": "NYSE"},
    ],
    "TECH-WATCH-1018": [
        {"symbol": "PTC", "name": "PTC Inc.", "exchange": "NASDAQ"},
        {"symbol": "SHOP", "name": "Shopify Inc.", "exchange": "NASDAQ"},
        {"symbol": "NTSK", "name": "Netskope, Inc.", "exchange": "NASDAQ"},
        {"symbol": "APPN", "name": "Appian Corporation", "exchange": "NASDAQ"},
        {"symbol": "RNG", "name": "RingCentral, Inc.", "exchange": "NYSE"},
        {"symbol": "DOCU", "name": "DocuSign, Inc.", "exchange": "NASDAQ"},
        {"symbol": "BOX", "name": "Box, Inc.", "exchange": "NYSE"},
        {"symbol": "ADBE", "name": "Adobe Inc.", "exchange": "NASDAQ"},
        {"symbol": "ADSK", "name": "Autodesk, Inc.", "exchange": "NASDAQ"},
        {"symbol": "HUBS", "name": "HubSpot, Inc.", "exchange": "NYSE"},
        {"symbol": "TOST", "name": "Toast, Inc.", "exchange": "NYSE"},
        {"symbol": "CHKP", "name": "Check Point Software Technologies Ltd.", "exchange": "NASDAQ"},
        {"symbol": "KEYS", "name": "Keysight Technologies, Inc.", "exchange": "NYSE"},
        {"symbol": "PH", "name": "Parker-Hannifin Corporation", "exchange": "NYSE"},
        {"symbol": "ST", "name": "Sensata Technologies Holding plc", "exchange": "NYSE"},
        {"symbol": "GTES", "name": "Gates Industrial Corporation Ltd.", "exchange": "NYSE"},
        {"symbol": "RBC", "name": "RBC Bearings Incorporated", "exchange": "NYSE"},
        {"symbol": "ALGM", "name": "Allegro MicroSystems, Inc.", "exchange": "NASDAQ"},
        {"symbol": "AMBA", "name": "Ambarella, Inc.", "exchange": "NASDAQ"},
        {"symbol": "LSCC", "name": "Lattice Semiconductor Corporation", "exchange": "NASDAQ"},
        {"symbol": "STM", "name": "STMicroelectronics N.V.", "exchange": "NYSE"},
        {"symbol": "SLAB", "name": "Silicon Laboratories Inc.", "exchange": "NASDAQ"},
        {"symbol": "VSH", "name": "Vishay Intertechnology, Inc.", "exchange": "NYSE"},
        {"symbol": "OLED", "name": "Universal Display Corporation", "exchange": "NASDAQ"},
        {"symbol": "VIAV", "name": "Viavi Solutions Inc.", "exchange": "NASDAQ"},
        {"symbol": "IPGP", "name": "IPG Photonics Corporation", "exchange": "NASDAQ"},
        {"symbol": "WWD", "name": "Woodward, Inc.", "exchange": "NASDAQ"},
        {"symbol": "LOAR", "name": "Loar Holdings Inc.", "exchange": "NYSE"},
        {"symbol": "DGII", "name": "Digi International Inc.", "exchange": "NASDAQ"},
        {"symbol": "PRLB", "name": "Proto Labs, Inc.", "exchange": "NYSE"},
        {"symbol": "MXL", "name": "MaxLinear, Inc.", "exchange": "NASDAQ"},
        {"symbol": "AUR", "name": "Aurora Innovation, Inc.", "exchange": "NASDAQ"},
        {"symbol": "MBLY", "name": "Mobileye Global Inc.", "exchange": "NASDAQ"},
        {"symbol": "AXON", "name": "Axon Enterprise, Inc.", "exchange": "NASDAQ"},
        {"symbol": "ROG", "name": "Rogers Corporation", "exchange": "NYSE"},
        {"symbol": "SPCX", "name": "Space Exploration Technologies Corp.", "exchange": "NASDAQ"},
        {"symbol": "CBRS", "name": "Cerebras Systems Inc.", "exchange": "NASDAQ"},
        {"symbol": "Q", "name": "Qnity Electronics, Inc.", "exchange": "NYSE"},
        {"symbol": "HONA", "name": "Honeywell Aerospace Inc.", "exchange": "NASDAQ"},
        {"symbol": "FPS", "name": "Forgent Power Solutions, Inc.", "exchange": "NYSE"},
        {"symbol": "QNT", "name": "Quantinuum Inc.", "exchange": "NASDAQ"},
        {"symbol": "ARXS", "name": "Arxis, Inc.", "exchange": "NASDAQ"},
        {"symbol": "MDA", "name": "MDA Space Ltd.", "exchange": "NYSE"},
        {"symbol": "IONQ", "name": "IonQ, Inc.", "exchange": "NYSE"},
        {"symbol": "JOBY", "name": "Joby Aviation, Inc.", "exchange": "NYSE"},
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
