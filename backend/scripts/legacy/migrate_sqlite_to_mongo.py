"""One-time migration: copy every SQLite table into MongoDB collections.

Usage:
    cd backend && source venv/bin/activate && python migrate_sqlite_to_mongo.py

Reads MONGO_URI from env (or .env.local). Each SQLite table becomes a Mongo
collection of the same name; each row becomes a document keyed by column name.
The SQLite integer `id` is preserved as `_sqlite_id` (Mongo assigns its own _id).
Idempotent: drops+reloads each collection so re-running gives a clean copy.
"""
import os
import sqlite3
import sys

from dotenv import load_dotenv
from pymongo import MongoClient

# Load .env.local first (local dev creds), then fall back to .env
_here = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_here, "..", ".env.local"))
load_dotenv(os.path.join(_here, "..", ".env"))

MONGO_URI = os.environ.get("MONGO_URI")
MONGO_DB = os.environ.get("MONGO_DB", "zservice")
SQLITE_PATH = os.path.join(_here, "history.db")

if not MONGO_URI:
    sys.exit("MONGO_URI is not set (put it in .env.local)")

sq = sqlite3.connect(SQLITE_PATH)
sq.row_factory = sqlite3.Row
tables = [r[0] for r in sq.execute(
    "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
).fetchall()]

client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=10000)
db = client[MONGO_DB]

print(f"SQLite: {SQLITE_PATH}")
print(f"Mongo : {MONGO_DB} @ {MONGO_URI.split('@')[-1].split('/')[0]}")
print(f"Tables: {tables}\n")

# Collections that use an auto-increment integer `id` (referenced by the API).
SEQ_COLLECTIONS = {"history", "stock_radar_history", "earning_scan_history"}

for t in tables:
    rows = sq.execute(f"SELECT * FROM {t}").fetchall()
    db[t].drop()  # clean reload
    max_id = 0
    if rows:
        docs = []
        for r in rows:
            d = dict(r)
            if "id" in d and d["id"] is not None:
                max_id = max(max_id, int(d["id"]))  # keep SQLite id as-is
            docs.append(d)
        db[t].insert_many(docs)
    # Seed the counter so new inserts continue from the current max id.
    if t in SEQ_COLLECTIONS:
        db["counters"].update_one(
            {"_id": t}, {"$set": {"seq": max_id}}, upsert=True
        )
    print(f"  {t:24} -> {len(rows)} docs (max id {max_id})")

sq.close()
print("\n✅ migration complete")
