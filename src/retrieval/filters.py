"""Centralized filter definitions and validation - Single Source of Truth.

This module defines SearchFilters as the ONLY place where:
1. Filter extraction from LLM output happens
2. Filter validation occurs
3. Event matching logic is implemented
4. Date/time normalization is handled

This eliminates the distributed validation anti-pattern that caused whac-a-mole regressions.
"""

import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Optional, Dict, Any, List
from enum import Enum

from src.data.models import Event

logger = logging.getLogger(__name__)


class DateRangeType(Enum):
    """Type of date range filter."""
    EXACT_DATE = "exact_date"  # Single date
    DATE_RANGE = "date_range"  # Min/max range
    WEEKEND = "weekend"  # Special case
    NONE = "none"  # No date filter


@dataclass
class SearchFilters:
    """Validated search filters - single source of truth for all filtering logic.

    This class centralizes ALL filter-related logic that was previously duplicated across:
    - METADATA_EXTRACTION_PROMPT (prompts.py)
    - RetrievalManager.parse_intent() (manager.py)
    - EventVectorStore._matches_filter() (vector_store.py)
    - RAG_SYSTEM_PROMPT grounding rules (prompts.py)

    Now there's ONE place to update when filter logic needs to change.
    """

    # Core filters
    city: Optional[str] = None
    date_min: Optional[date] = None
    date_max: Optional[date] = None
    category: Optional[str] = None
    is_free: Optional[bool] = None
    age: Optional[int] = None

    # Metadata for debugging
    date_range_type: DateRangeType = DateRangeType.NONE
    original_query: str = ""

    def __post_init__(self):
        """Validate and normalize filters after initialization."""
        # Normalize city name
        if self.city:
            self.city = self._normalize_city(self.city)

        # Normalize category
        if self.category:
            self.category = self._normalize_category(self.category)

        # Ensure date_min <= date_max
        if self.date_min and self.date_max and self.date_min > self.date_max:
            logger.warning(f"date_min ({self.date_min}) > date_max ({self.date_max}), swapping")
            self.date_min, self.date_max = self.date_max, self.date_min

    @staticmethod
    def _normalize_city(city: str) -> str:
        """Normalize city name to standard format.

        Examples:
            "paris" → "Paris"
            "PARIS" → "Paris"
            "Paris, France" → "Paris"
            "ile de france" → "Île-de-France" (regional term)
        """
        city = city.strip()

        # Remove country suffix
        if "," in city:
            city = city.split(",")[0].strip()

        # Handle regional terms
        city_lower = city.lower()
        if city_lower in ["ile de france", "ile-de-france", "île-de-france", "idf", "paris region"]:
            return "Île-de-France"

        # Title case for city names
        return city.title()

    @staticmethod
    def _normalize_category(category: str) -> str:
        """Normalize category to standard format.

        Examples:
            "JAZZ" → "jazz"
            "Classical Music" → "classical"
            "théâtre" → "théâtre"
        """
        category = category.strip().lower()

        # Map common variations to canonical forms
        category_map = {
            "classical music": "classical",
            "classique": "classical",
            "musique classique": "classical",
            "theater": "théâtre",
            "theatre": "théâtre",
            "dance": "danse",
            "world music": "musique du monde",
            "electronic": "électronique",
            "hip hop": "hip-hop",
        }

        return category_map.get(category, category)

    @classmethod
    def from_llm_output(cls, raw: Dict[str, Any], reference_date: Optional[date] = None) -> "SearchFilters":
        """Parse and validate LLM extraction output into SearchFilters.

        This is the SINGLE PLACE where LLM output → SearchFilters conversion happens.
        Previously this logic was split between:
        - METADATA_EXTRACTION_PROMPT (natural language rules)
        - RetrievalManager.parse_intent() (Python normalization)

        Args:
            raw: LLM output dictionary with keys: city, month, day, year, category, is_free, age
            reference_date: Current date for relative date calculations (default: today)

        Returns:
            Validated SearchFilters instance
        """
        reference_date = reference_date or date.today()

        filters = cls()
        filters.city = raw.get("city")
        filters.category = raw.get("category")
        filters.is_free = raw.get("is_free")
        filters.age = raw.get("age")

        # Date extraction - SINGLE SOURCE OF TRUTH
        year = raw.get("year")
        month = raw.get("month")
        day = raw.get("day")

        # Handle explicit date_min/date_max if provided
        if "date_min" in raw:
            filters.date_min = cls._parse_date_value(raw["date_min"])
        if "date_max" in raw:
            filters.date_max = cls._parse_date_value(raw["date_max"])

        # Convert month/day/year to date_min/date_max
        if month is not None and day is not None:
            # Handle day as list (e.g., weekend [24, 25])
            if isinstance(day, list):
                if not day:
                    pass  # Empty list, ignore
                elif len(day) == 1:
                    # Single day
                    try:
                        filters.date_min = date(year or reference_date.year, month, day[0])
                        filters.date_max = filters.date_min
                        filters.date_range_type = DateRangeType.EXACT_DATE
                    except ValueError as e:
                        logger.warning(f"Invalid date: year={year}, month={month}, day={day[0]}: {e}")
                else:
                    # Multiple days (e.g., weekend)
                    try:
                        filters.date_min = date(year or reference_date.year, month, min(day))
                        filters.date_max = date(year or reference_date.year, month, max(day))
                        filters.date_range_type = DateRangeType.WEEKEND
                    except ValueError as e:
                        logger.warning(f"Invalid date range: year={year}, month={month}, days={day}: {e}")
            else:
                # Single day as integer
                try:
                    filters.date_min = date(year or reference_date.year, month, day)
                    filters.date_max = filters.date_min
                    filters.date_range_type = DateRangeType.EXACT_DATE
                except ValueError as e:
                    logger.warning(f"Invalid date: year={year}, month={month}, day={day}: {e}")

        elif month is not None:
            # Month only - first to last day of month
            try:
                year_val = year or reference_date.year
                filters.date_min = date(year_val, month, 1)
                # Last day of month
                if month == 12:
                    filters.date_max = date(year_val, 12, 31)
                else:
                    filters.date_max = date(year_val, month + 1, 1) - timedelta(days=1)
                filters.date_range_type = DateRangeType.DATE_RANGE
            except ValueError as e:
                logger.warning(f"Invalid month: year={year}, month={month}: {e}")

        # Determine date_range_type if not set
        if filters.date_min or filters.date_max:
            if filters.date_range_type == DateRangeType.NONE:
                if filters.date_min == filters.date_max:
                    filters.date_range_type = DateRangeType.EXACT_DATE
                else:
                    filters.date_range_type = DateRangeType.DATE_RANGE

        # Manually apply normalization (since __post_init__ already ran)
        if filters.city:
            filters.city = cls._normalize_city(filters.city)
        if filters.category:
            filters.category = cls._normalize_category(filters.category)

        logger.info(f"Parsed filters: {filters}")
        return filters

    @staticmethod
    def _parse_date_value(value: Any) -> Optional[date]:
        """Parse date from various formats."""
        if value is None:
            return None
        if isinstance(value, date):
            return value
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, str):
            try:
                return date.fromisoformat(value)
            except ValueError:
                logger.warning(f"Could not parse date string: {value}")
                return None
        return None

    def matches(self, event: Event) -> bool:
        """Check if event matches these filters.

        This is the SINGLE PLACE where event matching logic is implemented.
        Previously duplicated in EventVectorStore._matches_filter() (lines 313-414).

        Args:
            event: Event to check

        Returns:
            True if event matches all filters, False otherwise
        """
        # City filter
        if self.city:
            if not self._matches_city(event, self.city):
                return False

        # Date filters
        if self.date_min or self.date_max:
            if not self._matches_date_range(event, self.date_min, self.date_max):
                return False

        # Category filter
        if self.category:
            if not self._matches_category(event, self.category):
                return False

        # is_free filter
        if self.is_free is True:
            if not self._matches_is_free(event):
                return False

        # Age filter
        if self.age is not None:
            if not self._matches_age(event, self.age):
                return False

        return True

    @staticmethod
    def _matches_city(event: Event, target_city: str) -> bool:
        """Check if event matches city filter.

        Handles:
        - Regional terms (Île-de-France matches any city)
        - Exact city name matching (case-insensitive)
        """
        if not event.location or not event.location.city:
            return False

        # Regional term matches any city
        if target_city == "Île-de-France":
            return True

        # Case-insensitive substring match
        return target_city.lower() in event.location.city.lower()

    @staticmethod
    def _matches_date_range(event: Event, date_min: Optional[date], date_max: Optional[date]) -> bool:
        """Check if event falls within date range."""
        if not event.start_date:
            return False

        event_date = event.start_date.date() if isinstance(event.start_date, datetime) else event.start_date

        if date_min and event_date < date_min:
            return False
        if date_max and event_date > date_max:
            return False

        return True

    @staticmethod
    def _matches_category(event: Event, target_category: str) -> bool:
        """Check if event matches category filter.

        Uses bidirectional substring matching:
        - "jazz" matches "Jazz Concert"
        - "classical" matches event.category = "Musique Classique"
        """
        if not event.category:
            return False

        event_cat = event.category.lower()
        target_cat = target_category.lower()

        # Bidirectional substring match
        return target_cat in event_cat or event_cat in target_cat

    @staticmethod
    def _matches_is_free(event: Event) -> bool:
        """Check if event is free."""
        if not event.conditions:
            return False
        return "gratuit" in event.conditions.lower() or "free" in event.conditions.lower()

    @staticmethod
    def _matches_age(event: Event, target_age: int) -> bool:
        """Check if event is suitable for target age."""
        if event.age_min is not None and event.age_min > target_age:
            return False
        if event.age_max is not None and event.age_max < target_age:
            return False
        return True

    def to_dict(self) -> Dict[str, Any]:
        """Convert filters to dictionary for logging/debugging."""
        return {
            "city": self.city,
            "date_min": self.date_min.isoformat() if self.date_min else None,
            "date_max": self.date_max.isoformat() if self.date_max else None,
            "category": self.category,
            "is_free": self.is_free,
            "age": self.age,
            "date_range_type": self.date_range_type.value,
        }

    def remove_city(self) -> "SearchFilters":
        """Create a copy of filters with city removed (for nearby location fallback)."""
        return SearchFilters(
            city=None,  # Remove city
            date_min=self.date_min,
            date_max=self.date_max,
            category=self.category,
            is_free=self.is_free,
            age=self.age,
            date_range_type=self.date_range_type,
            original_query=self.original_query,
        )

    def expand_date_window(self, days: int = 7) -> "SearchFilters":
        """Create a copy with expanded date window (for alternative date suggestions).

        Args:
            days: Number of days to expand in each direction

        Returns:
            New SearchFilters with wider date range
        """
        if not self.date_min and not self.date_max:
            return self

        new_min = None
        new_max = None

        if self.date_min:
            new_min = self.date_min - timedelta(days=days)
        if self.date_max:
            new_max = self.date_max + timedelta(days=days)

        return SearchFilters(
            city=self.city,
            date_min=new_min,
            date_max=new_max,
            category=self.category,
            is_free=self.is_free,
            age=self.age,
            date_range_type=DateRangeType.DATE_RANGE,
            original_query=self.original_query,
        )

    def has_date_filter(self) -> bool:
        """Check if any date filtering is active."""
        return self.date_min is not None or self.date_max is not None

    def has_city_filter(self) -> bool:
        """Check if city filtering is active."""
        return self.city is not None and self.city != "Île-de-France"

    def __repr__(self) -> str:
        """Human-readable representation."""
        parts = []
        if self.city:
            parts.append(f"city={self.city}")
        if self.date_min or self.date_max:
            if self.date_min == self.date_max:
                parts.append(f"date={self.date_min}")
            else:
                parts.append(f"dates={self.date_min} to {self.date_max}")
        if self.category:
            parts.append(f"category={self.category}")
        if self.is_free:
            parts.append("free=True")
        if self.age:
            parts.append(f"age={self.age}")

        return f"SearchFilters({', '.join(parts) if parts else 'no filters'})"
