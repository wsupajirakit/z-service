import sqlite3
import json

db = sqlite3.connect('history.db')
cur = db.cursor()
cur.execute("SELECT result_json FROM history WHERE id = 371")
row = cur.fetchone()
if row:
    data = json.loads(row[0])
    print("Number of candles in record 371:", len(data))
    if len(data) > 0:
        print("First candle sample:", data[0])
else:
    print("Record 371 not found")
db.close()
