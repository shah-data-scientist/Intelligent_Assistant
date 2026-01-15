"""OpenAgenda API client for fetching cultural events."""

import logging
from typing import Any

import httpx

from src.config import settings

logger = logging.getLogger(__name__)


class OpenAgendaAPIError(Exception):
    """Exception raised for OpenAgenda API errors."""

    pass


class OpenAgendaClient:
    """Client for interacting with OpenAgenda API."""

    def __init__(
        self,
        base_url: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        """Initialize OpenAgenda API client.

        Args:
            base_url: Base URL for OpenAgenda API. If None, uses settings.
            timeout: Request timeout in seconds
        """
        self.base_url = base_url or settings.openagenda_base_url
        self.timeout = timeout
        self._client = httpx.Client(timeout=timeout)

    def __enter__(self) -> "OpenAgendaClient":
        """Context manager entry."""
        return self

    def __exit__(self, *args: Any) -> None:
        """Context manager exit."""
        self.close()

    def close(self) -> None:
        """Close the HTTP client."""
        self._client.close()

    def fetch_events(
        self,
        limit: int | None = None,
        offset: int = 0,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch events from OpenAgenda API.

        Args:
            limit: Maximum number of events to fetch. If None, uses settings.
            offset: Number of events to skip
            filters: Additional query filters (e.g., city, date range)

        Returns:
            List of event records

        Raises:
            OpenAgendaAPIError: If API request fails
        """
        limit = limit or settings.max_events_to_fetch

        params: dict[str, Any] = {
            "limit": limit,
            "offset": offset,
        }

        if filters:
            params.update(filters)

        try:
            logger.info(f"Fetching events from OpenAgenda API (limit={limit}, offset={offset})")
            response = self._client.get(self.base_url, params=params)
            response.raise_for_status()

            data = response.json()

            # Extract records from response (Opendatasoft v2.1 format)
            records = data.get("results", [])
            total_count = data.get("total_count", 0)
            logger.info(
                f"Successfully fetched {len(records)} events "
                f"(total available: {total_count:,})"
            )

            return records

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching events: {e}")
            raise OpenAgendaAPIError(f"HTTP {e.response.status_code}: {e.response.text}") from e

        except httpx.RequestError as e:
            logger.error(f"Request error fetching events: {e}")
            raise OpenAgendaAPIError(f"Request failed: {str(e)}") from e

        except Exception as e:
            logger.error(f"Unexpected error fetching events: {e}")
            raise OpenAgendaAPIError(f"Unexpected error: {str(e)}") from e

    def fetch_all_events(
        self,
        max_events: int | None = None,
        batch_size: int = 100,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch all available events using pagination.

        Args:
            max_events: Maximum total events to fetch. If None, fetches all.
            batch_size: Number of events per API request
            filters: Additional query filters

        Returns:
            List of all event records

        Raises:
            OpenAgendaAPIError: If API request fails
        """
        all_records: list[dict[str, Any]] = []
        offset = 0
        max_events = max_events or settings.max_events_to_fetch

        logger.info(f"Starting to fetch all events (max={max_events})")

        while len(all_records) < max_events:
            remaining = max_events - len(all_records)
            limit = min(batch_size, remaining)

            records = self.fetch_events(limit=limit, offset=offset, filters=filters)

            if not records:
                logger.info("No more events to fetch")
                break

            all_records.extend(records)
            offset += len(records)

            # If we got fewer records than requested, we've reached the end
            if len(records) < limit:
                logger.info("Reached end of available events")
                break

        logger.info(f"Fetched total of {len(all_records)} events")
        return all_records


def main() -> None:
    """CLI entry point for testing API client."""
    logging.basicConfig(level=logging.INFO)

    with OpenAgendaClient() as client:
        # Fetch a sample of events
        events = client.fetch_events(limit=20)
        logger.info(f"Sample fetch: {len(events)} events")

        if events:
            # Display first event as example
            import json
            logger.info("First event:")
            logger.info(json.dumps(events[0], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
