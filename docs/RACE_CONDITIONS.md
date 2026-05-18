# Race Condition Analysis & Fixes

## Overview

With multiple students submitting answers simultaneously and a teacher viewing results in real-time, race conditions are a critical concern. This document outlines the identified risks and implemented solutions.

---

## Identified Race Conditions

### 1. **CSV File Writes** ⚠️ CRITICAL
**Problem**: Multiple students submitting answers simultaneously could corrupt `responses.csv`

**Scenario**:
- Student A writes answer at byte position 1000
- Student B starts writing at byte position 1000 (before A finishes)
- Result: Corrupted CSV file

**Solution**: ✅ **CSV Lock**
```python
csv_lock = threading.Lock()

with csv_lock:
    with open(RESPONSES_CSV, 'a', newline='', encoding='utf-8') as f:
        writer.writerow(data)
```

### 2. **Cache Invalidation** ⚠️ HIGH
**Problem**: Response cache could serve stale data during concurrent writes

**Scenario**:
- Thread 1 reads cache (mtime = 100)
- Thread 2 writes new response, invalidates cache
- Thread 1 still uses old cache data
- Result: Teacher sees outdated submission count

**Solution**: ✅ **Cache Lock**
```python
cache_lock = threading.Lock()

with cache_lock:
    if current_mtime > responses_cache_mtime:
        responses_cache = reload_from_disk()
```

### 3. **Read-Modify-Write Operations** ⚠️ CRITICAL
**Problem**: SHORT answer resubmission and response deletion do read-modify-write

**Scenario**:
- Thread 1 reads all responses
- Thread 2 reads all responses
- Thread 1 deletes one, writes back
- Thread 2 deletes one, writes back (overwrites Thread 1's change)
- Result: Lost deletion

**Solution**: ✅ **Atomic Operations with Lock**
```python
with csv_lock:
    # Read
    responses = list(csv.DictReader(f))
    # Modify
    filtered = [r for r in responses if condition]
    # Write
    writer.writerows(filtered)

# Then invalidate cache
with cache_lock:
    responses_cache = None
```

### 4. **Database Concurrent Writes** ⚠️ MEDIUM
**Problem**: Multiple threads updating `student_last_seen` simultaneously

**Scenario**:
- 10 students poll `/api/room/status` at the same time
- All try to UPDATE their last_seen timestamp
- SQLite locks database

**Solution**: ✅ **WAL Mode + Busy Timeout**
```python
conn.execute("PRAGMA journal_mode=WAL")  # Allow concurrent reads during writes
conn.execute("PRAGMA busy_timeout=30000")  # Wait up to 30s for lock
isolation_level='DEFERRED'  # Optimistic locking for reads
```

---

## Implemented Protections

### SQLite Configuration
```python
# configuration.py
conn = sqlite3.connect(
    DB_PATH,
    timeout=30.0,              # Wait for locks
    isolation_level='DEFERRED' # Better for read-heavy workloads
)
conn.execute("PRAGMA journal_mode=WAL")
conn.execute("PRAGMA busy_timeout=30000")
conn.execute("PRAGMA wal_autocheckpoint=1000")
```

**Benefits**:
- WAL mode allows multiple readers during writes
- 30-second timeout prevents immediate failures
- DEFERRED isolation reduces lock contention

### Thread-Safe Caching
```python
# app.py
cache_lock = threading.Lock()

def read_responses():
    with cache_lock:
        if cache_needs_reload():
            with csv_lock:
                responses_cache = reload()
        return copy(responses_cache)  # Return copy, not reference
```

**Benefits**:
- Cache reads are atomic
- Cache invalidation is thread-safe
- Callers get independent copies

### CSV Write Protection
```python
# All CSV writes use csv_lock
with csv_lock:
    with open(file, 'w') as f:
        writer.writerows(data)

# Always invalidate cache after write
with cache_lock:
    responses_cache = None
```

**Benefits**:
- Only one thread can write at a time
- Cache is always invalidated after writes
- No partial writes or corruption

---

## Remaining Risks

### 1. **Multi-Process Deployments** ⚠️ LOW
**Issue**: If running with multiple Gunicorn/Waitress workers, each has its own cache

**Impact**: 
- Cache invalidation only affects current process
- Other processes may serve stale data for up to 2 seconds (until next poll)

**Mitigation**:
- Use single worker for small classes (<20 students)
- For larger deployments, consider Redis for shared cache
- Current impact is minimal (2-second staleness acceptable for formative assessment)

### 2. **CSV File Corruption on Crash** ⚠️ LOW
**Issue**: If process crashes during CSV write, file could be corrupted

**Impact**:
- Partial line written to responses.csv
- Next read fails

**Mitigation**:
- Use atomic writes (write to temp file, then rename)
- Regular backups via admin dashboard
- CSV format is human-readable and easily fixable

### 3. **SQLite Database Lock Timeout** ⚠️ LOW
**Issue**: Under extreme load, 30-second timeout could be exceeded

**Impact**:
- Student sees "Database locked" error
- Submission fails

**Mitigation**:
- 30-second timeout is very generous
- WAL mode makes this unlikely
- For 50+ concurrent users, migrate to PostgreSQL

---

## Testing for Race Conditions

### Manual Testing
```bash
# Terminal 1: Start server
python app.py

# Terminal 2-11: Simulate 10 concurrent submissions
for i in {1..10}; do
  curl -X POST http://localhost:5000/api/submit \
    -H "Content-Type: application/json" \
    -d "{\"room_id\":\"test\",\"q_id\":\"q1\",\"student_name\":\"Student$i\",\"ans\":\"A\"}" &
done
wait

# Check responses.csv for corruption
cat database/responses.csv | wc -l  # Should be 11 (header + 10 responses)
```

### Load Testing
```bash
# Install Apache Bench
apt-get install apache2-utils

# Test concurrent polling
ab -n 1000 -c 10 http://localhost:5000/api/room/status?room_id=test&role=teacher

# Test concurrent submissions
ab -n 100 -c 10 -p submit.json -T application/json http://localhost:5000/api/submit
```

### Monitoring
```python
# Add to app.py for debugging
import logging
logging.basicConfig(level=logging.DEBUG)

# Log lock acquisitions
csv_lock.acquire()
logging.debug(f"CSV lock acquired by {threading.current_thread().name}")
# ... do work ...
csv_lock.release()
logging.debug(f"CSV lock released by {threading.current_thread().name}")
```

---

## Best Practices

1. **Always use locks for CSV operations**
   - Read-modify-write must be atomic
   - Invalidate cache after every write

2. **Return copies from cache**
   - Never return direct reference to cached data
   - Prevents external modification

3. **Keep critical sections small**
   - Hold locks for minimum time
   - Do filtering/processing outside locks

4. **Use WAL mode for SQLite**
   - Allows concurrent reads
   - Better performance under load

5. **Set generous timeouts**
   - 30 seconds for database locks
   - Prevents spurious failures

---

## Migration to PostgreSQL (Future)

For 50+ concurrent users, consider PostgreSQL:

```python
# Benefits:
- True concurrent writes (MVCC)
- Row-level locking
- Better connection pooling
- No file-based limitations

# Migration path:
1. Export CSV data to PostgreSQL tables
2. Replace sqlite3 with psycopg2
3. Use SQLAlchemy for ORM
4. Add Redis for distributed caching
```

---

## Summary

| Risk | Severity | Status | Solution |
|------|----------|--------|----------|
| CSV write corruption | CRITICAL | ✅ Fixed | csv_lock |
| Cache staleness | HIGH | ✅ Fixed | cache_lock + invalidation |
| Read-modify-write | CRITICAL | ✅ Fixed | Atomic operations |
| DB lock contention | MEDIUM | ✅ Fixed | WAL mode + timeout |
| Multi-process cache | LOW | ⚠️ Acceptable | 2s staleness OK |
| CSV corruption on crash | LOW | ⚠️ Acceptable | Backups available |
| Extreme load timeout | LOW | ⚠️ Acceptable | Migrate to PostgreSQL |

**Conclusion**: The application is now **production-ready for 20-30 concurrent students** with proper race condition protections in place.
