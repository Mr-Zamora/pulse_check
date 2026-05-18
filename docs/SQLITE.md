# Migration Plan: Responses to SQLite

This document outlines the plan to migrate student responses from `responses.csv` to the SQLite database to eliminate cross-process race conditions on PythonAnywhere's multi-worker WSGI environment.

## Goal Description

Move volatile, write-heavy student responses out of `responses.csv` and into the SQLite database. This permanently fixes the "File Wipe" race condition where multiple uWSGI worker processes ignore each other's `threading.Lock()` and simultaneously rewrite the CSV file, corrupting or wiping all student response data.

`questions.csv` remains unchanged — teachers can continue editing it directly in Excel.

---

## Proposed Changes

### 1. Database Schema — `configuration.py`

Add a new `responses` table to `init_db()`:

```sql
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
```

Add a **one-time data migration step** inside `init_db()`: if `database/responses.csv` exists and the `responses` table is empty, read all CSV rows and bulk-insert them into SQLite so no historical data is lost.

> **Note on Unicode:** SQLite's `LOWER()` function only handles ASCII characters, while Python's `.lower()` handles full Unicode. The `normalize_answer()` function uses Python's `.lower()`. To avoid a mismatch when soft-deleting responses, the `is_correct = 'DELETED'` update in `delete_response` should pass the already-normalised `normalized_answer` Python-side rather than relying on SQL `LOWER(TRIM(...))`. See Section 4.

---

### 2. Remove In-Memory Cache — `app.py`

The `responses_cache`, `responses_cache_mtime`, and `cache_lock` variables exist purely to reduce repeated CSV file reads. SQLite makes them redundant.

- **Delete** the following variable declarations (lines 39–42):
  - `responses_cache = None`
  - `responses_cache_mtime = 0`
  - `cache_lock = threading.Lock()`
- **Do NOT remove** `questions_cache = None` (line 39) — questions still use CSV caching.
- **Remove all four usages** of `cache_lock` across the file:
  - Inside `read_responses()`
  - Inside `write_response()`
  - Inside `delete_response()`
  - Inside `/api/submit` (short answer resubmission block)
- **Remove orphan `global` declarations** — two `global responses_cache, responses_cache_mtime` statements live *inside* the `cache_lock` blocks and will not be caught by simply removing the `with cache_lock:` wrapper:
  - Line 467 inside `delete_response()`
  - Line 585 inside `/api/submit`
  These must be explicitly deleted.
- **Remove** `import threading` from app.py (line 6) — it is only used for `cache_lock`.
- **Remove** the `RESPONSES_CSV` constant (line 36).
- Keep `import csv` and `csv_lock` — both are still required for `questions.csv`.

---

### 3. Update Response Read/Write Helpers — `app.py`

#### `read_responses(room_id, question_id)`
Replace the entire cache + CSV parsing block with a SQL `SELECT`:
```python
def read_responses(room_id=None, question_id=None):
    db = get_db()
    if room_id and question_id:
        rows = db.execute(
            "SELECT * FROM responses WHERE room_id = ? AND question_id = ?",
            (room_id, question_id)
        ).fetchall()
    elif room_id:
        rows = db.execute(
            "SELECT * FROM responses WHERE room_id = ?", (room_id,)
        ).fetchall()
    else:
        rows = db.execute("SELECT * FROM responses").fetchall()
    return [dict(r) for r in rows]  # Convert sqlite3.Row → dict for downstream compatibility
```

> The `[dict(r) for r in rows]` conversion ensures all downstream callers (`get_responses()`, `admin_stats()`) that use `.get()` and key access continue to work without any changes.

#### `write_response(response_dict)`
Replace CSV append with a SQL `INSERT`:
```python
def write_response(response_dict):
    db = get_db()
    db.execute(
        "INSERT INTO responses (timestamp, room_id, student_name, question_id, answer, is_correct) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (
            response_dict.get('timestamp', ''),
            response_dict['room_id'],
            response_dict['student_name'],
            response_dict['question_id'],
            response_dict.get('answer', ''),
            response_dict.get('is_correct', '')
        )
    )
    db.commit()
```

---

### 4. Fix Race Conditions — `app.py`

#### `/api/submit` (Short Answer Resubmission)
Replace the entire `if os.path.exists(RESPONSES_CSV):` block (lines 565–587) with a targeted SQL delete. The `if os.path.exists(...)` wrapper also goes away:
```python
db = get_db()
db.execute(
    "DELETE FROM responses WHERE room_id = ? AND student_name = ? AND question_id = ?",
    (room_id, student_name, q_id)
)
db.commit()
```
Then call `write_response()` as normal to insert the new answer.

#### `/api/teacher/delete_response`
Replace the entire block from `responses = read_responses(...)` down to the `cache_lock` invalidation with a single atomic SQL update. Use `cursor.rowcount` to preserve the `deleted_count` return value the frontend expects:
```python
cursor = db.execute(
    "UPDATE responses SET is_correct = 'DELETED' "
    "WHERE room_id = ? AND question_id = ? AND LOWER(TRIM(answer)) = ?",
    (room_id, question_id, normalized_answer)  # normalized_answer already lowercased+stripped by normalize_answer()
)
db.commit()
deleted_count = cursor.rowcount
```

> **Note:** `LOWER(TRIM(answer))` — the `TRIM` must be kept (it was in the original plan but accidentally dropped in an earlier revision). Stored answers could have trailing whitespace; without `TRIM`, the match would fail silently.

---

### 5. Admin Routes — `app.py`

#### `admin_delete_all_responses()` (line 837)
Currently opens `responses.csv` in `'w'` mode — this is itself an instance of the File Wipe bug.
Replace with:
```python
db = get_db()
db.execute("DELETE FROM responses")
db.commit()
```

#### `admin_stats()` (line 717)
After migration, `read_responses()` still works correctly here via the updated helper. For efficiency, replace with a direct SQL count:
```python
response_count = db.execute(
    "SELECT COUNT(*) FROM responses WHERE is_correct != 'DELETED'"
).fetchone()[0]
```

#### `admin_backup()` (line 863)
Currently adds `responses.csv` to the ZIP download. After migration:
- Remove `responses.csv` from the ZIP — it will be empty and stale.
- The `.db` file already contains all responses, so the backup remains complete.

---

## Deployment: One-Time Migration on PythonAnywhere

> [!IMPORTANT]
> `init_db()` is only called when running `python app.py` locally. On PythonAnywhere, the WSGI server imports the app directly and never calls `init_db()`. After deploying this change, you must run the migration **once** manually via the PythonAnywhere Bash console:

```bash
cd /home/pulsecheck/pulse_check
python -c "from configuration import init_db; init_db()"
```

This creates the new `responses` table and migrates any existing CSV data into SQLite. It is safe to run multiple times — the `CREATE TABLE IF NOT EXISTS` and the empty-table check prevent duplicate inserts.

After running, reload the web app from the PythonAnywhere Web tab.

---

## Summary of All Affected Files

| File | Change |
|---|---|
| `configuration.py` | Add `responses` table + index + CSV migration to `init_db()` |
| `app.py` | Remove `responses_cache`, `responses_cache_mtime`, `cache_lock`, `RESPONSES_CSV`, `import threading` |
| `app.py` | Keep `questions_cache`, `csv_lock`, `import csv` — required for questions |
| `app.py` | Rewrite `read_responses()` and `write_response()` |
| `app.py` | Fix `/api/submit` short answer resubmission |
| `app.py` | Fix `/api/teacher/delete_response` |
| `app.py` | Fix `admin_delete_all_responses()` |
| `app.py` | Update `admin_stats()` response count |
| `app.py` | Update `admin_backup()` ZIP contents |

---

## Verification Plan

1. Run the one-time migration via Bash console (see Deployment section above).
2. Run `test_race_conditions.py` — all three tests must pass, especially "SHORT Answer Resubmission".
3. Manually test an MCQ submission and verify it appears on the teacher dashboard.
4. Manually test a SHORT answer resubmission and verify only the latest answer is stored.
5. Test the admin "Delete All Responses" button and verify it clears from the DB.
6. Test the admin backup download and verify the ZIP contains the `.db` file with response data.
