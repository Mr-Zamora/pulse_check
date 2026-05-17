#!/usr/bin/env python3
"""Quick diagnostic for database issues"""

import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'database', 'classroom_pulse.db')

print("=" * 60)
print("Database Diagnostics")
print("=" * 60)

# Check file exists
print(f"\n1. Database path: {DB_PATH}")
print(f"   Exists: {os.path.exists(DB_PATH)}")

if os.path.exists(DB_PATH):
    print(f"   Size: {os.path.getsize(DB_PATH)} bytes")
    print(f"   Readable: {os.access(DB_PATH, os.R_OK)}")
    print(f"   Writable: {os.access(DB_PATH, os.W_OK)}")

# Try to connect
print("\n2. Testing connection...")
try:
    conn = sqlite3.connect(DB_PATH)
    print("   ✓ Connection successful")
    
    # Check journal mode
    cursor = conn.cursor()
    cursor.execute("PRAGMA journal_mode;")
    mode = cursor.fetchone()[0]
    print(f"   Journal mode: {mode}")
    
    # Try to query room_states
    print("\n3. Testing queries...")
    try:
        cursor.execute("SELECT COUNT(*) FROM room_states")
        count = cursor.fetchone()[0]
        print(f"   ✓ room_states table: {count} rows")
    except Exception as e:
        print(f"   ✗ Error querying room_states: {e}")
    
    # Try to query student_last_seen
    try:
        cursor.execute("SELECT COUNT(*) FROM student_last_seen")
        count = cursor.fetchone()[0]
        print(f"   ✓ student_last_seen table: {count} rows")
    except Exception as e:
        print(f"   ✗ Error querying student_last_seen: {e}")
    
    conn.close()
    
except Exception as e:
    print(f"   ✗ Connection failed: {e}")

print("\n" + "=" * 60)
