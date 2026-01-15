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
        initial_months: int = 12,
        max_months: int = 36,
    ) -> None:
        """Initialize ingestion pipeline.

        Args:
            storage: EventStorage instance (creates new if None)
            min_events: Minimum number of events required (hard constraint)
            initial_months: Initial time window in months from now
            max_months: Maximum time window in months (safety limit)
        """
        self.storage = storage or EventStorage()
        self.processor = EventProcessor()
        self.min_events = min_events
        self.initial_months = initial_months
        self.max_months = max_months

    def fetch_events_with_dynamic_window(
        self,
        client: OpenAgendaClient,
        batch_size: int = 100,
    ) -> tuple[list[Event], datetime, datetime]:
        """Fetch events with dynamic time window to meet minimum count.

        Starts with initial_months window, extends if needed to reach min_events.

        Args:
            client: OpenAgendaClient instance
            batch_size: Events per API request

        Returns:
            Tuple of (filtered_events, start_date, end_date)
        """
        now = datetime.now()
        months_to_try = self.initial_months
        filtered_events: list[Event] = []

        logger.info(
            f"Starting data fetch with dynamic window "
            f"(target: {self.min_events} events minimum)"
        )

        while months_to_try <= self.max_months:
            end_date = now + timedelta(days=30 * months_to_try)

            logger.info(
                f"Attempting fetch with {months_to_try}-month window "
                f"({now.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')})"
            )

            # Fetch raw records from API
            # Note: OpenAgenda API doesn't support date filtering in query params
            # We need to fetch a large batch and filter client-side
            max_fetch = min(self.min_events * 10, 5000)  # Fetch 10x minimum or 5000 max
            records = client.fetch_all_events(
                max_events=max_fetch,
                batch_size=batch_size,
            )

            if not records:
                logger.warning("No records fetched from API")
                return [], now, end_date

            # Process records
            all_events = self.processor.process_records(records)
            logger.info(f"Processed {len(all_events)} events from {len(records)} records")

            # Apply filters: Île-de-France + date range
            idf_events = self.processor.filter_ile_de_france_events(all_events)
            filtered_events = self.processor.filter_by_date_range(
                idf_events,
                start_date=now,
                end_date=end_date,
            )

            event_count = len(filtered_events)
            logger.info(
                f"After filtering (Île-de-France + {months_to_try} months): "
                f"{event_count} events"
            )

            # Check if we have enough events
            if event_count >= self.min_events:
                logger.info(
                    f"✓ Achieved minimum: {event_count} events "
                    f"(target: {self.min_events})"
                )
                return filtered_events, now, end_date

            # Need more events - extend window
            logger.warning(
                f"Only {event_count} events found "
                f"(need {self.min_events - event_count} more)"
            )

            if months_to_try >= self.max_months:
                logger.error(
                    f"Reached maximum time window ({self.max_months} months) "
                    f"with only {event_count} events"
                )
                return filtered_events, now, end_date

            # Extend by 6 months
            months_to_try += 6
            logger.info(f"Extending time window to {months_to_try} months...")

        logger.error(
            f"Failed to reach minimum of {self.min_events} events "
            f"even with {self.max_months}-month window"
        )
        return filtered_events, now, now + timedelta(days=30 * self.max_months)

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
            "fetched_count": 0,
            "filtered_count": 0,
            "new_events_added": 0,
            "total_after_ingest": 0,
            "time_window_months": 0,
            "start_date": None,
            "end_date": None,
            "min_events_target": self.min_events,
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

            # Fetch events with dynamic window
            with OpenAgendaClient() as client:
                filtered_events, start_date, end_date = (
                    self.fetch_events_with_dynamic_window(client)
                )

            stats["filtered_count"] = len(filtered_events)
            stats["start_date"] = start_date.isoformat()
            stats["end_date"] = end_date.isoformat()
            stats["time_window_months"] = (
                (end_date - start_date).days / 30
            )

            if not filtered_events:
                logger.error("No events to ingest after filtering")
                stats["target_met"] = False
                return stats

            # Store events (deduplication handled by storage layer)
            new_count = self.storage.add_events_bulk(filtered_events)
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
            logger.info(f"  Events fetched: {stats['filtered_count']}")
            logger.info(f"  New events added: {stats['new_events_added']}")
            logger.info(f"  Total in storage: {stats['total_after_ingest']}")
            logger.info(f"  Time window: {stats['time_window_months']:.1f} months")
            logger.info(f"  Date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
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
