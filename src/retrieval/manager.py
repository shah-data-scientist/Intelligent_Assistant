"""Deterministic multi-stage retrieval manager for cultural events."""

import logging
from datetime import date, timedelta, datetime
from typing import Any, Dict, List, Optional, Tuple, Set
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
    month: Optional[int] = None
    year: Optional[int] = 2026
    date_min: Optional[date] = None
    date_max: Optional[date] = None
    category: Optional[str] = None
    is_free: Optional[bool] = None
    audience: Optional[str] = None  # kids, family, professional

    @property
    def has_date_filter(self) -> bool:
        return any([self.days, self.month, self.date_min, self.date_max])

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
            audience=filters.get("audience")
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
                intent.target_date = date(intent.year, intent.month, intent.days[0])
            except:
                pass
        elif intent.date_min:
            intent.target_date = intent.date_min
            
        return intent

    def execute_search(self, refined_query: str, intent: SearchIntent) -> Dict[str, Any]:
        """Execute the deterministic multi-stage retrieval process."""
        logger.info(f"Executing search with intent: {intent}")

        final_events: List[Tuple[Event, float, str, float]] = [] # (Event, Score, MatchType, Distance)
        seen_ids: Set[str] = set()

        # 1. Exact Match
        exact_results = self._search_exact(refined_query, intent)
        for evt, score in exact_results:
            if evt.event_id not in seen_ids:
                final_events.append((evt, score, "Exact Match", 0.0))
                seen_ids.add(evt.event_id)

        exact_count = len(final_events)
        logger.info(f"Phase 1: Found {exact_count} exact matches.")

        # 2. Nearby Locations (Fallback) - KEEP DATE STRICT
        if len(final_events) < self.k and intent.city:
            target_coords = self.vector_store.city_locator.get_coords(intent.city)
            if target_coords:
                needed = self.k * 3 # Fetch more for diversity
                nearby_results = self._search_nearby_locations(refined_query, intent, needed)
                
                # Calculate distances and sort
                candidates = []
                for evt, score in nearby_results:
                    if evt.event_id in seen_ids:
                        continue
                    
                    dist = float('inf')
                    # Try event coords, fallback to city coords
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
                
                # Sort by distance
                candidates.sort(key=lambda x: x[2])
                
                for evt, score, dist in candidates:
                    if len(final_events) >= self.k * 3: break # Limit to 24 for LLM
                    final_events.append((evt, score, "Nearby Location", dist))
                    seen_ids.add(evt.event_id)
                
                logger.info(f"Phase 2: Added {len(final_events) - exact_count} nearby location matches.")

        # 3. Alternative Dates Check (Metadata only) - SAME CITY
        alt_date_note = ""
        if intent.city and intent.has_date_filter:
            alt_count = self._count_alt_dates(refined_query, intent, seen_ids)
            if alt_count > 0:
                alt_date_note = f"SYSTEM_NOTE: Found {alt_count} events in {intent.city} on ALTERNATIVE DATES (within +/- 7 days). Mention this verbally."

        # Convert to Documents (enforce k limit here - single source of truth)
        docs = []
        for evt, score, m_type, dist in final_events[:self.k]:
            meta = evt.get_metadata()
            meta.update({
                "score": score,
                "match_type": m_type,
                "distance_km": dist
            })
            if alt_date_note:
                meta["nearby_date_note"] = alt_date_note
                alt_date_note = "" # Only add to first doc

            docs.append(Document(page_content=evt.to_text(), metadata=meta))

        logger.info(f"Phase 4: Returning {len(docs)} events (limit k={self.k})")

        # 5. Count total matching events in database (for transparency)
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
                "has_date": intent.has_date_filter
            }
        }

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
            "audience": intent.audience
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
            "audience": intent.audience
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
            "audience": intent.audience
        }
        clean = {k: v for k, v in filters.items() if v is not None}

        # Get a larger sample to estimate total
        results = self.vector_store.search(query, k=500, metadata_filter=clean, candidate_pool=2000)
        return len(results)

    def _count_alt_dates(self, query: str, intent: SearchIntent, exclude_ids: Set[str]) -> int:
        # Keep city and audience, remove date, add window
        filters = {
            "city": intent.city,
            "category": intent.category,
            "is_free": intent.is_free,
            "audience": intent.audience
        }
        if intent.target_date:
            filters["date_min"] = intent.target_date - timedelta(days=7)
            filters["date_max"] = intent.target_date + timedelta(days=7)

        clean = {k: v for k, v in filters.items() if v is not None}
        results = self.vector_store.search(query, k=20, metadata_filter=clean, candidate_pool=500)

        count = 0
        for evt, _ in results:
            if evt.event_id not in exclude_ids:
                count += 1
        return count
