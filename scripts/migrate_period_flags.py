"""Migration script to populate period filter flags for existing events.

This script sets has_morning, has_afternoon, has_evening flags based on
the existing timings_json and periods_json data.
"""

import json
import logging
import sqlite3
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DB_PATH = Path("./data/events.db")


def add_period_columns(conn: sqlite3.Connection) -> None:
    """Add period filter columns if they don't exist."""
    cursor = conn.cursor()

    cursor.execute("PRAGMA table_info(events)")
    existing_cols = {row[1] for row in cursor.fetchall()}

    new_columns = [
        ("has_morning", "INTEGER"),
        ("has_afternoon", "INTEGER"),
        ("has_evening", "INTEGER"),
    ]

    for col_name, col_type in new_columns:
        if col_name not in existing_cols:
            logger.info(f"Adding column: {col_name}")
            cursor.execute(f"ALTER TABLE events ADD COLUMN {col_name} {col_type}")

    # Create indexes for fast filtering
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_has_morning ON events(has_morning)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_has_afternoon ON events(has_afternoon)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_has_evening ON events(has_evening)")

    conn.commit()


def classify_period(hour: int) -> str:
    """Classify time into period of day."""
    if hour < 12:
        return "matin"
    elif hour < 18:
        return "après-midi"
    else:
        return "soir"


def populate_period_flags(conn: sqlite3.Connection, dry_run: bool = True) -> dict:
    """Populate period flags based on existing timings data."""
    cursor = conn.cursor()

    # Get all events
    cursor.execute("""
        SELECT id, timings_json, periods_json, is_full_day, start_date
        FROM events
    """)

    updates = []
    stats = {"morning": 0, "afternoon": 0, "evening": 0, "full_day": 0}

    for row in cursor.fetchall():
        event_id, timings_json, periods_json, is_full_day, start_date = row

        has_morning = False
        has_afternoon = False
        has_evening = False

        # If full day, set all flags
        if is_full_day:
            has_morning = True
            has_afternoon = True
            has_evening = True
            stats["full_day"] += 1
        # If has periods_json, use it directly
        elif periods_json:
            try:
                periods = json.loads(periods_json)
                has_morning = "matin" in periods
                has_afternoon = "après-midi" in periods
                has_evening = "soir" in periods
            except json.JSONDecodeError:
                pass
        # If has timings_json, classify each time
        elif timings_json:
            try:
                timings = json.loads(timings_json)
                for time_str in timings:
                    hour = int(time_str.split(":")[0])
                    period = classify_period(hour)
                    if period == "matin":
                        has_morning = True
                    elif period == "après-midi":
                        has_afternoon = True
                    else:
                        has_evening = True
            except (json.JSONDecodeError, ValueError, IndexError):
                pass
        # Fallback to start_date
        elif start_date:
            try:
                # start_date format: "2026-02-15 10:00:00"
                hour = int(start_date.split(" ")[1].split(":")[0])
                period = classify_period(hour)
                if period == "matin":
                    has_morning = True
                elif period == "après-midi":
                    has_afternoon = True
                else:
                    has_evening = True
            except (ValueError, IndexError, AttributeError):
                pass

        # Track stats
        if has_morning:
            stats["morning"] += 1
        if has_afternoon:
            stats["afternoon"] += 1
        if has_evening:
            stats["evening"] += 1

        updates.append((
            1 if has_morning else None,
            1 if has_afternoon else None,
            1 if has_evening else None,
            event_id
        ))

    if not dry_run:
        cursor.executemany("""
            UPDATE events
            SET has_morning = ?, has_afternoon = ?, has_evening = ?
            WHERE id = ?
        """, updates)
        conn.commit()
        logger.info(f"Updated {len(updates)} events with period flags")

    return {
        "total_events": len(updates),
        "with_morning": stats["morning"],
        "with_afternoon": stats["afternoon"],
        "with_evening": stats["evening"],
        "full_day": stats["full_day"],
        "dry_run": dry_run
    }


def run_migration(dry_run: bool = True) -> dict:
    """Run the period flags migration."""
    conn = sqlite3.connect(DB_PATH)

    try:
        # Add columns if needed
        if not dry_run:
            add_period_columns(conn)
        else:
            logger.info("[DRY RUN] Would add columns: has_morning, has_afternoon, has_evening")

        # Populate flags
        stats = populate_period_flags(conn, dry_run=dry_run)

        action = "Would update" if dry_run else "Updated"
        logger.info(f"\n{'='*60}")
        logger.info(f"Period Flags Migration {'Preview' if dry_run else 'Complete'}")
        logger.info(f"{'='*60}")
        logger.info(f"Total events: {stats['total_events']}")
        logger.info(f"Events with morning showtime: {stats['with_morning']}")
        logger.info(f"Events with afternoon showtime: {stats['with_afternoon']}")
        logger.info(f"Events with evening showtime: {stats['with_evening']}")
        logger.info(f"Full day events: {stats['full_day']}")
        logger.info(f"{'='*60}\n")

        return stats

    finally:
        conn.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Populate period filter flags")
    parser.add_argument("--execute", action="store_true", help="Actually perform the migration")

    args = parser.parse_args()
    dry_run = not args.execute

    if dry_run:
        print("\n" + "="*60)
        print("DRY RUN MODE - No changes will be made")
        print("Use --execute to actually perform the migration")
        print("="*60 + "\n")

    stats = run_migration(dry_run=dry_run)

    print(f"\nMigration Statistics:")
    print(f"  Total events: {stats['total_events']}")
    print(f"  Morning events: {stats['with_morning']}")
    print(f"  Afternoon events: {stats['with_afternoon']}")
    print(f"  Evening events: {stats['with_evening']}")
