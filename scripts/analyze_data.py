"""Analyze ingested event data."""

import logging
from collections import Counter
from datetime import datetime

from src.data.storage import EventStorage

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

def analyze_data():
    with EventStorage() as storage:
        events = storage.get_all_events()
        
    logger.info(f"Total events analyzed: {len(events)}")
    
    if not events:
        logger.warning("No events found.")
        return

    # 1. Category Distribution
    categories = [e.category or "Unknown" for e in events]
    cat_counts = Counter(categories)
    
    logger.info("\n--- Category Distribution (Top 10) ---")
    for cat, count in cat_counts.most_common(10):
        logger.info(f"{cat}: {count}")

    # 2. Geographic Distribution (City)
    cities = [e.location.city for e in events if e.location and e.location.city]
    city_counts = Counter(cities)
    
    logger.info("\n--- Geographic Distribution (Top 10 Cities) ---")
    for city, count in city_counts.most_common(10):
        logger.info(f"{city}: {count}")

    # 3. Temporal Distribution (Month)
    dates = [e.start_date for e in events if e.start_date]
    months = [d.strftime("%Y-%m") for d in dates]
    month_counts = Counter(months)
    
    logger.info("\n--- Temporal Distribution (by Month) ---")
    for month in sorted(month_counts.keys()):
        logger.info(f"{month}: {month_counts[month]}")

    # 4. Tags Analysis
    all_tags = []
    for e in events:
        if e.tags:
            all_tags.extend(e.tags)
    tag_counts = Counter(all_tags)
    
    logger.info("\n--- Top Tags ---")
    for tag, count in tag_counts.most_common(10):
        logger.info(f"{tag}: {count}")

if __name__ == "__main__":
    analyze_data()
