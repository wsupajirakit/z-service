import re
import time
from tvDatafeed import TvDatafeed, Interval

with open('dash/src/App.tsx', 'r') as f:
    content = f.read()

# Extract symbols
match = re.search(r'const SYMBOLS\s*=\s*\[(.*?)\];', content, re.DOTALL)
if not match:
    import sys
    print("Could not find SYMBOLS array")
    sys.exit(1)

symbols_str = match.group(1)
symbols = []
for line in symbols_str.split('\n'):
    line = line.strip()
    if line.startswith('{') and 'symbol:' in line:
        sym_match = re.search(r"symbol:\s*'([^']+)'", line)
        exc_match = re.search(r"exchange:\s*'([^']+)'", line)
        if sym_match and exc_match:
            symbols.append({
                "symbol": sym_match.group(1),
                "exchange": exc_match.group(1)
            })

print(f"Extracted {len(symbols)} symbols. Testing...")

tv = TvDatafeed()

results = {"ok": [], "fail": []}

for s in symbols:
    sym = s['symbol']
    exc = s['exchange']
    time.sleep(0.1)
    try:
        df = tv.get_hist(symbol=sym, exchange=exc, interval=Interval.in_daily, n_bars=1)
        if df is not None and not df.empty:
            results["ok"].append(sym)
        else:
            results["fail"].append((sym, exc, "Empty / None returned"))
            print(f"[FAIL] {sym} ({exc})")
    except Exception as e:
        results["fail"].append((sym, exc, str(e)))
        print(f"[ERROR] {sym} ({exc}): {e}")

print(f"\n--- RESULTS ---")
print(f"Total: {len(symbols)}")
print(f"OK: {len(results['ok'])}")
print(f"FAIL: {len(results['fail'])}")

if results["fail"]:
    print("\nFailed Symbols:")
    for sym, exc, reason in results["fail"]:
        print(f"  {sym} ({exc}) - {reason}")
