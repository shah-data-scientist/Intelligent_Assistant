"""
FILE: audit_data_folder.py
STATUS: Active
RESPONSIBILITY: Comprehensive audit of data folder to identify obsolete files and database tables.

DEPENDENCIES (Who uses this file):
- Manual developer usage for data folder cleanup analysis

IMPORTS (What this file needs):
- sqlite3: Inspect database schema and tables
- pathlib: File system operations

LAST MAJOR UPDATE: 2026-01-31
MAINTAINER: Development Team
"""

import sqlite3
from pathlib import Path


def audit_data_folder():
    """Audit data folder and generate report."""

    print("=" * 80)
    print("DATA FOLDER AUDIT REPORT")
    print("=" * 80)

    # 1. Check database files
    print("\n[1] DATABASE FILES")
    print("-" * 80)

    db_files = [
        ("chat_history.db", "Main chat storage (ACTIVE)"),
        ("chat_history.db-shm", "SQLite WAL shared memory (ACTIVE - DO NOT DELETE)"),
        ("chat_history.db-wal", "SQLite Write-Ahead Log (ACTIVE - DO NOT DELETE)"),
        ("chat_history.db.backup_20260130_184816", "Migration backup (CAN BE DELETED after verification)"),
        ("events.db", "Main event storage (ACTIVE)"),
        ("events.db-shm", "SQLite WAL shared memory (ACTIVE - DO NOT DELETE)"),
        ("events.db-wal", "SQLite Write-Ahead Log (ACTIVE - DO NOT DELETE)"),
    ]

    for filename, description in db_files:
        filepath = Path(f"data/{filename}")
        if filepath.exists():
            size = filepath.stat().st_size / (1024 * 1024)  # MB
            print(f"  [OK] {filename:<45} {size:>8.2f} MB - {description}")
        else:
            print(f"  [--] {filename:<45} NOT FOUND")

    # 2. Check tables in chat_history.db
    print("\n[2] chat_history.db TABLES")
    print("-" * 80)
    conn = sqlite3.connect("data/chat_history.db")
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()

    for table in tables:
        table_name = table[0]
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        print(f"  [OK] {table_name:<30} {count:>10,} rows - ACTIVE")
    conn.close()

    # 3. Check tables in events.db
    print("\n[3] events.db TABLES")
    print("-" * 80)
    conn = sqlite3.connect("data/events.db")
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()

    for table in tables:
        table_name = table[0]
        if table_name == "sqlite_sequence":
            print(f"  [OK] {table_name:<30}            - SQLite internal")
            continue

        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]

        if table_name == "events":
            print(f"  [OK] {table_name:<30} {count:>10,} rows - ACTIVE")
        elif table_name in ["conversations", "feedbacks"]:
            print(f"  [!!] {table_name:<30} {count:>10,} rows - OBSOLETE (moved to chat_history.db)")
    conn.close()

    # 4. Check directories
    print("\n[4] DIRECTORIES")
    print("-" * 80)

    directories = [
        ("faiss_index", "ACTIVE - Vector search index"),
        ("processed", "EMPTY - Can be removed"),
        ("evaluation", "ACTIVE - Should be moved to root"),
    ]

    for dirname, status in directories:
        dirpath = Path(f"data/{dirname}")
        if dirpath.exists():
            file_count = len(list(dirpath.rglob("*")))
            print(f"  [OK] {dirname:<30} {file_count:>5} files - {status}")

    # 5. Summary
    print("\n[5] RECOMMENDED ACTIONS")
    print("-" * 80)

    actions = [
        ("HIGH", "Drop obsolete tables from events.db", ["conversations (236 rows)", "feedbacks (16 rows)"]),
        ("HIGH", "Move evaluation folder to root", ["mv evaluation ./evaluation"]),
        ("MEDIUM", "Remove processed folder", ["Empty directory, not used"]),
        ("LOW", "Delete backup file after verification", ["chat_history.db.backup_20260130_184816 (2.7 MB)"]),
        ("INFO", "Keep WAL files", [".db-shm and .db-wal are ACTIVE, do NOT delete"]),
    ]

    for priority, action, details in actions:
        print(f"\n  [{priority}] {action}")
        for detail in details:
            print(f"      - {detail}")

    print("\n" + "=" * 80)
    print("END OF AUDIT REPORT")
    print("=" * 80)


if __name__ == "__main__":
    audit_data_folder()
