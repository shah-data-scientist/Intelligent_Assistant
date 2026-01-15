"""Data ingestion pipeline with dynamic time window to ensure minimum event count."""

import logging
from datetime import datetime, timedelta
from typing import Any

from src.config import settings
from src.data.api_client import OpenAgendaClient
from src.data.models import Event
from src.data.processor import EventProcessor
from src.data.storage import EventStorage

logger = logging.getLogger(__name__)


class DataIngestionPipeline:
    """Pipeline for fetching, processing, and storing events."""

    def __init__(
        self,
        storage: EventStorage | None = None,
        min_events: int = 1000,
    ) -> None:
        """Initialize ingestion pipeline.

        Args:
            storage: EventStorage instance (creates new if None)
            min_events: Target number of events
        """
        self.storage = storage or EventStorage()
        self.processor = EventProcessor()
        self.min_events = min_events

    def fetch_and_transform_events(
        self,
        client: OpenAgendaClient,
        batch_size: int = 100,
    ) -> list[Event]:
        """Fetch recent events, filter for IDF, and redistribute dates.

        Args:
            client: OpenAgendaClient instance
            batch_size: Events per API request

        Returns:
            List of transformed events
        """
        logger.info("Starting fetch of recent events...")
        
        # 1. Fetch recent events from API
        # Use ODSQL 'where' clause for filtering. 
        # Note: double quotes for string literals in ODSQL.
        filters = {
            "order_by": "firstdate_begin desc",
            "where": 'location_region like "Île-de-France"'
        }
        
        # We need 1000 events. Fetching 2000 should be safe if the filter works.
        # If the filter fails (e.g. wrong field name), we might get 0 or non-IDF events.
        # But this is the most efficient way.
        target_fetch = max(self.min_events * 2, 2000)
        
        raw_records = client.fetch_all_events(
            max_events=target_fetch,
            batch_size=batch_size,
            filters=filters,
        )
        
        if not raw_records:
            logger.warning("No records fetched from API with IDF filter")
            return []

        # 2. Process records into Event objects
        all_events = self.processor.process_records(raw_records)
        logger.info(f"Processed {len(all_events)} valid events")

        # 3. Filter for Île-de-France (double-check locally in case API filter was loose)
        idf_events = self.processor.filter_ile_de_france_events(all_events)
        
        # 4. Select top N events
        selected_events = idf_events[:self.min_events]
        
        if len(selected_events) < self.min_events:
            logger.warning(
                f"Only found {len(selected_events)} IDF events "
                f"(target: {self.min_events}). Using all available."
            )
        else:
            logger.info(f"Selected top {len(selected_events)} IDF events")

        # 5. Redistribute dates seasonally
        # Transform dates to [Now, Now + 365 days]
        transformed_events = self.processor.redistribute_events_seasonally(
            selected_events,
            start_date=datetime.now()
        )
        
        return transformed_events

    def ingest(self, force_refresh: bool = False) -> dict[str, Any]:
        """Run full ingestion pipeline.

        Args:
            force_refresh: If True, clears existing data and refetches

        Returns:
            Dictionary with ingestion statistics
        """
        stats = {
            "start_time": datetime.now(),
            "existing_count": 0,
            "fetched_raw": 0,
            "selected_count": 0,
            "new_events_added": 0,
            "total_after_ingest": 0,
            "target_met": False,
        }

        try:
            # Check existing count
            stats["existing_count"] = self.storage.count_events()
            logger.info(f"Existing events in storage: {stats['existing_count']}")

            if force_refresh:
                logger.warning("Force refresh requested - clearing existing data")
                self.storage.clear_all()
                stats["existing_count"] = 0

            # Fetch and transform
            with OpenAgendaClient() as client:
                transformed_events = self.fetch_and_transform_events(client)

            stats["selected_count"] = len(transformed_events)

            if not transformed_events:
                logger.error("No events to ingest after processing")
                return stats

            # Store events
            new_count = self.storage.add_events_bulk(transformed_events)
            stats["new_events_added"] = new_count
            stats["total_after_ingest"] = self.storage.count_events()
            stats["target_met"] = stats["total_after_ingest"] >= self.min_events

            # Summary
            stats["end_time"] = datetime.now()
            stats["duration_seconds"] = (
                stats["end_time"] - stats["start_time"]
            ).total_seconds()

            logger.info("=" * 80)
            logger.info("Ingestion Summary:")
            logger.info(f"  Events selected & transformed: {stats['selected_count']}")
            logger.info(f"  New events added: {stats['new_events_added']}")
            logger.info(f"  Total in storage: {stats['total_after_ingest']}")
            logger.info(f"  Target ({self.min_events} events): {'✓ MET' if stats['target_met'] else '✗ NOT MET'}")
            logger.info(f"  Duration: {stats['duration_seconds']:.1f}s")
            logger.info("=" * 80)

            return stats

        except Exception as e:
            logger.error(f"Ingestion failed: {e}", exc_info=True)
            stats["error"] = str(e)
            stats["end_time"] = datetime.now()
            return stats


def run_ingestion(
    force_refresh: bool = False,
    min_events: int = 1000,
) -> dict[str, Any]:
    """CLI entry point for data ingestion.

    Args:
        force_refresh: Clear existing data before ingestion
        min_events: Minimum number of events required

    Returns:
        Ingestion statistics
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    logger.info("Starting data ingestion pipeline")
    logger.info(f"Minimum events target: {min_events}")
    logger.info(f"Force refresh: {force_refresh}")

    pipeline = DataIngestionPipeline(min_events=min_events)
    stats = pipeline.ingest(force_refresh=force_refresh)

    return stats


if __name__ == "__main__":
    import sys

    force_refresh = "--force" in sys.argv or "-f" in sys.argv
    run_ingestion(force_refresh=force_refresh)
