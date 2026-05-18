import sqlite3
import threading
import os

# --- CSV lock (questions.csv only; responses now live in SQLite) ---
csv_lock = threading.Lock()

# --- SQLite setup ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'database', 'classroom_pulse.db')

DISCONNECT_TIMEOUT = 30   # seconds before a student is marked disconnected
DEFAULT_QUESTION_TIME = 120  # seconds

# Thread-local storage for database connections
_thread_local = threading.local()


def get_db():
    """Get or create a thread-local SQLite connection with WAL mode enabled."""
    if not hasattr(_thread_local, 'connection') or _thread_local.connection is None:
        conn = sqlite3.connect(
            DB_PATH, 
            check_same_thread=False, 
            timeout=30.0,  # Increased timeout for concurrent writes
            isolation_level='DEFERRED'  # Better for read-heavy workloads
        )
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA synchronous=NORMAL")  # Better performance with WAL
        conn.execute("PRAGMA cache_size=-64000")  # 64MB cache
        conn.execute("PRAGMA busy_timeout=30000")  # 30 second busy timeout
        conn.execute("PRAGMA wal_autocheckpoint=1000")  # Checkpoint every 1000 pages
        _thread_local.connection = conn
    return _thread_local.connection


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
            auto_start          INTEGER DEFAULT 0,
            show_responses      INTEGER DEFAULT 0,
            explainer_text      TEXT,
            explainer_timestamp REAL
        );

        CREATE TABLE IF NOT EXISTS student_last_seen (
            room_id         TEXT NOT NULL,
            student_name    TEXT NOT NULL,
            last_seen       REAL NOT NULL,
            PRIMARY KEY (room_id, student_name)
        );
        
        CREATE INDEX IF NOT EXISTS idx_student_room_lastseen 
            ON student_last_seen(room_id, last_seen);
        
        CREATE INDEX IF NOT EXISTS idx_room_state 
            ON room_states(state);

        CREATE TABLE IF NOT EXISTS responses (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp     TEXT NOT NULL,
            room_id       TEXT NOT NULL,
            student_name  TEXT NOT NULL,
            question_id   TEXT NOT NULL,
            answer        TEXT,
            is_correct    TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_responses_room_question
            ON responses(room_id, question_id);
    """)
    
    # Migration: Add show_responses column if it doesn't exist
    try:
        conn.execute("SELECT show_responses FROM room_states LIMIT 1")
    except sqlite3.OperationalError:
        # Column doesn't exist, add it
        conn.execute("ALTER TABLE room_states ADD COLUMN show_responses INTEGER DEFAULT 0")
        conn.commit()
    
    # Migration: Add explainer columns if they don't exist
    try:
        conn.execute("SELECT explainer_text FROM room_states LIMIT 1")
    except sqlite3.OperationalError:
        conn.execute("ALTER TABLE room_states ADD COLUMN explainer_text TEXT")
        conn.commit()
    
    try:
        conn.execute("SELECT explainer_timestamp FROM room_states LIMIT 1")
    except sqlite3.OperationalError:
        conn.execute("ALTER TABLE room_states ADD COLUMN explainer_timestamp REAL")
        conn.commit()
    
    conn.commit()

    # Deduplicate before creating UNIQUE index: keep only the latest row per
    # (room_id, student_name, question_id) so the index creation never fails.
    conn.execute("""
        DELETE FROM responses
        WHERE id NOT IN (
            SELECT MAX(id)
            FROM responses
            GROUP BY room_id, student_name, question_id
        )
    """)
    conn.commit()

    # UNIQUE index created after dedup so it never hits existing duplicate rows.
    conn.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_responses_unique_submission
            ON responses(room_id, student_name, question_id)
    """)
    conn.commit()

    # One-time migration: import existing responses.csv into SQLite (safe to run repeatedly)
    import csv as _csv
    csv_path = os.path.join(os.path.dirname(DB_PATH), 'responses.csv')
    if os.path.exists(csv_path):
        existing = conn.execute("SELECT COUNT(*) FROM responses").fetchone()[0]
        if existing == 0:
            with open(csv_path, 'r', encoding='utf-8') as _f:
                for row in _csv.DictReader(_f):
                    conn.execute(
                        "INSERT INTO responses "
                        "(timestamp, room_id, student_name, question_id, answer, is_correct) "
                        "VALUES (?, ?, ?, ?, ?, ?)",
                        (row.get('timestamp', ''), row.get('room_id', ''),
                         row.get('student_name', ''), row.get('question_id', ''),
                         row.get('answer', ''), row.get('is_correct', ''))
                    )
            conn.commit()

    _thread_local.connection = None  # prevent get_db() returning a closed connection
    conn.close()
