import sys
from tvDatafeed import TvDatafeed
import time

tv = TvDatafeed()

test_list = [
    "ASE", "BTCUSDT", "COPX", "DXY", "FIW", "HYG", "IWM", "NASDAQ", 
    "POWR", "ROBO", "SHLD", "SPY", "TICK", "US10", "US10Y", "USDTHB", 
    "XAUUSD", "XBI", "XLF", "XLRE", "XLU", "XLV", "XME"
]

for sym in test_list:
    try:
        search_res = tv.search_symbol(sym)
        if search_res:
            found_exchanges = []
            for item in search_res:
                if item.get("symbol") == sym:
                    found_exchanges.append(item.get("exchange"))
            # deduplicate
            found_exchanges = list(dict.fromkeys(found_exchanges))
            if found_exchanges:
                print(f"{sym}: Working exchanges found -> {found_exchanges}")
            else:
                print(f"{sym}: Symbol found but no exact match for '{sym}'")
        else:
            print(f"{sym}: No search results")
    except Exception as e:
        print(f"{sym}: Error -> {e}")
    time.sleep(0.5)
