import sqlite3
from datetime import datetime
import re

symbols = ["EME", "ETN", "MU", "TLN", "VRT", "NVDA", "CEG", "HWM", "PWR", "VST", "NRG", "AVGO", "MSFT", "META", "OKLO"]

db = sqlite3.connect("backend/history.db")
cursor = db.cursor()

with open("dash/src/symbols.ts", "r") as f:
    content = f.read()

symbol_map = {}
for match in re.finditer(r"symbol:\s*'([^']+)',\s*name:\s*(['\"])(.*?)\2", content):
    symbol_map[match.group(1)] = match.group(3)

for sym in symbols:
    name = symbol_map.get(sym, sym)
    ts = datetime.utcnow().isoformat() + "Z"
    try:
        cursor.execute(
            "INSERT OR IGNORE INTO watchlist (list_name, symbol, name, timestamp) VALUES (?, ?, ?, ?)",
            ("5-july", sym, name, ts)
        )
    except Exception as e:
        print(f"Error for {sym}: {e}")

db.commit()
db.close()
print("Watchlist 5-july populated.")
