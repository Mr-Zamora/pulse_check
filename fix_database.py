#!/usr/bin/env python3
"""
Database recovery script for Pulse Check
Run this if you get "database disk image is malformed" error
"""

import os
import sqlite3
from datetime import datetime

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.join(BASE_DIR, 'database')
DB_PATH = os.path.join(DB_DIR, 'classroom_pulse.db')
BACKUP_PATH = os.path.join(DB_DIR, f'classroom_pulse_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db')

def fix_database():
    """Fix corrupted database by recreating it"""
    
    print("=" * 60)
    print("Pulse Check Database Recovery Tool")
    print("=" * 60)
    
    # Check if database exists
    if not os.path.exists(DB_PATH):
        print(f"✓ Database not found at {DB_PATH}")
        print("  It will be created automatically when the app starts.")
        return
    
    print(f"Found database at: {DB_PATH}")
    
    # Try to check integrity
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("PRAGMA integrity_check;")
        result = cursor.fetchone()
        conn.close()
        
        if result[0] == 'ok':
            print("✓ Database integrity check passed - no corruption detected")
            return
        else:
            print(f"✗ Database integrity check failed: {result[0]}")
    except Exception as e:
        print(f"✗ Database is corrupted: {e}")
    
    # Backup the corrupted database
    print(f"\nBacking up corrupted database to: {BACKUP_PATH}")
    try:
        import shutil
        shutil.copy2(DB_PATH, BACKUP_PATH)
        print("✓ Backup created successfully")
    except Exception as e:
        print(f"⚠ Warning: Could not create backup: {e}")
    
    # Delete corrupted database
    print(f"\nDeleting corrupted database...")
    try:
        os.remove(DB_PATH)
        print("✓ Corrupted database deleted")
    except Exception as e:
        print(f"✗ Error deleting database: {e}")
        return
    
    # Create fresh database
    print("\nCreating fresh database...")
    try:
        from configuration import init_db
        init_db()
        print("✓ Fresh database created successfully")
    except Exception as e:
        print(f"✗ Error creating database: {e}")
        return
    
    print("\n" + "=" * 60)
    print("✓ Database recovery complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Restart your Flask app")
    print("2. The app should now work normally")
    print("3. All room state has been reset (this is expected)")
    print(f"4. Corrupted database backed up to: {BACKUP_PATH}")

if __name__ == '__main__':
    fix_database()
