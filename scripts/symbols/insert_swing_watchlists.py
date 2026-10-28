import sqlite3
from datetime import datetime
import re

db = sqlite3.connect("backend/history.db")
cursor = db.cursor()

with open("dash/src/App.tsx", "r") as f:
    content = f.read()

symbol_map = {}
for match in re.finditer(r"symbol:\s*'([^']+)',\s*name:\s*(['\"])(.*?)\2", content):
    symbol_map[match.group(1)] = match.group(3)

lists = {
    'swing-short': 'hbm jef vici itrn kgs ITRN AGO TOL KGS HBM',
    'swing-mod': 'vrt powl hbm plmr jef VRT HBM WHD PLMR HALO powl'
}

ts = datetime.utcnow().isoformat() + "Z"
count = 0
for list_name, symbols_str in lists.items():
    symbols_clean = re.sub(r'[^a-zA-Z0-9]', ' ', symbols_str)
    symbols = [s.strip().upper() for s in symbols_clean.split() if s.strip()]
    for sym in symbols:
        name = symbol_map.get(sym, sym)
        try:
            cursor.execute(
                "INSERT OR IGNORE INTO watchlist (list_name, symbol, name, timestamp) VALUES (?, ?, ?, ?)",
                (list_name, sym, name, ts)
            )
            count += 1
        except Exception as e:
            print(f"Error for {sym} in {list_name}: {e}")

db.commit()
db.close()
print(f"Watchlists populated. Inserted/Updated {count} total symbol entries.")
