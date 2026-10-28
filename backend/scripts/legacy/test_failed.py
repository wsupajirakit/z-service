import os
import sys

os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))  # backend/
sys.path.append('.')

from tvDatafeed import TvDatafeed, Interval
import concurrent.futures
import threading

tv = TvDatafeed()
tv_lock = threading.Lock()

def get_tv_data_with_retry(symbol, exchange, interval_enum, n_bars, extended_session, max_retries=2):
    global tv
    last_err = None
    
    for attempt in range(max_retries + 1):
        try:
            with tv_lock:
                current_tv = tv
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(
                    current_tv.get_hist,
                    symbol=symbol,
                    exchange=exchange,
                    interval=interval_enum,
                    n_bars=n_bars,
                    extended_session=extended_session
                )
                df = future.result(timeout=20)
                
            if df is not None and not df.empty:
                return df
                
            if (df is None or df.empty) and extended_session:
                print(f"[{symbol}] extended=True returned empty, falling back to extended=False")
                return get_tv_data_with_retry(symbol, exchange, interval_enum, n_bars, False, max_retries=0)
            
            return df
                    
        except concurrent.futures.TimeoutError as e:
            last_err = "Timeout"
            print(f"[{symbol}] Timeout on attempt {attempt+1}")
            with tv_lock:
                try:
                    tv = TvDatafeed()
                except Exception as ex:
                    print(f"Failed to reinit TV: {ex}")
        except Exception as e:
            last_err = str(e)
            print(f"[{symbol}] Error on attempt {attempt+1}: {e}")
            with tv_lock:
                try:
                    tv = TvDatafeed()
                except Exception as ex:
                    print(f"Failed to reinit TV: {ex}")
                
    if extended_session:
        print(f"[{symbol}] Exhausted retries with extended=True, trying extended=False")
        return get_tv_data_with_retry(symbol, exchange, interval_enum, n_bars, False, max_retries=1)
        
    raise Exception(f"Failed after {max_retries} retries. Last error: {last_err}")

failed_symbols = ["AAOI", "ACLS", "AEHR", "AES", "AMAT", "AMD", "AMKR", "ANET", "APP", "ASE", "ASML", "AVAV", "AVGO", "AXTI", "BABA", "BIIB", "BOTZ", "BTCUSDT", "BWXT", "CDNS", "COHR", "DUK", "EME", "EOSE", "EQIX", "ETN", "FORM", "FTNT", "GD", "GE", "GOOG", "GOOGL", "HOOD", "HYG", "IGV", "IOT", "NASDAQ", "NBIS", "NKE", "NOC"]

# Find exchanges for these
import re
app_tsx_path = '../dash/src/App.tsx'
with open(app_tsx_path, 'r', encoding='utf-8') as f:
    content = f.read()

symbols = []
for line in content.split('\n'):
    sym_match = re.search(r"symbol:\s*'([^']+)'", line)
    exch_match = re.search(r"exchange:\s*'([^']+)'", line)
    if sym_match and exch_match and sym_match.group(1) in failed_symbols:
        symbols.append({'symbol': sym_match.group(1), 'exchange': exch_match.group(1)})

for s in symbols:
    ex = s['exchange']
    if ex.upper() == 'NYSE ARCA': ex = 'AMEX'
    try:
        print(f"Testing {s['symbol']}...")
        df = get_tv_data_with_retry(s['symbol'], ex, Interval.in_1_hour, 300, True)
        if df is not None and not df.empty:
            print(f"-> SUCCESS {len(df)}")
        else:
            print("-> EMPTY")
    except Exception as e:
        print(f"-> ERROR {e}")
