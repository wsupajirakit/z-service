from tvDatafeed import TvDatafeed, Interval
import time

tv = TvDatafeed()

test_list = {
    "ASE": ["AMEX", "NYSE"],
    "BTCUSDT": ["BINANCE", "CRYPTO"],
    "COPX": ["AMEX", "NYSE", "NYSE Arca"],
    "DXY": ["TVC"],
    "FIW": ["AMEX", "NYSE"],
    "HYG": ["AMEX", "NYSE"],
    "IWM": ["AMEX", "NYSE"],
    "NASDAQ": ["TVC", "NASDAQ"],
    "POWR": ["AMEX", "NYSE"],
    "ROBO": ["AMEX", "NYSE"],
    "SHLD": ["AMEX", "NYSE"],
    "SPY": ["AMEX", "NYSE"],
    "TICK": ["USI"],
    "US10": ["TVC"],
    "US10Y": ["TVC"],
    "USDTHB": ["FX_IDC"],
    "XAUUSD": ["OANDA", "FOREXCOM", "FX_IDC"],
    "XBI": ["AMEX", "NYSE"],
    "XLF": ["AMEX", "NYSE"],
    "XLRE": ["AMEX", "NYSE"],
    "XLU": ["AMEX", "NYSE"],
    "XLV": ["AMEX", "NYSE"],
    "XME": ["AMEX", "NYSE"]
}

results = []
for sym, exchanges in test_list.items():
    working_exc = None
    for exc in exchanges:
        time.sleep(0.5)
        try:
            df = tv.get_hist(symbol=sym, exchange=exc, interval=Interval.in_daily, n_bars=5)
            if df is not None and not df.empty:
                working_exc = exc
                break
        except Exception as e:
            print(f"Error for {sym} on {exc}: {e}")
    if working_exc:
        results.append((sym, working_exc))
        print(f"[OK] {sym} -> {working_exc}")
    else:
        results.append((sym, "FAILED"))
        print(f"[FAIL] {sym} could not be fetched on any attempted exchange")

print("\n--- FINAL CORRECT SYMBOLS ---")
for sym, exc in results:
    print(f"{sym}: {exc}")

