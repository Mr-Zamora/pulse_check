import sqlite3
import threading
import os

# --- CSV lock (still needed for questions.csv and responses.csv writes) ---
csv_lock = threading.Lock()

# --- SQLite setup ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'database', 'classroom_pulse.db')

DISCONNECT_TIMEOUT = 30   # seconds before a student is marked disconnected
DEFAULT_QUESTION_TIME = 120  # seconds


def get_db():
    """Open a thread-local SQLite connection with WAL mode enabled."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """Create tables if they don't exist. Called once on app startup."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS room_states (
            room_id             TEXT PRIMARY KEY,
            state               TEXT NOT NULL DEFAULT 'WAITING',
            current_q           TEXT,
            instruction_start   REAL,
            instruction_duration INTEGER DEFAULT 120,
            quiz_start          REAL,
            quiz_duration       INTEGER DEFAULT 120,
            auto_start          INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS student_last_seen (
            room_id         TEXT NOT NULL,
            student_name    TEXT NOT NULL,
            last_seen       REAL NOT NULL,
            PRIMARY KEY (room_id, student_name)
        );
    """)
    conn.commit()
    conn.close()
