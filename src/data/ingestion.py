"""Data ingestion pipeline with dynamic time window to ensure minimum event count."""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from src.data.api_client import OpenAgendaClient
from src.data.models import Event
from src.data.processor import EventProcessor
from src.data.storage import EventStorage
from src.data.scraper import EventScraper
from src.models.vector_store import EventVectorStore

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
        self.scraper = EventScraper()
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
        filters = {"order_by": "firstdate_begin desc", "where": 'location_region like "Île-de-France"'}

        target_fetch = max(self.min_events * 2, 2000)

        raw_records = client.fetch_all_events(
            max_events=target_fetch,
            batch_size=batch_size,
            filters=filters,
        )

        if not raw_records:
            logger.warning("No records fetched from API with IDF filter")
            return []

        # 2. Process records into granular, deduplicated Event objects
        # The processor now handles parsing timings and cross-record deduplication
        all_events = self.processor.process_records(raw_records)
        logger.info(f"Processed into {len(all_events)} granular, unique event instances")

        # 3. Filter for Île-de-France
        idf_events = self.processor.filter_ile_de_france_events(all_events)

        # 4. Redistribute dates seasonally
        # We do this BEFORE selection so we select from the correct target timeframe
        transformed_events = self.processor.redistribute_events_seasonally(
            idf_events, start_date=datetime.now(timezone.utc)
        )

        # 5. Select top N events
        selected_events = transformed_events[: self.min_events]

        if len(selected_events) < self.min_events:
            logger.warning(
                f"Only found {len(selected_events)} unique instances "
                f"(target: {self.min_events}). Using all available."
            )
        else:
            logger.info(f"Selected top {len(selected_events)} unique event instances")

        return selected_events

    async def ingest(self, force_refresh: bool = False) -> dict[str, Any]:
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
            "scraped_count": 0,
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
            # We filter for only NEW events to avoid re-scraping existing ones
            # Note: event_id is now base_id + _index, ensuring granular instances are unique
            existing_ids = self.storage.get_existing_event_ids()
            new_events = [e for e in transformed_events if e.event_id not in existing_ids]

            if new_events:
                logger.info(f"Adding {len(new_events)} granular event instances...")
                # Scrape in batches
                BATCH_SIZE = 10
                for i in range(0, len(new_events), BATCH_SIZE):
                    batch = new_events[i : i + BATCH_SIZE]
                    # Only scrape if URL exists and is not already scraped
                    tasks = [self.scraper.scrape_url(e.url) for e in batch if e.url]
                    if tasks:
                        results = await asyncio.gather(*tasks)
                        # Map results back to events that have URLs
                        urls_in_batch = [e.url for e in batch if e.url]
                        url_to_content = dict(zip(urls_in_batch, results))

                        for event in batch:
                            if event.url in url_to_content and url_to_content[event.url]:
                                event.scraped_content = url_to_content[event.url]
                                stats["scraped_count"] += 1

                # Add to DB
                new_count = self.storage.add_events_bulk(new_events)
                stats["new_events_added"] = new_count

                # REBUILD INDEX if new events were added
                if new_count > 0:
                    logger.info("Rebuilding FAISS index with new events...")
                    with EventVectorStore(storage=self.storage) as vector_store:
                        all_events = self.storage.get_all_events()
                        vector_store.build_index(all_events)
                        vector_store.save_index()
            else:
                logger.info("No new events to scrape or add.")

            stats["total_after_ingest"] = self.storage.count_events()
            stats["target_met"] = stats["total_after_ingest"] >= self.min_events

            # Summary
            stats["end_time"] = datetime.now()
            stats["duration_seconds"] = (stats["end_time"] - stats["start_time"]).total_seconds()

            logger.info("=" * 80)
            logger.info("Ingestion Summary:")
            logger.info(f"  New events added & scraped: {stats['new_events_added']}")
            logger.info(f"  Total in storage: {stats['total_after_ingest']}")
            logger.info(f"  Duration: {stats['duration_seconds']:.1f}s")
            logger.info("=" * 80)

            return stats

        except Exception as e:
            logger.error(f"Ingestion failed: {e}", exc_info=True)
            stats["error"] = str(e)
            stats["end_time"] = datetime.now()
            return stats


async def run_ingestion(
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
    pipeline = DataIngestionPipeline(min_events=min_events)
    stats = await pipeline.ingest(force_refresh=force_refresh)

    return stats


if __name__ == "__main__":
    import sys

    force_refresh = "--force" in sys.argv or "-f" in sys.argv
    asyncio.run(run_ingestion(force_refresh=force_refresh))
