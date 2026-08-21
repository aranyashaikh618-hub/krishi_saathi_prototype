import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "sensor_data.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # lets you access columns by name
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sensor_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            soil_moisture REAL,
            soil_temperature REAL,
            air_temperature REAL,
            humidity REAL,
            rainfall REAL,
            crop_type TEXT,
            crop_age_days INTEGER,
            soil_type TEXT,
            soil_ph REAL,
            recorded_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def insert_reading(soil_moisture, soil_temperature, air_temperature,
                    humidity, rainfall, crop_type, crop_age_days,
                    soil_type, soil_ph):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO sensor_data
        (soil_moisture, soil_temperature, air_temperature, humidity,
         rainfall, crop_type, crop_age_days, soil_type, soil_ph)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (soil_moisture, soil_temperature, air_temperature, humidity,
          rainfall, crop_type, crop_age_days, soil_type, soil_ph))
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return new_id

def get_latest_reading():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM sensor_data ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_all_readings(limit=100):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM sensor_data ORDER BY id DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]