"""Retrieval orchestrator for multi-stage search with centralized filtering.

This module implements Phase 2 & 4 of the architectural refactoring:
- Phase 2: Separate concerns (orchestrator controls flow, vector_store is dumb)
- Phase 4: Move filtering OUT of vector_store (apply filters after retrieval)

Key improvements:
1. Vector store returns RAW similarity results (no filtering during search)
2. Filtering happens ONCE using SearchFilters.matches()
3. Geo-sorting happens ONCE in orchestrator
4. Clear separation: retrieval → filter → sort → return
"""

import logging
from typing import List, Tuple, Set, Dict, Any
from datetime import timedelta

from langchain_core.documents import Document
from src.models.vector_store import EventVectorStore
from src.data.models import Event
from src.retrieval.filters import SearchFilters
from src.utils.geo import haversine_distance

logger = logging.getLogger(__name__)


class RetrievalOrchestrator:
    """Orchestrates multi-stage retrieval with centralized filtering.

    Responsibilities:
    1. Control multi-stage search flow (exact → nearby → alt dates)
    2. Apply filters using SearchFilters.matches() AFTER retrieval
    3. Handle geo-sorting in one place
    4. Deduplicate results
    5. Add metadata (match_type, distance, etc.)

    The vector_store is now "dumb" - it just returns raw similarity scores.
    All filtering and sorting logic is centralized here.
    """

    def __init__(self, vector_store: EventVectorStore, k: int = 8):
        """Initialize orchestrator.

        Args:
            vector_store: EventVectorStore instance
            k: Number of results to return (default: 8)
        """
        self.vector_store = vector_store
        self.k = k

    def search(
        self,
        query: str,
        filters: SearchFilters,
        language: str = "fr"
    ) -> Dict[str, Any]:
        """Execute multi-stage retrieval with centralized filtering and language support.

        Flow:
        1. Stage 1: Get raw candidates from vector_store (no filtering)
        2. Stage 2: Apply filters using SearchFilters.matches()
        3. Stage 3: If insufficient results, try nearby locations
        4. Stage 4: Sort by geo-proximity if city filter exists
        5. Stage 5: Check for alternative dates (metadata only)
        6. Return top-k results

        Args:
            query: Search query string
            filters: SearchFilters instance
            language: Language code for BM25 tokenization ("fr" or "en")

        Returns:
            Dictionary with:
                - docs: List of Document objects
                - exact_count: Number of exact matches
                - total_count: Total number of results
        """
        logger.info(f"Orchestrator search: query='{query}', filters={filters}, language={language}")

        final_events: List[Tuple[Event, float, str, float]] = []  # (Event, Score, MatchType, Distance)
        seen_ids: Set[str] = set()

        # ========================================
        # STAGE 1: Get raw candidates (no filtering during search)
        # ========================================
        # Request more candidates than needed for filtering
        candidate_pool_size = self.k * 10  # Fetch 80 candidates for k=8
        raw_candidates = self.vector_store.search_raw(query, k=candidate_pool_size, language=language)
        logger.debug(f"Stage 1: Retrieved {len(raw_candidates)} raw candidates")

        # ========================================
        # STAGE 2: Apply filters AFTER retrieval
        # ========================================
        filtered_exact = []
        for event, score in raw_candidates:
            if filters.matches(event):
                filtered_exact.append((event, score))

        logger.info(f"Stage 2: {len(filtered_exact)} candidates match filters")

        # Add exact matches
        for event, score in filtered_exact:
            if event.event_id not in seen_ids:
                final_events.append((event, score, "Exact Match", 0.0))
                seen_ids.add(event.event_id)
                if len(final_events) >= self.k:
                    break

        exact_count = len(final_events)
        logger.info(f"Stage 2: {exact_count} exact matches added")

        # ========================================
        # STAGE 3: Nearby location fallback (if needed)
        # ========================================
        if len(final_events) < self.k and filters.has_city_filter():
            target_coords = self.vector_store.city_locator.get_coords(filters.city)
            if target_coords:
                # Get more raw candidates
                nearby_pool_size = self.k * 15  # Fetch even more for nearby
                raw_nearby = self.vector_store.search_raw(query, k=nearby_pool_size, language=language)

                # Apply filters WITHOUT city (keep dates strict)
                nearby_filters = filters.remove_city()
                filtered_nearby = [
                    (evt, score) for evt, score in raw_nearby
                    if nearby_filters.matches(evt) and evt.event_id not in seen_ids
                ]

                logger.info(f"Stage 3: {len(filtered_nearby)} nearby candidates match filters")

                # Calculate distances
                candidates_with_dist = []
                for evt, score in filtered_nearby:
                    dist = self._calculate_distance(evt, target_coords)
                    candidates_with_dist.append((evt, score, dist))

                # Sort by distance
                candidates_with_dist.sort(key=lambda x: x[2])

                # Add up to remaining needed
                needed = self.k * 3 - len(final_events)  # Fetch extra for LLM context
                for evt, score, dist in candidates_with_dist[:needed]:
                    final_events.append((evt, score, "Nearby Location", dist))
                    seen_ids.add(evt.event_id)

                logger.info(f"Stage 3: Added {len(final_events) - exact_count} nearby matches")

        # ========================================
        # STAGE 4: Geo-sorting (if city filter exists)
        # ========================================
        if filters.has_city_filter():
            target_coords = self.vector_store.city_locator.get_coords(filters.city)
            if target_coords:
                # Separate exact city matches from nearby
                exact_city = []
                nearby_city = []

                for evt, score, match_type, dist in final_events:
                    if match_type == "Exact Match":
                        # Exact matches stay first
                        exact_city.append((evt, score, match_type, dist))
                    else:
                        # Nearby matches get sorted by distance
                        nearby_city.append((evt, score, match_type, dist))

                # Combine: exact first, then nearby sorted by distance
                final_events = exact_city + nearby_city
                logger.debug(f"Stage 4: Geo-sorted results ({len(exact_city)} exact, {len(nearby_city)} nearby)")

        # ========================================
        # STAGE 5: Alternative dates check (metadata only)
        # ========================================
        alt_date_note = ""
        if filters.has_city_filter() and filters.has_date_filter():
            alt_count = self._count_alternative_dates(query, filters, seen_ids, language)
            if alt_count > 0:
                alt_date_note = f"SYSTEM_NOTE: Found {alt_count} events in {filters.city} on ALTERNATIVE DATES (within +/- 7 days). Mention this verbally."
                logger.info(f"Stage 5: {alt_count} events on alternative dates")

        # ========================================
        # STAGE 6: Convert to Documents
        # ========================================
        docs = []
        for evt, score, match_type, dist in final_events:
            meta = evt.get_metadata()
            meta.update({
                "score": score,
                "match_type": match_type,
                "distance_km": dist
            })
            if alt_date_note:
                meta["nearby_date_note"] = alt_date_note
                alt_date_note = ""  # Only add to first doc

            docs.append(Document(page_content=evt.to_text(), metadata=meta))

        logger.info(f"Orchestrator returning {len(docs)} documents ({exact_count} exact matches)")

        return {
            "docs": docs,
            "exact_count": exact_count,
            "total_count": len(docs)
        }

    def _calculate_distance(self, event: Event, target_coords: Tuple[float, float]) -> float:
        """Calculate distance from event to target coordinates.

        Args:
            event: Event to calculate distance for
            target_coords: (lat, lon) tuple

        Returns:
            Distance in km, or infinity if coordinates unavailable
        """
        # Try event coordinates first
        if event.location and event.location.coordinates:
            lat = event.location.coordinates.get("lat")
            lon = event.location.coordinates.get("lon")
            if lat is not None and lon is not None:
                return haversine_distance(target_coords[0], target_coords[1], lat, lon)

        # Fallback to city coordinates
        if event.location and event.location.city:
            city_coords = self.vector_store.city_locator.get_coords(event.location.city)
            if city_coords:
                return haversine_distance(target_coords[0], target_coords[1], city_coords[0], city_coords[1])

        return float('inf')

    def _count_alternative_dates(
        self,
        query: str,
        filters: SearchFilters,
        exclude_ids: Set[str],
        language: str = "fr"
    ) -> int:
        """Count events on alternative dates (±7 day window).

        Args:
            query: Search query
            filters: Current filters
            exclude_ids: Event IDs to exclude (already shown)
            language: Language code for BM25 tokenization

        Returns:
            Count of events on alternative dates
        """
        # Expand date window
        alt_filters = filters.expand_date_window(days=7)

        # Get raw candidates (with language for BM25)
        raw_candidates = self.vector_store.search_raw(query, k=50, language=language)

        # Apply expanded filters
        count = 0
        for evt, score in raw_candidates:
            if evt.event_id in exclude_ids:
                continue
            if alt_filters.matches(evt):
                count += 1

        return count
