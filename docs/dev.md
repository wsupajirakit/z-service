# 📌 z-service Developer Guide: Adding & Validating New Symbols

> **TL;DR / Critical Architecture Warning:**
> New symbols **must be updated in 2 locations**:
> 1. `dash/src/App.tsx` (`SYMBOLS` hardcoded array)
> 2. Database watchlists (MongoDB / SQLite)
> 
> All UI buttons (**Auto All**, export, watchlist filters) send symbols strictly from `App.tsx`. If a symbol exists only in the database, UI watchlist filtering will intersect it to 0.

---

## 🛠️ Step-by-Step Checklist

### Step 0: Validate Symbol on TradingView & Test Fetching

Before editing code, verify that the symbol exists on TradingView with the correct primary exchange.

#### 1. Search Symbol Metadata via TradingView API
```bash
curl -s "https://symbol-search.tradingview.com/symbol_search/?text=DOCN&hl=0&lang=en&domain=production" \
  -H "Origin: https://www.tradingview.com" -H "User-Agent: Mozilla/5.0" | python3 -m json.tool | head -30
```
- **Requirements:** Ensure exact symbol match, `country: US`, exchange is `NASDAQ`, `NYSE`, or `AMEX`, and `is_primary_listing: true`.
- *Note:* Mismatched exchange causes `tvDatafeed` to idle for ~35s per retry during fetches.

#### 2. Test Fetching Historical Data via `tvDatafeed` (Python)
Run a quick Python verification script using the project's backend environment to ensure `tvDatafeed` returns valid OHLCV bars:
```python
from tvDatafeed import TvDatafeed, Interval

tv = TvDatafeed()
# Example: Testing DOCN on NYSE
df = tv.get_hist(symbol="DOCN", exchange="NYSE", interval=Interval.in_daily, n_bars=5)

if df is not None and not df.empty:
    print("SUCCESS: Data fetched successfully")
    print(df.tail())
else:
    print("FAILED: Empty response from TradingView")
```

---

### Step 1: Update Frontend Hardcoded Array (`dash/src/App.tsx`)

Add the new symbol item to the `SYMBOLS` array in `dash/src/App.tsx` (preferably in alphabetical order):

```typescript
{ symbol: 'DOCN', name: 'DigitalOcean Holdings, Inc.', exchange: 'NYSE' },
{ symbol: 'MDB', name: 'MongoDB, Inc.', exchange: 'NASDAQ' },
```

#### Verification & Push:
1. Run TypeScript check:
   ```bash
   cd dash && npx tsc --noEmit
   ```
2. Commit & Push to `main`:
   ```bash
   git add dash/src/App.tsx
   git commit -m "feat: add DOCN and MDB symbols"
   git push origin main
   ```
3. Wait for production deployment (e.g. Coolify build). Ensure a clean build is produced.

---

### Step 2: Populate Database Watchlists (MongoDB / SQLite)

Add the symbol to the database watchlists so it can be filtered/grouped.

#### Option A: Via REST API
```bash
curl -sk -X POST "https://z-service.duckdns.org/api/watchlist" \
  -H "Content-Type: application/json" -H "X-Pull-Key: $PULL_KEY" \
  -d '{"symbol":"DOCN","name":"DigitalOcean Holdings, Inc.","list_name":"Default"}'
```

#### Option B: Via Python Database Script
Execute a script to populate all watchlist groups in SQLite (`history.db`) or MongoDB (`store.py`):
```python
import sqlite3
from datetime import datetime, timezone

db = sqlite3.connect("history.db")
cursor = db.cursor()

cursor.execute("SELECT DISTINCT list_name FROM watchlist")
groups = [r[0] for r in cursor.fetchall()]

ts = datetime.now(timezone.utc).isoformat()
for group in groups:
    cursor.execute(
        "INSERT OR IGNORE INTO watchlist (list_name, symbol, name, timestamp) VALUES (?, ?, ?, ?)",
        (group, "DOCN", "DigitalOcean Holdings, Inc.", ts)
    )

db.commit()
db.close()
```

---

### Step 3: Post-Deployment Pitfalls & Solutions

| Trap / Issue | Symptom | Fix / Solution |
|---|---|---|
| **In-Memory Job Death** | Container redeploy stops running background fetch silently. | Click **Auto All** on UI to re-trigger job after deploy. |
| **Locked Job Symbol List** | Auto job locked symbol count when started prior to deploy. | Stop active job and restart **Auto All** (ideally during 15-min cooldown window). |
| **Browser JS Cache** | UI buttons send old symbol count despite deployment. | Perform **Hard Refresh (`Cmd + Shift + R`)** in browser. |
| **Empty CSV Export** | Export missing newly added symbols. | Wait for the first fetch round to finish before exporting CSV. |

---

### Step 4: End-to-End Verification

1. Verify automation total symbol count:
   ```bash
   GET /api/automate/status
   ```
   Confirm `total` matches the updated count (e.g., `258`).

2. Verify CSV Export readiness:
   ```bash
   GET /api/export/check?interval=1d&list_name=Default
   ```
   Confirm `missing` list is empty after fetch round finishes.
