import sqlite3

def setup_database():
    conn = sqlite3.connect('flight_data.db')
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS price_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            route_id TEXT NOT NULL,
            airline TEXT NOT NULL,
            price REAL NOT NULL,
            departure_date TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            source TEXT NOT NULL
        )
    ''')

    conn.commit()
    conn.close()
    print("SUCCESS: Database 'flight_data.db' and 'price_history' table created.")

if __name__ == "__main__":
    setup_database()