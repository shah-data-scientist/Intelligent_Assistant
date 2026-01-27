"""Migration script to deduplicate multi-showtime events.

This script consolidates events occurring at multiple times on the same day
into single records with timings stored as JSON metadata.

Before: Multiple rows for same event at 10:00, 14:00, 18:00
After: Single row with timings_json = ["10:00", "14:00", "18:00"]
"""

import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DB_PATH = Path("./data/events.db")


def add_new_columns(conn: sqlite3.Connection) -> None:
    """Add new columns for timings metadata if they don't exist."""
    cursor = conn.cursor()

    # Check existing columns
    cursor.execute("PRAGMA table_info(events)")
    existing_cols = {row[1] for row in cursor.fetchall()}

    new_columns = [
        ("timings_json", "TEXT"),      # JSON array of time strings: ["10:00", "14:00"]
        ("periods_json", "TEXT"),      # JSON array: ["matin", "après-midi", "soir"]
        ("is_full_day", "INTEGER"),    # 1 if no specific time, spans full day
    ]

    for col_name, col_type in new_columns:
        if col_name not in existing_cols:
            logger.info(f"Adding column: {col_name} ({col_type})")
            cursor.execute(f"ALTER TABLE events ADD COLUMN {col_name} {col_type}")

    conn.commit()
    logger.info("Schema migration complete")


def classify_period(hour: int) -> str:
    """Classify time into period of day."""
    if hour < 12:
        return "matin"
    elif hour < 18:
        return "après-midi"
    else:
        return "soir"


def find_duplicate_groups(conn: sqlite3.Connection, limit: int | None = None) -> list[dict]:
    """Find groups of events that can be deduplicated.

    Groups are identified by matching (title, city, date without time).
    """
    cursor = conn.cursor()

    # Find groups with multiple entries on same day
    query = """
    SELECT
        title,
        city,
        DATE(start_date) as event_date,
        COUNT(*) as count,
        GROUP_CONCAT(id) as ids,
        GROUP_CONCAT(strftime('%H:%M', start_date)) as times
    FROM events
    WHERE start_date IS NOT NULL
    GROUP BY title, city, DATE(start_date)
    HAVING COUNT(*) > 1
    ORDER BY count DESC
    """

    if limit:
        query += f" LIMIT {limit}"

    cursor.execute(query)

    groups = []
    for row in cursor.fetchall():
        title, city, event_date, count, ids_str, times_str = row
        groups.append({
            "title": title,
            "city": city,
            "event_date": event_date,
            "count": count,
            "ids": [int(i) for i in ids_str.split(",")],
            "times": times_str.split(",") if times_str else []
        })

    return groups


def merge_event_group(conn: sqlite3.Connection, group: dict, dry_run: bool = True) -> dict:
    """Merge a group of duplicate events into a single record.

    Strategy:
    - Keep the record with the earliest time as the "primary"
    - Aggregate all times into timings_json
    - Classify times into periods_json
    - Delete duplicate rows

    Returns dict with merge statistics.
    """
    cursor = conn.cursor()
    ids = group["ids"]
    times = group["times"]

    # Get full data for all records to find the primary
    cursor.execute(f"SELECT * FROM events WHERE id IN ({','.join('?' * len(ids))})", ids)
    columns = [desc[0] for desc in cursor.description]
    records = [dict(zip(columns, row)) for row in cursor.fetchall()]

    # Sort by start_date to get earliest as primary
    records.sort(key=lambda r: r["start_date"] if r["start_date"] else "")
    primary = records[0]
    duplicates = records[1:]

    # Collect all unique times
    all_times = set()
    for record in records:
        if record["start_date"]:
            try:
                dt = datetime.fromisoformat(record["start_date"])
                time_str = dt.strftime("%H:%M")
                all_times.add(time_str)
            except (ValueError, TypeError):
                pass

    all_times = sorted(all_times)

    # Classify periods
    periods = set()
    is_full_day = False

    if not all_times:
        is_full_day = True
    else:
        for time_str in all_times:
            try:
                hour = int(time_str.split(":")[0])
                periods.add(classify_period(hour))
            except (ValueError, IndexError):
                pass

    periods = sorted(periods)

    # Merge any differing conditions (if any - analysis showed minimal variation)
    merged_conditions = primary.get("conditions", "")
    for dup in duplicates:
        dup_cond = dup.get("conditions", "")
        if dup_cond and dup_cond != merged_conditions:
            # Keep the longer/more detailed one
            if len(dup_cond) > len(merged_conditions or ""):
                merged_conditions = dup_cond

    result = {
        "primary_id": primary["id"],
        "duplicate_ids": [d["id"] for d in duplicates],
        "timings": all_times,
        "periods": periods,
        "is_full_day": is_full_day,
        "merged_conditions": merged_conditions,
    }

    if not dry_run:
        # Update primary record with merged data
        cursor.execute("""
            UPDATE events
            SET timings_json = ?,
                periods_json = ?,
                is_full_day = ?,
                conditions = ?
            WHERE id = ?
        """, (
            json.dumps(all_times),
            json.dumps(periods),
            1 if is_full_day else 0,
            merged_conditions,
            primary["id"]
        ))

        # Delete duplicates
        if duplicates:
            dup_ids = [d["id"] for d in duplicates]
            cursor.execute(
                f"DELETE FROM events WHERE id IN ({','.join('?' * len(dup_ids))})",
                dup_ids
            )

        conn.commit()
        logger.info(f"Merged: '{primary['title'][:50]}...' - kept ID {primary['id']}, deleted {len(duplicates)} duplicates")

    return result


def run_migration(sample_size: int | None = None, dry_run: bool = True) -> dict:
    """Run the deduplication migration.

    Args:
        sample_size: If set, only process this many groups (for testing)
        dry_run: If True, don't make any changes, just report what would happen

    Returns:
        Statistics about the migration
    """
    conn = sqlite3.connect(DB_PATH)

    try:
        # Step 1: Add new columns
        if not dry_run:
            add_new_columns(conn)
        else:
            logger.info("[DRY RUN] Would add columns: timings_json, periods_json, is_full_day")

        # Step 2: Find duplicate groups
        groups = find_duplicate_groups(conn, limit=sample_size)
        logger.info(f"Found {len(groups)} groups with duplicates")

        if not groups:
            return {"groups": 0, "rows_to_delete": 0, "status": "no_duplicates"}

        # Step 3: Process each group
        total_deleted = 0
        merge_results = []

        for i, group in enumerate(groups):
            result = merge_event_group(conn, group, dry_run=dry_run)
            merge_results.append(result)
            total_deleted += len(result["duplicate_ids"])

            if (i + 1) % 10 == 0:
                logger.info(f"Processed {i + 1}/{len(groups)} groups...")

        # Step 4: Report statistics
        stats = {
            "groups_processed": len(groups),
            "rows_deleted": total_deleted,
            "dry_run": dry_run,
            "sample_size": sample_size,
            "examples": merge_results[:5]  # First 5 examples
        }

        action = "Would delete" if dry_run else "Deleted"
        logger.info(f"\n{'='*60}")
        logger.info(f"Migration {'Preview' if dry_run else 'Complete'}")
        logger.info(f"{'='*60}")
        logger.info(f"Groups with duplicates: {len(groups)}")
        logger.info(f"{action} {total_deleted} duplicate rows")
        logger.info(f"{'='*60}\n")

        return stats

    finally:
        conn.close()


def verify_migration(conn: sqlite3.Connection = None) -> dict:
    """Verify the migration was successful."""
    close_conn = False
    if conn is None:
        conn = sqlite3.connect(DB_PATH)
        close_conn = True

    try:
        cursor = conn.cursor()

        # Count total events
        cursor.execute("SELECT COUNT(*) FROM events")
        total = cursor.fetchone()[0]

        # Count events with timings_json
        cursor.execute("SELECT COUNT(*) FROM events WHERE timings_json IS NOT NULL")
        with_timings = cursor.fetchone()[0]

        # Check for remaining duplicates
        cursor.execute("""
            SELECT COUNT(*) FROM (
                SELECT title, city, DATE(start_date)
                FROM events
                WHERE start_date IS NOT NULL
                GROUP BY title, city, DATE(start_date)
                HAVING COUNT(*) > 1
            )
        """)
        remaining_dups = cursor.fetchone()[0]

        return {
            "total_events": total,
            "events_with_timings": with_timings,
            "remaining_duplicate_groups": remaining_dups
        }
    finally:
        if close_conn:
            conn.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Deduplicate multi-showtime events")
    parser.add_argument("--sample", type=int, help="Process only N groups (for testing)")
    parser.add_argument("--execute", action="store_true", help="Actually perform the migration (default: dry run)")
    parser.add_argument("--verify", action="store_true", help="Verify migration status")

    args = parser.parse_args()

    if args.verify:
        stats = verify_migration()
        print(f"\nVerification Results:")
        print(f"  Total events: {stats['total_events']}")
        print(f"  Events with timings: {stats['events_with_timings']}")
        print(f"  Remaining duplicate groups: {stats['remaining_duplicate_groups']}")
    else:
        dry_run = not args.execute

        if dry_run:
            print("\n" + "="*60)
            print("DRY RUN MODE - No changes will be made")
            print("Use --execute to actually perform the migration")
            print("="*60 + "\n")

        stats = run_migration(sample_size=args.sample, dry_run=dry_run)

        print("\nMigration Statistics:")
        print(f"  Groups processed: {stats['groups_processed']}")
        print(f"  Rows {'would be' if dry_run else ''} deleted: {stats['rows_deleted']}")

        if stats.get("examples"):
            print("\nExample merges:")
            for ex in stats["examples"][:3]:
                print(f"  - Primary ID {ex['primary_id']}: {len(ex['timings'])} timings, periods: {ex['periods']}")
