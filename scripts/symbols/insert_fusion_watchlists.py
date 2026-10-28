import sqlite3
from datetime import datetime
import re

db = sqlite3.connect("backend/history.db")
cursor = db.cursor()

with open("dash/src/symbols.ts", "r") as f:
    content = f.read()

symbol_map = {}
for match in re.finditer(r"symbol:\s*'([^']+)',\s*name:\s*(['\"])(.*?)\2", content):
    symbol_map[match.group(1)] = match.group(3)

lists = {
    'fusion-long': 'HBM  KGS POWL AGO IRM JEF VICI SKWD',
    'fusion-short': 'hbm kgs jef mli itrn nwpx uslm ago  irm skwd t tol ottr exp usfd wldn ceco agx ghm ngs',
    'fusion-med': 'vrt whd powl ceco. plmr jef kgs agx ngs uslm hbm ghm WLDN NXST'
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
