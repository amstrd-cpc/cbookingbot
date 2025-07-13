import sqlite3
from datetime import datetime, timedelta

DB_PATH = "bookings.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            date TEXT,
            hour INTEGER
        )
    ''')
    conn.commit()
    conn.close()

def get_booked_slots(date_str):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT hour FROM bookings WHERE date = ?', (date_str,))
    results = c.fetchall()
    conn.close()
    return [row[0] for row in results]

def add_booking(username, date_str, hour):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM bookings WHERE date = ? AND hour = ?', (date_str, hour))
    if c.fetchone()[0] == 0:
        c.execute('INSERT INTO bookings (username, date, hour) VALUES (?, ?, ?)',
                  (username, date_str, hour))
        conn.commit()
        conn.close()
        return True
    else:
        conn.close()
        return False

def get_future_bookings(username):
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        SELECT id, date, hour FROM bookings
        WHERE username = ? AND date >= ?
        ORDER BY date, hour
    ''', (username, tomorrow))
    results = c.fetchall()
    conn.close()
    return results

def get_booking_details(booking_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT id, username, date, hour FROM bookings WHERE id = ?', (booking_id,))
    row = c.fetchone()
    conn.close()
    return row

def delete_booking(booking_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('DELETE FROM bookings WHERE id = ?', (booking_id,))
    conn.commit()
    conn.close()

def get_all_bookings(date_str):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT id, username, hour FROM bookings WHERE date = ? ORDER BY hour', (date_str,))
    results = c.fetchall()
    conn.close()
    return results
