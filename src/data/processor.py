"""Data processing and normalization for cultural events."""

import logging
from datetime import datetime
from typing import Any

from src.data.models import Event, EventLocation

logger = logging.getLogger(__name__)


class EventProcessor:
    """Process and normalize event data from OpenAgenda API."""

    @staticmethod
    def parse_date(date_str: str | None) -> datetime | None:
        """Parse date string to datetime object.

        Args:
            date_str: Date string in various formats

        Returns:
            Parsed datetime or None if parsing fails
        """
        if not date_str:
            return None

        # Handle timezone offset (e.g., +00:00, +01:00)
        # Remove timezone info for simple parsing
        if "+" in date_str or date_str.endswith("Z"):
            # Remove timezone suffix for parsing
            date_str_clean = date_str.split("+")[0].replace("Z", "")
        else:
            date_str_clean = date_str

        # Common date formats
        formats = [
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str_clean, fmt)
            except ValueError:
                continue

        logger.warning(f"Could not parse date: {date_str}")
        return None

    @staticmethod
    def extract_location(fields: dict[str, Any]) -> EventLocation | None:
        """Extract location information from event fields.

        Args:
            fields: Event fields dictionary (Opendatasoft v2.1 or legacy format)

        Returns:
            EventLocation object or None
        """
        location_data: dict[str, Any] = {}

        # Extract address components (Opendatasoft format)
        if address := (
            fields.get("location_address")
            or fields.get("address")
        ):
            location_data["address"] = address

        if city := (
            fields.get("location_city")
            or fields.get("city")
            or fields.get("ville")
        ):
            location_data["city"] = city

        if postal_code := (
            fields.get("location_postalcode")
            or fields.get("postal_code")
            or fields.get("code_postal")
        ):
            location_data["postal_code"] = postal_code

        # Extract coordinates (Opendatasoft format)
        if coords := fields.get("location_coordinates"):
            if isinstance(coords, dict) and "lat" in coords and "lon" in coords:
                location_data["coordinates"] = {
                    "lat": coords["lat"],
                    "lon": coords["lon"]
                }
        # Legacy format
        elif geo := fields.get("geo_point_2d") or fields.get("geometry"):
            if isinstance(geo, dict):
                if "lat" in geo and "lon" in geo:
                    location_data["coordinates"] = {"lat": geo["lat"], "lon": geo["lon"]}
                elif "coordinates" in geo:
                    coords = geo["coordinates"]
                    if isinstance(coords, list) and len(coords) >= 2:
                        location_data["coordinates"] = {"lon": coords[0], "lat": coords[1]}

        if not location_data:
            return None

        return EventLocation(**location_data)

    @staticmethod
    def extract_tags(fields: dict[str, Any]) -> list[str]:
        """Extract tags from event fields.

        Args:
            fields: Event fields dictionary (Opendatasoft v2.1 or legacy format)

        Returns:
            List of tags
        """
        tags: list[str] = []

        # Check various tag fields (Opendatasoft and legacy formats)
        for field in ["keywords_fr", "keywords", "tags", "mots_cles"]:
            if value := fields.get(field):
                if isinstance(value, list):
                    tags.extend(str(tag) for tag in value)
                elif isinstance(value, str):
                    tags.extend(tag.strip() for tag in value.split(","))

        return list(set(tags))  # Remove duplicates

    def process_record(self, record: dict[str, Any]) -> Event | None:
        """Process a single event record from OpenAgenda API.

        Args:
            record: Raw event record from API (Opendatasoft v2.1 or legacy format)

        Returns:
            Processed Event object or None if processing fails
        """
        try:
            # Check if this is Opendatasoft v2.1 format (fields at root)
            # or legacy format (fields nested under "fields" key)
            if "title_fr" in record or "uid" in record:
                # Opendatasoft v2.1 format
                fields = record
            else:
                # Legacy format
                fields = record.get("fields", {})

            # Generate unique event ID
            event_id = (
                record.get("uid")
                or record.get("slug")
                or record.get("recordid")
                or record.get("id")
            )
            if not event_id:
                logger.warning("Event missing ID, skipping")
                return None

            # Extract title
            title = (
                fields.get("title_fr")
                or fields.get("title")
                or fields.get("titre")
                or fields.get("nom")
                or "Untitled Event"
            )

            # Extract description
            description = (
                fields.get("description_fr")
                or fields.get("longdescription_fr")
                or fields.get("description")
                or fields.get("description_longue")
                or fields.get("free_text")
            )

            # Extract category (use keywords as proxy for Opendatasoft format)
            category = None
            if keywords_fr := fields.get("keywords_fr"):
                if isinstance(keywords_fr, list) and keywords_fr:
                    category = keywords_fr[0]
            if not category:
                category = (
                    fields.get("category")
                    or fields.get("categorie")
                    or fields.get("type")
                )

            # Extract dates (Opendatasoft format or legacy)
            start_date = self.parse_date(
                fields.get("firstdate_begin")
                or fields.get("start_date")
                or fields.get("date_debut")
                or fields.get("date_start")
            )

            end_date = self.parse_date(
                fields.get("lastdate_end")
                or fields.get("firstdate_end")
                or fields.get("end_date")
                or fields.get("date_fin")
                or fields.get("date_end")
            )

            # Extract location
            location = self.extract_location(fields)

            # Extract other fields
            organizer = (
                fields.get("organizer")
                or fields.get("organisateur")
                or fields.get("organization")
            )

            url = fields.get("url") or fields.get("link") or fields.get("lien")

            image_url = (
                fields.get("image")
                or fields.get("image_url")
                or fields.get("photo")
            )

            # Extract tags
            tags = self.extract_tags(fields)

            # Create Event object
            event = Event(
                event_id=str(event_id),
                title=title,
                description=description,
                category=category,
                location=location,
                start_date=start_date,
                end_date=end_date,
                organizer=organizer,
                url=url,
                image_url=image_url,
                tags=tags,
                raw_data=record,
            )

            return event

        except Exception as e:
            logger.error(f"Error processing event record: {e}")
            return None

    def process_records(self, records: list[dict[str, Any]]) -> list[Event]:
        """Process multiple event records.

        Args:
            records: List of raw event records from API

        Returns:
            List of processed Event objects
        """
        events: list[Event] = []

        for record in records:
            if event := self.process_record(record):
                events.append(event)

        logger.info(f"Processed {len(events)} events from {len(records)} records")
        return events

    def filter_ile_de_france_events(self, events: list[Event]) -> list[Event]:
        """Filter events to only include Île-de-France region events.

        Île-de-France includes: Paris, Hauts-de-Seine (92), Seine-Saint-Denis (93),
        Val-de-Marne (94), Seine-et-Marne (77), Yvelines (78), Essonne (91),
        Val-d'Oise (95), and major cities in these departments.

        Args:
            events: List of Event objects

        Returns:
            List of events in Île-de-France region
        """
        # Major cities and departments in Île-de-France
        idf_cities = {
            "paris", "versailles", "boulogne-billancourt", "saint-denis",
            "argenteuil", "montreuil", "créteil", "nanterre", "courbevoie",
            "vitry-sur-seine", "asnières-sur-seine", "colombes", "aulnay-sous-bois",
            "rueil-malmaison", "aubervilliers", "champigny-sur-marne", "saint-maur-des-fossés",
            "drancy", "issy-les-moulineaux", "levallois-perret", "antony", "noisy-le-grand",
            "neuilly-sur-seine", "clichy", "ivry-sur-seine", "villejuif", "épinay-sur-seine",
            "fontenay-sous-bois", "la courneuve", "bondy", "maisons-alfort", "suresnes",
            "pantin", "vincennes", "meaux", "évry", "corbeil-essonnes", "mantes-la-jolie",
            "melun", "savigny-sur-orge", "pontoise", "cergy"
        }

        # Postal code prefixes for Île-de-France departments
        idf_postal_prefixes = {"75", "77", "78", "91", "92", "93", "94", "95"}

        idf_events = []
        for event in events:
            if not event.location:
                continue

            # Check city name
            if event.location.city:
                city_lower = event.location.city.lower().strip()
                # Remove accents for comparison
                city_normalized = (
                    city_lower.replace("é", "e")
                    .replace("è", "e")
                    .replace("ê", "e")
                    .replace("à", "a")
                    .replace("ô", "o")
                )
                if any(idf_city in city_normalized for idf_city in idf_cities):
                    idf_events.append(event)
                    continue

            # Check postal code
            if event.location.postal_code:
                postal_prefix = event.location.postal_code[:2]
                if postal_prefix in idf_postal_prefixes:
                    idf_events.append(event)

        logger.info(
            f"Filtered to {len(idf_events)} Île-de-France events "
            f"from {len(events)} total"
        )
        return idf_events

    def filter_paris_events(self, events: list[Event]) -> list[Event]:
        """Filter events to only include Paris events.

        Deprecated: Use filter_ile_de_france_events() instead for broader coverage.

        Args:
            events: List of Event objects

        Returns:
            List of events in Paris
        """
        paris_events = [
            event
            for event in events
            if event.location
            and event.location.city
            and "paris" in event.location.city.lower()
        ]

        logger.info(f"Filtered to {len(paris_events)} Paris events from {len(events)} total")
        return paris_events

    def filter_by_date_range(
        self,
        events: list[Event],
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[Event]:
        """Filter events by date range.

        Args:
            events: List of Event objects
            start_date: Minimum start date (inclusive)
            end_date: Maximum end date (inclusive)

        Returns:
            List of events within date range
        """
        filtered_events = []

        for event in events:
            if not event.start_date:
                continue

            if start_date and event.start_date < start_date:
                continue

            if end_date and event.start_date > end_date:
                continue

            filtered_events.append(event)

        logger.info(
            f"Filtered to {len(filtered_events)} events from {len(events)} "
            f"(date range: {start_date} to {end_date})"
        )
        return filtered_events
