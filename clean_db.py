import sqlite3
import os

DB_FILE = "flight_data.db"
TARGET_CITY = "OKA"

print(f"1. Looking for database: {DB_FILE}...")

if not os.path.exists(DB_FILE):
    print(f"❌ ERROR: Could not find {DB_FILE} in this folder! Are you in the right directory?")
else:
    print("2. Database found. Connecting...")
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        print(f"3. Searching for any routes containing '{TARGET_CITY}'...")
        
        # Count cb vont etre deleter avant
        cursor.execute(f"SELECT COUNT(*) FROM prices WHERE route_id LIKE '%{TARGET_CITY}%'")
        count_before = cursor.fetchone()[0]
        print(f"   -> Found {count_before} rows matching '{TARGET_CITY}'.")
        
        if count_before > 0:
            print("4. Executing deletion...")
            cursor.execute(f"DELETE FROM prices WHERE route_id LIKE '%{TARGET_CITY}%'")
            conn.commit()
            print(f"✅ SUCCESS: Wiped {cursor.rowcount} rows from the vault.")
        else:
            print("✅ SUCCESS: Nothing to delete. The city is already gone.")
            
    except Exception as e:
        print(f"❌ Database error: {e}")
        
    finally:
        if 'conn' in locals():
            conn.close()
            print("5. Vault connection closed.")