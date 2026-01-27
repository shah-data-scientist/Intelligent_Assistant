#!/usr/bin/env python
"""Migration script to populate price_label and age_label columns.

This script computes the derived display labels from the raw fields:
- price_label: derived from conditions field
- age_label: derived from age_min/age_max fields

Run once to populate existing records. New records will have these fields
set during ingestion via EventProcessor.
"""

import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from src.data.storage import EventStorage

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def compute_price_label(conditions: str | None) -> str:
    """Compute display-ready price label from conditions field."""
    if not conditions:
        return "Non spécifié"

    cond_lower = conditions.lower()
    if "gratuit" in cond_lower or "free" in cond_lower or "entrée libre" in cond_lower:
        return "Gratuit"
    elif "€" in conditions or "euro" in cond_lower:
        # Keep first 50 chars of price info
        return conditions[:50]
    else:
        return conditions[:50] if conditions else "Non spécifié"


def compute_age_label(age_min: int | None, age_max: int | None) -> str:
    """Compute display-ready age label from age_min/age_max fields."""
    if age_min is not None and age_max is not None:
        if age_min == 0 and age_max >= 99:
            return "Tout public"
        else:
            return f"{age_min}-{age_max} ans"
    elif age_min is not None:
        return f"Dès {age_min} ans"
    elif age_max is not None:
        return f"Jusqu'à {age_max} ans"
    else:
        return "Tout public"


def migrate_display_labels():
    """Populate price_label and age_label for all existing records."""
    storage = EventStorage()

    with storage.engine.connect() as conn:
        # First, ensure columns exist (handled by _ensure_schema, but be safe)
        columns = conn.execute(text("PRAGMA table_info(events)")).fetchall()
        column_names = [col[1] for col in columns]

        if "price_label" not in column_names:
            logger.info("Adding price_label column")
            conn.execute(text("ALTER TABLE events ADD COLUMN price_label VARCHAR(100)"))

        if "age_label" not in column_names:
            logger.info("Adding age_label column")
            conn.execute(text("ALTER TABLE events ADD COLUMN age_label VARCHAR(100)"))

        conn.commit()

        # Fetch all events that need migration
        result = conn.execute(text("""
            SELECT event_id, conditions, age_min, age_max, price_label, age_label
            FROM events
        """)).fetchall()

        logger.info(f"Found {len(result)} events to process")

        updated = 0
        for row in result:
            event_id = row[0]
            conditions = row[1]
            age_min = row[2]
            age_max = row[3]
            current_price = row[4]
            current_age = row[5]

            # Compute labels
            new_price_label = compute_price_label(conditions)
            new_age_label = compute_age_label(age_min, age_max)

            # Only update if different (avoid unnecessary writes)
            if current_price != new_price_label or current_age != new_age_label:
                conn.execute(
                    text("""
                        UPDATE events
                        SET price_label = :price_label, age_label = :age_label
                        WHERE event_id = :event_id
                    """),
                    {
                        "price_label": new_price_label,
                        "age_label": new_age_label,
                        "event_id": event_id
                    }
                )
                updated += 1

        conn.commit()
        logger.info(f"Migration complete: {updated} events updated")

        # Show sample results
        sample = conn.execute(text("""
            SELECT title, conditions, price_label, age_min, age_max, age_label
            FROM events
            LIMIT 5
        """)).fetchall()

        logger.info("\nSample results:")
        for row in sample:
            logger.info(f"  {row[0][:40]}: price={row[2]}, age={row[5]}")


if __name__ == "__main__":
    migrate_display_labels()
