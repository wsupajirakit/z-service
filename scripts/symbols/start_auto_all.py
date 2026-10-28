"""start_auto_all.py — (re)start the server's Auto-All fetch job with the FULL symbol list from dash/src/App.tsx,
without waiting for a Coolify rebuild of the frontend (the UI button only knows the symbols baked into the deployed build).
Usage:  python3 start_auto_all.py            # stop current job, then start with all symbols in App.tsx (rows 80, default TF mode)
        python3 start_auto_all.py --status   # just print job status
Reads the pull key from add_symbols_0811.py (or PULL_KEY env). Never prints the key."""
import json, os, re, ssl, sys, time, urllib.request
BASE = "https://z-service.duckdns.org"
def pull_key():
    k = os.environ.get("PULL_KEY")
    if k: return k
    m = re.search(r'PULL_KEY\s*=\s*"([^"]+)"', open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "add_symbols_0811.py")).read())
    return m.group(1) if m else sys.exit("no pull key")
KEY = pull_key(); CTX = ssl.create_default_context(); CTX.check_hostname = False; CTX.verify_mode = ssl.CERT_NONE
def call(path, data=None):
    req = urllib.request.Request(BASE + path, data=json.dumps(data).encode() if data is not None else None,
                                 headers={"X-Pull-Key": KEY, "Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}, method="POST" if data is not None else "GET")
    try:
        with urllib.request.urlopen(req, context=CTX, timeout=30) as r: return r.status, json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e: return e.code, e.read().decode()[:200]
    except Exception as e: return 0, str(e)[:120]
def status():
    c, d = call("/api/automate/status"); return c, ({k: d.get(k) for k in ("phase", "round", "total", "current_tf", "current", "started_at", "last_round_finished_at", "message")} if isinstance(d, dict) else d)
if "--status" in sys.argv: print(status()); sys.exit(0)
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "dash/src/App.tsx"), encoding="utf-8").read()
blk = src[src.find("const SYMBOLS"):]; blk = blk[:blk.find("\n];") + 3]
syms = [{"symbol": s, "exchange": e} for s, e in re.findall(r"symbol:\s*'([^']+)'[^}]*?exchange:\s*'([^']+)'", blk)]
print(f"symbols in App.tsx: {len(syms)}"); print("status before:", status())
print("stop:", call("/api/auto/stop", {})); time.sleep(5)
for k in range(12):
    c, d = status()
    if isinstance(d, dict) and d.get("phase") in ("idle", None): break
    print("  waiting for job to stop...", d.get("phase") if isinstance(d, dict) else d); time.sleep(10)
c, d = call("/api/auto/start_all", {})
print("start_all (server list):", c, d)
if c != 200:
    print("start (client list):", call("/api/auto/start", {"symbols": syms, "rows": 80, "force_all_tf": False}))
time.sleep(8)
print("status after:", status())
