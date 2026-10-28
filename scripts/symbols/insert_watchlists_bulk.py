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
    'A1-Short-week': 'FIX, VRT, PWR, EME, IESC, BWXT, CW, LEU, VICI, AGO, IRM, T, TOL, SKWD, OTTR, HBM, MLI, KGS, TLN, JEF, FN, POWL, NVT, STRL, AAON, CRS, WST, WHD, MWA, AROC, SBAC, ITRN, NWPX, WLDN, CECO, USLM, EXP, USFD, IDCC, NGS, PLMR',
    'A1-med-1m-6m': 'VRT, GEV, FIX, PWR, EME, ETN, IESC, LEU, POWL, AGX, HBM, EXP, FN, AGO, JEF, WST, USFD, TOL, T, TLN, KGS, IRM, VICI, PLMR, NGS, CECO, USLM, WLDN, ATEX, UTI, UFPT, UMH, GHM, ITRN',
    'A1-long-6m': 'GEV, VRT, FIX, ETN, PWR, EME, IESC, LEU, POWL, MLI, HBM, FLS, AGO, SKWD, KGS, WHD, IRM, NVT, MWA, IDCC, OTTR, AAON, SBAC, STRL, CRS, TLN',
    'A2-Short-week': 'VICI, AGO, IRM, T, TOL, SKWD, OTTR, EXP, USFD, ITRN, JEF, HBM, MLI, NWPX, SBAC, TLN, FN, AGX, CECO, WLDN, ATEX, LEU, GHM, USLM, NGS, KGS',
    'A2-med-1m-6m': 'AGX, CECO, EXP, USLM, JEF, PLMR, FN, WST, EXEL, USFD, UTI, NXST, OTTR, NGS, UMH, VRT, FIX, POWL, KGS, WHD, PIPR, GHM, WLDN, ATEX, HBM, MOD',
    'A2-long-6m': 'POWL, FLS, MLI, HBM, AGO, SKWD, KGS, IRM, VICI, T, NI, BG, STE, IDCC, TOL, GEV, VRT, FIX, PWR, ETN, NVT, KGC, STRL, AAON, CRS, AROC, FLEX, MOD, LEU, HNRG'
}

ts = datetime.utcnow().isoformat() + "Z"
count = 0
for list_name, symbols_str in lists.items():
    symbols = [s.strip() for s in symbols_str.split(',') if s.strip()]
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
