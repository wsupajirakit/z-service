import sqlite3
from tvDatafeed import TvDatafeed, Interval
from datetime import datetime
import sys

symbol = "NVO"
exchange = "NYSE"
target_name = "Novo Nordisk A/S Sponsored ADR Class B"

print(f"=== STEP 1: Verifying {symbol} data fetching from TradingView via tvDatafeed ===")
try:
    tv = TvDatafeed()
    df = tv.get_hist(symbol=symbol, exchange=exchange, interval=Interval.in_daily, n_bars=5)
    if df is not None and not df.empty:
        print(f"SUCCESS: {symbol} on {exchange} returned valid historical data:")
        print(df.tail())
    else:
        print(f"FAILED: {symbol} on {exchange} returned empty data.")
        sys.exit(1)
except Exception as e:
    print(f"FAILED to fetch {symbol} via tvDatafeed: {e}")
    sys.exit(1)

print(f"\n=== STEP 2: Populating database watchlists for {symbol} ===")
db = sqlite3.connect("backend/history.db")
cursor = db.cursor()

# Get all unique lists
cursor.execute("SELECT DISTINCT list_name FROM watchlist")
lists = [row[0] for row in cursor.fetchall()]

ts = datetime.utcnow().isoformat() + "Z"
added_count = 0

for lst in lists:
    cursor.execute("SELECT 1 FROM watchlist WHERE list_name = ? AND symbol = ?", (lst, symbol))
    exists = cursor.fetchone()
    
    if not exists:
        cursor.execute("INSERT INTO watchlist (list_name, symbol, name, timestamp) VALUES (?, ?, ?, ?)", (lst, symbol, target_name, ts))
        print(f"Added {symbol} to watchlist group: '{lst}'")
        added_count += 1
    else:
        print(f"{symbol} already in watchlist group: '{lst}' (Skipped)")

db.commit()
db.close()
print(f"\nFinished. NVO is verified on tvDatafeed and inserted into all {len(lists)} watchlist groups in database.")
