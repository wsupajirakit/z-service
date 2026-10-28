import re

with open("backend/main.py", "r") as f:
    content = f.read()

# 1. Update export endpoints
content = content.replace(
    'def export_csv(interval: str, part: int = 1):',
    'def export_csv(interval: str, part: int = 1, list_name: str = None):'
)

content = content.replace(
    'csv_content = _build_export_csv_bytes(interval, part)',
    'csv_content = _build_export_csv_bytes(interval, part, list_name)'
)

content = content.replace(
    'def export_zip(interval: str = None, all: bool = False):',
    'def export_zip(interval: str = None, all: bool = False, list_name: str = None):'
)

content = content.replace(
    'z.writestr(f"ztrade_export_{iv}_part1.csv", _build_export_csv_bytes(iv, 1))',
    'z.writestr(f"ztrade_export_{iv}_part1.csv", _build_export_csv_bytes(iv, 1, list_name))'
)
content = content.replace(
    'z.writestr(f"ztrade_export_{iv}_part2.csv", _build_export_csv_bytes(iv, 2))',
    'z.writestr(f"ztrade_export_{iv}_part2.csv", _build_export_csv_bytes(iv, 2, list_name))'
)

# 2. Update _build_export_csv_bytes signature and query
content = content.replace(
    'def _build_export_csv_bytes(interval: str, part: int = 1) -> bytes:',
    'def _build_export_csv_bytes(interval: str, part: int = 1, list_name: str = None) -> bytes:'
)

query_target = """
        cur.execute('''
            SELECT symbol, result_json, timestamp, exchange
            FROM history
            WHERE id IN (
                SELECT MAX(id)
                FROM history
                WHERE interval = ?
                GROUP BY symbol
            )
            ORDER BY symbol ASC
        ''', (interval,))
"""
query_replacement = """
        if list_name and list_name != "All Symbols":
            cur.execute('''
                SELECT symbol, result_json, timestamp, exchange
                FROM history
                WHERE id IN (
                    SELECT MAX(id)
                    FROM history
                    WHERE interval = ?
                    GROUP BY symbol
                )
                AND symbol IN (
                    SELECT symbol FROM watchlist WHERE list_name = ?
                )
                ORDER BY symbol ASC
            ''', (interval, list_name))
        else:
            cur.execute('''
                SELECT symbol, result_json, timestamp, exchange
                FROM history
                WHERE id IN (
                    SELECT MAX(id)
                    FROM history
                    WHERE interval = ?
                    GROUP BY symbol
                )
                ORDER BY symbol ASC
            ''', (interval,))
"""
content = content.replace(query_target, query_replacement)

# 3. Add /api/export/check endpoint
check_endpoint = """
@app.get("/api/export/check")
def export_check(interval: str, list_name: str):
    db = get_db()
    try:
        cur = db.cursor()
        
        # Get symbols in the watchlist
        cur.execute("SELECT DISTINCT symbol FROM watchlist WHERE list_name = ?", (list_name,))
        watchlist_symbols = [r[0] for r in cur.fetchall()]
        
        # Get symbols in history for this interval
        if list_name != "All Symbols":
            cur.execute('''
                SELECT DISTINCT symbol 
                FROM history 
                WHERE interval = ? AND symbol IN (SELECT symbol FROM watchlist WHERE list_name = ?)
            ''', (interval, list_name))
        else:
            cur.execute('SELECT DISTINCT symbol FROM history WHERE interval = ?', (interval,))
            
        history_symbols = set([r[0] for r in cur.fetchall()])
        
        if list_name == "All Symbols":
            # For "All Symbols", we just say how many we found
            available = list(history_symbols)
            return {
                "total_in_list": len(available),
                "available_count": len(available),
                "missing_count": 0,
                "missing_symbols": []
            }
            
        available = [s for s in watchlist_symbols if s in history_symbols]
        missing = [s for s in watchlist_symbols if s not in history_symbols]
        
        return {
            "total_in_list": len(watchlist_symbols),
            "available_count": len(available),
            "missing_count": len(missing),
            "missing_symbols": missing
        }
    finally:
        db.close()
"""
content = content.replace(
    '@app.get("/api/export")\ndef export_csv(interval: str, part: int = 1, list_name: str = None):',
    check_endpoint.strip() + '\n\n@app.get("/api/export")\ndef export_csv(interval: str, part: int = 1, list_name: str = None):'
)

with open("backend/main.py", "w") as f:
    f.write(content)
