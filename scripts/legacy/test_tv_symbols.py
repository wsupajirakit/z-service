from tvDatafeed import TvDatafeed, Interval
import time

tv = TvDatafeed()

test_list = [
    ("ASE", "NYSE"),
    ("BTCUSDT", "BINANCE"),
    ("COPX", "NYSE Arca"),
    ("DXY", "TVC"),
    ("FIW", "NYSE Arca"),
    ("HYG", "NYSE Arca"),
    ("IWM", "NYSE Arca"),
    ("NASDAQ", "TVC"),
    ("POWR", "NYSE Arca"),
    ("ROBO", "NYSE Arca"),
    ("SHLD", "NYSE Arca"),
    ("SPY", "NYSE Arca"),
    ("TICK", "USI"),
    ("US10", "TVC"),
    ("US10Y", "TVC"),
    ("USDTHB", "FX_IDC"),
    ("XAUUSD", "OANDA"),
    ("XBI", "NYSE Arca"),
    ("XLF", "NYSE Arca"),
    ("XLRE", "NYSE Arca"),
    ("XLU", "NYSE Arca"),
    ("XLV", "NYSE Arca"),
    ("XME", "NYSE Arca")
]

results = []

for sym, orig_exc in test_list:
    time.sleep(0.5)
    # First, try the original exchange
    df = tv.get_hist(symbol=sym, exchange=orig_exc, interval=Interval.in_daily, n_bars=5)
    if df is not None and not df.empty:
        results.append((sym, orig_exc, "OK (Original)"))
        print(f"[OK] {sym} ({orig_exc}) works as is.")
        continue
    
    # If not working, let's search
    print(f"[FAIL] {sym} ({orig_exc}) failed. Searching alternatives...")
    search_res = tv.search_symbol(sym)
    if search_res:
        found_working = False
        for item in search_res:
            if item.get("symbol") == sym:
                alt_exc = item.get("exchange")
                time.sleep(0.5)
                df_alt = tv.get_hist(symbol=sym, exchange=alt_exc, interval=Interval.in_daily, n_bars=5)
                if df_alt is not None and not df_alt.empty:
                    results.append((sym, alt_exc, "OK (Found alternative)"))
                    print(f"  -> Found working alternative: {sym} ({alt_exc})")
                    found_working = True
                    break
        if not found_working:
            results.append((sym, "N/A", "Failed all alternatives"))
            print(f"  -> No working alternatives found for {sym}")
    else:
        results.append((sym, "N/A", "Not found in search"))
        print(f"  -> Not found in search: {sym}")

print("\n--- FINAL CORRECT SYMBOLS ---")
for sym, exc, status in results:
    print(f"{sym}: {exc} - {status}")

