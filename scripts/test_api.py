"""Test script to analyze OpenAgenda API data."""

import logging
import sys
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data.api_client import OpenAgendaClient
from src.data.processor import EventProcessor

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def analyze_api_data() -> None:
    """Analyze data available from OpenAgenda API."""
    logger.info("=" * 80)
    logger.info("OpenAgenda API Data Analysis")
    logger.info("=" * 80)

    try:
        # Fetch sample data
        with OpenAgendaClient() as client:
            logger.info("\n1. Fetching sample data (100 records)...")
            records = client.fetch_events(limit=100)

            if not records:
                logger.warning("No records fetched!")
                return

            logger.info(f"✓ Fetched {len(records)} records")

            # Process records
            processor = EventProcessor()
            events = processor.process_records(records)
            logger.info(f"✓ Successfully processed {len(events)}/{len(records)} events")

            if not events:
                logger.warning("No events after processing!")
                return

            # Analyze date range
            logger.info("\n2. Date Range Analysis:")
            events_with_dates = [e for e in events if e.start_date]
            if events_with_dates:
                dates = [e.start_date for e in events_with_dates]
                min_date = min(dates)
                max_date = max(dates)
                now = datetime.now()

                logger.info(f"   Earliest event: {min_date.strftime('%Y-%m-%d')}")
                logger.info(f"   Latest event:   {max_date.strftime('%Y-%m-%d')}")
                logger.info(f"   Current date:   {now.strftime('%Y-%m-%d')}")
                logger.info(f"   Date span:      {(max_date - min_date).days} days")

                # Past vs upcoming
                past = [e for e in events_with_dates if e.start_date < now]
                upcoming = [e for e in events_with_dates if e.start_date >= now]
                logger.info(f"   Past events:    {len(past)} ({len(past)/len(events_with_dates)*100:.1f}%)")
                logger.info(f"   Upcoming events: {len(upcoming)} ({len(upcoming)/len(events_with_dates)*100:.1f}%)")
            else:
                logger.info("   No events with dates found")

            # Analyze locations
            logger.info("\n3. Geographic Distribution:")
            events_with_location = [e for e in events if e.location and e.location.city]
            if events_with_location:
                cities = {}
                for event in events_with_location:
                    city = event.location.city.lower()
                    cities[city] = cities.get(city, 0) + 1

                logger.info(f"   Total with location: {len(events_with_location)}")
                logger.info("   Top cities:")
                for city, count in sorted(cities.items(), key=lambda x: x[1], reverse=True)[:10]:
                    logger.info(f"     - {city}: {count} events")

                # Paris filtering
                paris_events = processor.filter_paris_events(events)
                logger.info(f"\n   Paris events: {len(paris_events)} ({len(paris_events)/len(events)*100:.1f}%)")
            else:
                logger.info("   No events with location found")

            # Category distribution
            logger.info("\n4. Category Distribution:")
            categories = {}
            for event in events:
                cat = event.category or "unknown"
                categories[cat] = categories.get(cat, 0) + 1

            logger.info(f"   Total categories: {len(categories)}")
            logger.info("   Top categories:")
            for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True)[:10]:
                logger.info(f"     - {cat}: {count} events")

            # Sample event
            logger.info("\n5. Sample Event:")
            if events:
                sample = events[0]
                logger.info(f"   Title: {sample.title}")
                logger.info(f"   Category: {sample.category}")
                if sample.location:
                    logger.info(f"   City: {sample.location.city}")
                if sample.start_date:
                    logger.info(f"   Date: {sample.start_date.strftime('%Y-%m-%d %H:%M')}")
                logger.info(f"   URL: {sample.url}")

            # Test one-year filter
            logger.info("\n6. One-Year Window Test:")
            now = datetime.now()
            from datetime import timedelta
            one_year_later = now + timedelta(days=365)

            filtered = processor.filter_by_date_range(
                events,
                start_date=now,
                end_date=one_year_later
            )
            logger.info(f"   Events in next 12 months: {len(filtered)}")

            # Combined filter (Paris + 1 year)
            paris_events = processor.filter_paris_events(events)
            paris_upcoming = processor.filter_by_date_range(
                paris_events,
                start_date=now,
                end_date=one_year_later
            )
            logger.info(f"   Paris events in next 12 months: {len(paris_upcoming)}")

            logger.info("\n" + "=" * 80)
            logger.info("Analysis Complete")
            logger.info("=" * 80)

    except Exception as e:
        logger.error(f"Error during analysis: {e}", exc_info=True)


if __name__ == "__main__":
    analyze_api_data()
