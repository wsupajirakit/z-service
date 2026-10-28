import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "history.db")

def migrate():
    print(f"Connecting to {DB_PATH}")
    db = sqlite3.connect(DB_PATH)
    cursor = db.cursor()
    
    # 1. Watchlist Migration
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='watchlist_old'")
    if not cursor.fetchone():
        print("Migrating watchlist...")
        # Rename old table
        try:
            cursor.execute("ALTER TABLE watchlist RENAME TO watchlist_old")
            # Create new table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS watchlist (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    list_name TEXT,
                    symbol TEXT,
                    name TEXT,
                    timestamp TEXT,
                    UNIQUE(list_name, symbol)
                )
            ''')
            
            # Copy data with default list_name 'Default'
            cursor.execute('''
                INSERT INTO watchlist (list_name, symbol, name, timestamp)
                SELECT 'Default', symbol, name, timestamp FROM watchlist_old
            ''')
            print("Watchlist migrated.")
        except Exception as e:
            print("Error migrating watchlist:", e)
    else:
        print("Watchlist already migrated.")
        
    # 2. Portfolio Migration
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='portfolio_old'")
    if not cursor.fetchone():
        print("Migrating portfolio...")
        # Rename old table
        try:
            cursor.execute("ALTER TABLE portfolio RENAME TO portfolio_old")
            
            # Create new table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS portfolio (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    port_name TEXT,
                    symbol TEXT,
                    quantity INTEGER,
                    buy_price REAL,
                    timestamp TEXT,
                    action TEXT
                )
            ''')
            
            # Copy data with default port_name 'Default'
            cursor.execute('''
                INSERT INTO portfolio (port_name, symbol, quantity, buy_price, timestamp, action)
                SELECT 'Default', symbol, quantity, buy_price, timestamp, action FROM portfolio_old
            ''')
            print("Portfolio migrated.")
        except Exception as e:
            print("Error migrating portfolio:", e)
    else:
        print("Portfolio already migrated.")

    db.commit()
    db.close()
    print("Migration complete.")

if __name__ == "__main__":
    migrate()
