"""STORAGE-NEW-1020 — storage / cloud / data-infrastructure names that were NEVER in the csv universe (20 Oct 2026).
Researched: 42 never-in-csv names (web + SEC/IR + Yahoo FA + Webull) -> 34 scored -> 1 pass all gates (AVPT) + 8 watch.
  AVPT  AvePoint       agent governance (AgentPulse) · ARR +27% · no debt · above SMA50/200 · earnings 5 Nov
  OTEX  Open Text      information management · reclaimed SMA200 · FCF 26% fwdPE 6 · OpenText World 19-22 Oct · earnings 5 Nov
  PRGS  Progress       data/dev platform · OM 43% · Agentic RAG 1 Oct · Domo closed 22 Sep · best chart of the watch set
  GDS   GDS Holdings   China data centres · backlog 757MW · DayOne (DODC) IPO filed 5 Oct · chart broken
  INOD  Innodata       human expert data AI cannot self-generate · rev +58% OM 17% no debt · new CEO 30 Sep
  PD    PagerDuty      incident/ops data · ARR $501M FCF 24% · Anthropic/CoreWeave customers · ext200 69% (no chase)
  QMCO  Quantum        object storage ActiveScale · back to profit, debt cleared · CFO fired 9 Oct · earnings 12 Nov
  BLZE  Backblaze      pure-play object storage · tied to CoreWeave · earnings 2 Nov
  IBM   IBM            storage+data platform (Confluent) · earnings 21 Oct
Excluded (acquired/private/illiquid): VRNT JAMF SNCR TIXT DBRG RAMP DTST NABL NLST CLMB TASK CXM KVYO AMPL RPD PEGA AI SOUN BBAI VERI KC VNET RXT MRAM SIFY BXDC SMWB LTRX CSPI UIS KD.
All 9 verified on TradingView 20 Oct 2026 (daily bars) and Webull (listStatus 1, no PTP). Dime! not script-checkable.
Run:  python3 add_symbols_storage_1020.py
"""
import json, os, re, ssl, sys, urllib.request
API_URL = "https://z-service.duckdns.org/api/watchlist"
LISTS = {"STORAGE-NEW-1020": [
    {"symbol": "AVPT", "name": "AvePoint, Inc.", "exchange": "NASDAQ"},
    {"symbol": "OTEX", "name": "Open Text Corporation", "exchange": "NASDAQ"},
    {"symbol": "PRGS", "name": "Progress Software Corporation", "exchange": "NASDAQ"},
    {"symbol": "GDS", "name": "GDS Holdings Limited", "exchange": "NASDAQ"},
    {"symbol": "INOD", "name": "Innodata Inc.", "exchange": "NASDAQ"},
    {"symbol": "PD", "name": "PagerDuty, Inc.", "exchange": "NYSE"},
    {"symbol": "QMCO", "name": "Quantum Corporation", "exchange": "NASDAQ"},
    {"symbol": "BLZE", "name": "Backblaze, Inc.", "exchange": "NASDAQ"},
    {"symbol": "IBM", "name": "International Business Machines Corporation", "exchange": "NYSE"},
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
