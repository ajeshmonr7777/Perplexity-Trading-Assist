import sqlite3
import os

DB_FILE = "trading_system.db"

def migrate():
    if not os.path.exists(DB_FILE):
        print(f"Database {DB_FILE} not found. Skipping migration.")
        return

    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # Check if column exists
        cursor.execute("PRAGMA table_info(portfolio)")
        columns = [info[1] for info in cursor.fetchall()]
        
        if 'side' in columns:
            print("Column 'side' already exists in 'portfolio' table.")
        else:
            print("Adding 'side' column to 'portfolio' table...")
            cursor.execute("ALTER TABLE portfolio ADD COLUMN side VARCHAR DEFAULT 'BUY'")
            conn.commit()
            print("Migration successful.")
            
        conn.close()
    except Exception as e:
        print(f"Migration error: {e}")

if __name__ == "__main__":
    migrate()
