"""
FILE: manager.py
STATUS: Active
RESPONSIBILITY: Manages multi-stage event retrieval using vector store and search intents.

DEPENDENCIES (Who uses this file):
- src/retrieval/chain.py: Uses RetrievalManager for search orchestration

IMPORTS (What this file needs):
- logging: For debug output
- datetime: For date handling
- typing: For type annotations
- dataclasses: For SearchIntent structure
- langchain_core: For Document type

LAST MAJOR UPDATE: 2026-02-02
MAINTAINER: Core Backend Team
"""

import logging
from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Tuple, Set, Union
from dataclasses import dataclass

from langchain_core.documents import Document
from src.utils.geo import haversine_distance
from src.models.vector_store import EventVectorStore
from src.data.models import Event

logger = logging.getLogger(__name__)


@dataclass
class SearchIntent:
    """Normalized search requirements extracted from user query."""

    city: Optional[str] = None
    target_date: Optional[date] = None
    days: List[int] = None
    month: Optional[Union[int, List[int]]] = None  # Support single month or list of months
    year: Optional[int] = 2026
    date_min: Optional[date] = None
    date_max: Optional[date] = None
    category: Optional[str] = None
    is_free: Optional[bool] = None
    audience: Optional[str] = None  # kids, family, professional

    @property
    def has_date_filter(self) -> bool:
        return any([self.days, self.month, self.date_min, self.date_max])


@dataclass
class FilterRelaxation:
    """Tracks what filters were relaxed to find results."""

    is_free_relaxed: bool = False  # "free" filter was removed
    category_relaxed: bool = False  # Category was broadened
    date_relaxed: bool = False  # Date window was expanded
    city_relaxed: bool = False  # City filter was removed (nearby)
    original_is_free: Optional[bool] = None
    original_category: Optional[str] = None
    original_date_desc: Optional[str] = None  # "February 15, 2026" or "this weekend"
    original_city: Optional[str] = None

    def get_transparency_message(self, language: str = "en") -> str:
        """Generate user-facing transparency message about relaxations.

        Uses i18n for proper translations.
        Returns empty string if no relaxations occurred.
        """
        if not any([self.is_free_relaxed, self.category_relaxed, self.date_relaxed, self.city_relaxed]):
            return ""

        try:
            from src.utils.i18n import get_translator

            t = get_translator(language)

            parts = []

            if self.is_free_relaxed:
                parts.append(t.get("transparency.is_free_relaxed"))
            if self.date_relaxed:
                parts.append(t.get("transparency.date_relaxed"))
            if self.city_relaxed:
                parts.append(t.get("transparency.city_relaxed"))
            if self.category_relaxed:
                # Not implemented yet but ready for future
                pass

            if not parts:
                return ""

            prefix = t.get("transparency.prefix")
            details = "; ".join(parts)
            relaxation_msg = f"{prefix} {t.get('transparency.combined_relaxation', details=details)}"

            # Add refinement hint so user knows they can be more specific
            refinement_hint = t.get("transparency.refinement_hint")
            return f"{relaxation_msg}\n\n💡 *{refinement_hint}*"

        except Exception as e:
            # Fallback to simple English message
            logger.warning(f"i18n failed for transparency message: {e}")
            parts = []
            if self.is_free_relaxed:
                parts.append("no free events found, showing paid alternatives")
            if self.date_relaxed:
                parts.append("showing events in the upcoming 7 days")
            if self.city_relaxed and self.original_city:
                parts.append(f"showing events from cities near {self.original_city}")

            if not parts:
                return ""

            msg = "📢 **Note:** " + "; ".join(parts) + "."
            msg += "\n\n💡 *Not what you're looking for? Try refining your search.*"
            return msg


class RetrievalManager:
    """Manages multi-stage retrieval: Exact -> Nearby Location -> Alt Date Check."""

    def __init__(self, vector_store: EventVectorStore, k: int = 8):
        self.vector_store = vector_store
        self.k = k

    def parse_intent(self, filters: Dict[str, Any]) -> SearchIntent:
        """Transform raw filters into a structured SearchIntent."""
        # Handle case where filters is a list instead of dict (LLM parsing error)
        if isinstance(filters, list):
            logger.warning(f"Received list instead of dict for filters: {filters}")
            # Take first item if list
            filters = filters[0] if filters else {}
        if not isinstance(filters, dict):
            logger.warning(f"Received non-dict filters: {type(filters)}")
            filters = {}
        # Handle case where dict has nested "filters" key (LLM format variation)
        if "filters" in filters and isinstance(filters["filters"], dict):
            filters = filters["filters"]

        intent = SearchIntent(
            city=filters.get("city"),
            month=filters.get("month"),
            year=filters.get("year", 2026),
            category=filters.get("category"),
            is_free=filters.get("is_free"),
            audience=filters.get("audience"),
        )

        # Handle Days (single or list)
        days = filters.get("day")
        if isinstance(days, list):
            intent.days = days
        elif isinstance(days, int):
            intent.days = [days]

        # Handle Date Range
        if "date_min" in filters:
            val = filters["date_min"]
            intent.date_min = val if isinstance(val, date) else date.fromisoformat(val)
        if "date_max" in filters:
            val = filters["date_max"]
            intent.date_max = val if isinstance(val, date) else date.fromisoformat(val)

        # Set a primary target date for distance calculations/windows
        if intent.month and intent.days:
            try:
                # Handle multi-month: use first month for target_date
                first_month = intent.month[0] if isinstance(intent.month, list) else intent.month
                intent.target_date = date(intent.year, first_month, intent.days[0])
            except (ValueError, IndexError, TypeError):
                pass
        elif intent.date_min:
            intent.target_date = intent.date_min

        return intent

    def execute_search(self, refined_query: str, intent: SearchIntent, language: str = "fr") -> Dict[str, Any]:
        """Execute the deterministic multi-stage retrieval process with progressive relaxation.

        Relaxation order (if no results):
        1. Exact match (all filters)
        2. Relax is_free (if True → None)
        3. Relax date (expand to ±7 days)
        4. Relax city (nearby locations)

        Args:
            refined_query: The refined search query
            intent: The search intent with filters
            language: Language for transparency messages ("fr" or "en")
        """
        logger.info(f"Executing search with intent: {intent}")

        # Track relaxations for transparency
        relaxation = FilterRelaxation(
            original_is_free=intent.is_free,
            original_category=intent.category,
            original_city=intent.city,
            original_date_desc=self._format_date_desc(intent),
        )

        final_events: List[Tuple[Event, float, str, float]] = []  # (Event, Score, MatchType, Distance)
        seen_ids: Set[str] = set()

        # Phase 1: Exact Match
        exact_results = self._search_exact(refined_query, intent)
        for evt, score in exact_results:
            if evt.event_id not in seen_ids:
                final_events.append((evt, score, "Exact Match", 0.0))
                seen_ids.add(evt.event_id)

        exact_count = len(final_events)
        logger.info(f"Phase 1: Found {exact_count} exact matches.")

        # Phase 2: Relax is_free filter (if no results and is_free=True)
        if len(final_events) == 0 and intent.is_free is True:
            logger.info("Phase 2: No free events found, relaxing is_free filter...")
            relaxed_intent = SearchIntent(
                city=intent.city,
                target_date=intent.target_date,
                days=intent.days,
                month=intent.month,
                year=intent.year,
                date_min=intent.date_min,
                date_max=intent.date_max,
                category=intent.category,
                is_free=None,  # Relaxed
                audience=intent.audience,
            )
            paid_results = self._search_exact(refined_query, relaxed_intent)
            for evt, score in paid_results:
                if evt.event_id not in seen_ids:
                    final_events.append((evt, score, "Paid Alternative", 0.0))
                    seen_ids.add(evt.event_id)

            if len(final_events) > 0:
                relaxation.is_free_relaxed = True
                logger.info(f"Phase 2: Found {len(final_events)} paid alternatives.")

        # Phase 3: Relax date filter (expand to upcoming 7 days - future only)
        if len(final_events) == 0 and intent.has_date_filter and intent.target_date:
            logger.info("Phase 3: No events on exact date, expanding to upcoming 7 days...")
            # Get future-only date range (never show past events)
            relaxed_date_min, relaxed_date_max = self._get_future_date_range(intent.target_date, days_ahead=7)
            relaxed_intent = SearchIntent(
                city=intent.city,
                target_date=intent.target_date,
                days=None,  # Remove specific days
                month=None,  # Remove month filter
                year=intent.year,
                date_min=relaxed_date_min,
                date_max=relaxed_date_max,
                category=intent.category,
                is_free=None if relaxation.is_free_relaxed else intent.is_free,
                audience=intent.audience,
            )
            expanded_results = self._search_exact(refined_query, relaxed_intent)
            for evt, score in expanded_results:
                if evt.event_id not in seen_ids:
                    final_events.append((evt, score, "Upcoming Date", 0.0))
                    seen_ids.add(evt.event_id)

            if len(final_events) > 0:
                relaxation.date_relaxed = True
                logger.info(f"Phase 3: Found {len(final_events)} events within upcoming 7 days.")

        # Phase 4: Nearby Locations (if still need more results)
        nearby_count = 0
        if len(final_events) < self.k and intent.city:
            target_coords = self.vector_store.city_locator.get_coords(intent.city)
            if target_coords:
                needed = self.k * 3
                # Use potentially relaxed filters for nearby search
                # Calculate future-only date range if date was relaxed
                nearby_date_min = intent.date_min
                nearby_date_max = intent.date_max
                if relaxation.date_relaxed and intent.target_date:
                    nearby_date_min, nearby_date_max = self._get_future_date_range(intent.target_date, days_ahead=7)

                relaxed_intent = SearchIntent(
                    city=None,  # Remove city for nearby
                    target_date=intent.target_date,
                    days=None if relaxation.date_relaxed else intent.days,
                    month=None if relaxation.date_relaxed else intent.month,
                    year=intent.year,
                    date_min=nearby_date_min,
                    date_max=nearby_date_max,
                    category=intent.category,
                    is_free=None if relaxation.is_free_relaxed else intent.is_free,
                    audience=intent.audience,
                )
                nearby_results = self._search_nearby_locations(refined_query, relaxed_intent, needed)

                # Calculate distances and sort
                candidates = []
                for evt, score in nearby_results:
                    if evt.event_id in seen_ids:
                        continue

                    dist = float("inf")
                    lat, lon = None, None
                    if evt.location and evt.location.coordinates:
                        lat = evt.location.coordinates.get("lat")
                        lon = evt.location.coordinates.get("lon")

                    if (lat is None or lon is None) and evt.location and evt.location.city:
                        city_coords = self.vector_store.city_locator.get_coords(evt.location.city)
                        if city_coords:
                            lat, lon = city_coords

                    if lat is not None and lon is not None:
                        dist = haversine_distance(target_coords[0], target_coords[1], lat, lon)

                    candidates.append((evt, score, dist))

                candidates.sort(key=lambda x: x[2])

                for evt, score, dist in candidates:
                    if len(final_events) >= self.k * 3:
                        break
                    match_type = "Nearby Location"
                    if relaxation.date_relaxed:
                        match_type = "Nearby Location (upcoming)"
                    final_events.append((evt, score, match_type, dist))
                    seen_ids.add(evt.event_id)
                    nearby_count += 1

                if nearby_count > 0:
                    relaxation.city_relaxed = True
                    logger.info(f"Phase 4: Added {nearby_count} nearby location matches.")

        # Phase 5: Alternative Dates Check (for informational note only)
        alt_date_note = ""
        if not relaxation.date_relaxed and intent.city and intent.has_date_filter:
            alt_count = self._count_alt_dates(refined_query, intent, seen_ids)
            if alt_count > 0:
                alt_date_note = f"SYSTEM_NOTE: Found {alt_count} events in {intent.city} on ALTERNATIVE DATES (within +/- 7 days). Mention this verbally."

        # Convert to Documents (enforce k limit)
        docs = []
        transparency_msg = relaxation.get_transparency_message(language)

        for evt, score, m_type, dist in final_events[: self.k]:
            meta = evt.get_metadata()
            meta.update({"score": score, "match_type": m_type, "distance_km": dist})
            if alt_date_note:
                meta["nearby_date_note"] = alt_date_note
                alt_date_note = ""
            if transparency_msg and len(docs) == 0:
                meta["transparency_note"] = transparency_msg

            docs.append(Document(page_content=evt.to_text(), metadata=meta))

        logger.info(f"Phase 5: Returning {len(docs)} events (limit k={self.k})")

        # Count total matching events in database
        total_in_db = self._count_total_matches(refined_query, intent)

        return {
            "docs": docs,
            "exact_count": exact_count,
            "total_count": len(docs),
            "total_in_database": total_in_db,
            "filters_applied": {
                "city": intent.city,
                "month": intent.month,
                "category": intent.category,
                "has_date": intent.has_date_filter,
            },
            "relaxation": {
                "is_free_relaxed": relaxation.is_free_relaxed,
                "date_relaxed": relaxation.date_relaxed,
                "city_relaxed": relaxation.city_relaxed,
                "transparency_message": transparency_msg,
            },
        }

    def _format_date_desc(self, intent: SearchIntent) -> Optional[str]:
        """Format a human-readable date description."""
        if intent.target_date:
            return intent.target_date.strftime("%B %d, %Y")
        elif intent.month:
            months = intent.month if isinstance(intent.month, list) else [intent.month]
            month_names = [
                "",
                "January",
                "February",
                "March",
                "April",
                "May",
                "June",
                "July",
                "August",
                "September",
                "October",
                "November",
                "December",
            ]
            return ", ".join(month_names[m] for m in months if 1 <= m <= 12)
        return None

    def _get_future_date_range(self, target_date: date, days_ahead: int = 7) -> Tuple[date, date]:
        """Get a date range that only includes future dates.

        Never returns dates before today - events that have already occurred
        are not useful to users.

        Args:
            target_date: The original target date from user's query
            days_ahead: Number of days to extend into the future

        Returns:
            Tuple of (date_min, date_max) where date_min >= today
        """
        today = date.today()
        # date_min is the later of: today OR target_date (no past events)
        date_min = max(today, target_date)
        # date_max extends into the future
        date_max = target_date + timedelta(days=days_ahead)
        # Ensure date_max is also in the future
        if date_max < today:
            date_max = today + timedelta(days=days_ahead)

        logger.debug(f"[DATE-RANGE] target={target_date}, range={date_min} to {date_max}")
        return date_min, date_max

    def _search_exact(self, query: str, intent: SearchIntent) -> List[Tuple[Event, float]]:
        filters = {
            "city": intent.city,
            "month": intent.month,
            "day": intent.days,
            "year": intent.year,
            "date_min": intent.date_min,
            "date_max": intent.date_max,
            "category": intent.category,
            "is_free": intent.is_free,
            "audience": intent.audience,
        }
        clean = {k: v for k, v in filters.items() if v is not None}
        return self.vector_store.search(query, k=self.k * 3, metadata_filter=clean, candidate_pool=1000)

    def _search_nearby_locations(self, query: str, intent: SearchIntent, k: int) -> List[Tuple[Event, float]]:
        # Remove city but keep date and audience strict
        filters = {
            "month": intent.month,
            "day": intent.days,
            "year": intent.year,
            "date_min": intent.date_min,
            "date_max": intent.date_max,
            "category": intent.category,
            "is_free": intent.is_free,
            "audience": intent.audience,
        }
        clean = {k: v for k, v in filters.items() if v is not None}
        return self.vector_store.search(query, k=k, metadata_filter=clean, candidate_pool=1500)

    def _count_total_matches(self, query: str, intent: SearchIntent) -> int:
        """Count total events matching the filters (for transparency reporting)."""
        filters = {
            "city": intent.city,
            "month": intent.month,
            "day": intent.days,
            "year": intent.year,
            "date_min": intent.date_min,
            "date_max": intent.date_max,
            "category": intent.category,
            "is_free": intent.is_free,
            "audience": intent.audience,
        }
        clean = {k: v for k, v in filters.items() if v is not None}

        # Get a larger sample to estimate total
        results = self.vector_store.search(query, k=500, metadata_filter=clean, candidate_pool=2000)
        return len(results)

    def _count_alt_dates(self, query: str, intent: SearchIntent, exclude_ids: Set[str]) -> int:
        # Keep city and audience, remove date, add future-only window
        filters = {
            "city": intent.city,
            "category": intent.category,
            "is_free": intent.is_free,
            "audience": intent.audience,
        }
        if intent.target_date:
            # Use future-only date range (no past events)
            alt_date_min, alt_date_max = self._get_future_date_range(intent.target_date, days_ahead=7)
            filters["date_min"] = alt_date_min
            filters["date_max"] = alt_date_max

        clean = {k: v for k, v in filters.items() if v is not None}
        results = self.vector_store.search(query, k=20, metadata_filter=clean, candidate_pool=500)

        count = 0
        for evt, _ in results:
            if evt.event_id not in exclude_ids:
                count += 1
        return count
