"""
FILE: inspect_schemas.py
STATUS: Active
RESPONSIBILITY: Inspect and display database schemas for chat_history.db and events.db.

DEPENDENCIES (Who uses this file):
- Manual developer usage for schema inspection

IMPORTS (What this file needs):
- sqlite3: Database schema inspection
- os: File existence checks

LAST MAJOR UPDATE: 2026-01-31
MAINTAINER: Development Team
"""

import sqlite3
import os

databases = ["data/chat_history.db", "data/events.db"]

for db_path in databases:
    print(f"--- Schema for {db_path} ---")
    if not os.path.exists(db_path):
        print("File not found.")
        continue

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()

        for table in tables:
            table_name = table[0]
            print(f"\nTable: {table_name}")

            # Get schema for the table
            cursor.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{table_name}';")
            schema = cursor.fetchone()[0]
            print(schema)

            # Get row count to see if it's populated
            try:
                cursor.execute(f"SELECT count(*) FROM {table_name}")
                count = cursor.fetchone()[0]
                print(f"Row count: {count}")
            except:
                print("Could not count rows.")

        conn.close()
    except Exception as e:
        print(f"Error reading {db_path}: {e}")
    print("\n" + "=" * 30 + "\n")
