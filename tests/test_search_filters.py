"""Tests for centralized SearchFilters class."""

import pytest
from datetime import date, datetime
from src.retrieval.filters import SearchFilters, DateRangeType
from src.data.models import Event, EventLocation


class TestSearchFiltersFromLLMOutput:
    """Test SearchFilters.from_llm_output() method."""

    def test_exact_date_extraction(self):
        """Test extraction of exact date (month + day)."""
        raw = {"month": 1, "day": 24, "year": 2026, "city": "Paris"}
        filters = SearchFilters.from_llm_output(raw)

        assert filters.date_min == date(2026, 1, 24)
        assert filters.date_max == date(2026, 1, 24)
        assert filters.date_range_type == DateRangeType.EXACT_DATE
        assert filters.city == "Paris"

    def test_weekend_extraction(self):
        """Test extraction of weekend (multiple days)."""
        raw = {"month": 1, "day": [24, 25], "year": 2026}
        filters = SearchFilters.from_llm_output(raw)

        assert filters.date_min == date(2026, 1, 24)
        assert filters.date_max == date(2026, 1, 25)
        assert filters.date_range_type == DateRangeType.WEEKEND

    def test_month_only_extraction(self):
        """Test extraction of month only (should expand to full month range)."""
        raw = {"month": 3, "year": 2026}
        filters = SearchFilters.from_llm_output(raw)

        assert filters.date_min == date(2026, 3, 1)
        assert filters.date_max == date(2026, 3, 31)
        assert filters.date_range_type == DateRangeType.DATE_RANGE

    def test_city_normalization(self):
        """Test city name normalization."""
        raw = {"city": "paris"}
        filters = SearchFilters.from_llm_output(raw)
        assert filters.city == "Paris"

        raw = {"city": "Paris, France"}
        filters = SearchFilters.from_llm_output(raw)
        assert filters.city == "Paris"

        raw = {"city": "ile de france"}
        filters = SearchFilters.from_llm_output(raw)
        assert filters.city == "Île-de-France"

    def test_category_normalization(self):
        """Test category normalization."""
        raw = {"category": "JAZZ"}
        filters = SearchFilters.from_llm_output(raw)
        assert filters.category == "jazz"

        raw = {"category": "Classical Music"}
        filters = SearchFilters.from_llm_output(raw)
        assert filters.category == "classical"

    def test_no_filters(self):
        """Test empty filter dict."""
        raw = {}
        filters = SearchFilters.from_llm_output(raw)

        assert filters.city is None
        assert filters.date_min is None
        assert filters.date_max is None
        assert filters.category is None
        assert not filters.has_date_filter()
        assert not filters.has_city_filter()


class TestSearchFiltersMatching:
    """Test SearchFilters.matches() method."""

    def test_matches_city(self):
        """Test city matching."""
        filters = SearchFilters(city="Paris")
        event = Event(
            event_id="1",
            title="Test Event",
            location=EventLocation(city="Paris")
        )
        assert filters.matches(event)

        event_versailles = Event(
            event_id="2",
            title="Test Event 2",
            location=EventLocation(city="Versailles")
        )
        assert not filters.matches(event_versailles)

    def test_matches_date_exact(self):
        """Test exact date matching."""
        filters = SearchFilters(
            date_min=date(2026, 1, 24),
            date_max=date(2026, 1, 24)
        )
        event = Event(
            event_id="1",
            title="Test Event",
            start_date=datetime(2026, 1, 24, 10, 0)
        )
        assert filters.matches(event)

        event_wrong_date = Event(
            event_id="2",
            title="Test Event 2",
            start_date=datetime(2026, 1, 25, 10, 0)
        )
        assert not filters.matches(event_wrong_date)

    def test_matches_date_range(self):
        """Test date range matching."""
        filters = SearchFilters(
            date_min=date(2026, 1, 24),
            date_max=date(2026, 1, 31)
        )
        event = Event(
            event_id="1",
            title="Test Event",
            start_date=datetime(2026, 1, 25, 10, 0)
        )
        assert filters.matches(event)

        event_before = Event(
            event_id="2",
            title="Test Event 2",
            start_date=datetime(2026, 1, 23, 10, 0)
        )
        assert not filters.matches(event_before)

    def test_matches_category(self):
        """Test category matching (bidirectional substring)."""
        filters = SearchFilters(category="jazz")
        event = Event(
            event_id="1",
            title="Jazz Concert",
            category="Jazz"
        )
        assert filters.matches(event)

        event_classical = Event(
            event_id="2",
            title="Classical Concert",
            category="Classical"
        )
        assert not filters.matches(event_classical)

    def test_matches_is_free(self):
        """Test free event matching."""
        filters = SearchFilters(is_free=True)
        event_free = Event(
            event_id="1",
            title="Free Event",
            conditions="Entrée gratuite"
        )
        assert filters.matches(event_free)

        event_paid = Event(
            event_id="2",
            title="Paid Event",
            conditions="10€"
        )
        assert not filters.matches(event_paid)

    def test_matches_multiple_filters(self):
        """Test matching with multiple filters."""
        filters = SearchFilters(
            city="Paris",
            date_min=date(2026, 1, 24),
            date_max=date(2026, 1, 24),
            category="jazz"
        )
        event_match = Event(
            event_id="1",
            title="Jazz Concert",
            category="Jazz",
            location=EventLocation(city="Paris"),
            start_date=datetime(2026, 1, 24, 20, 0)
        )
        assert filters.matches(event_match)

        # Wrong city
        event_wrong_city = Event(
            event_id="2",
            title="Jazz Concert",
            category="Jazz",
            location=EventLocation(city="Lyon"),
            start_date=datetime(2026, 1, 24, 20, 0)
        )
        assert not filters.matches(event_wrong_city)


class TestSearchFiltersHelpers:
    """Test helper methods on SearchFilters."""

    def test_remove_city(self):
        """Test remove_city() creates copy without city."""
        filters = SearchFilters(
            city="Paris",
            date_min=date(2026, 1, 24),
            category="jazz"
        )
        nearby_filters = filters.remove_city()

        assert nearby_filters.city is None
        assert nearby_filters.date_min == date(2026, 1, 24)
        assert nearby_filters.category == "jazz"
        # Original unchanged
        assert filters.city == "Paris"

    def test_expand_date_window(self):
        """Test expand_date_window() creates wider range."""
        filters = SearchFilters(
            date_min=date(2026, 1, 24),
            date_max=date(2026, 1, 24)
        )
        expanded = filters.expand_date_window(days=7)

        assert expanded.date_min == date(2026, 1, 17)
        assert expanded.date_max == date(2026, 1, 31)
        # Original unchanged
        assert filters.date_min == date(2026, 1, 24)

    def test_has_date_filter(self):
        """Test has_date_filter() helper."""
        filters_no_date = SearchFilters(city="Paris")
        assert not filters_no_date.has_date_filter()

        filters_with_date = SearchFilters(date_min=date(2026, 1, 24))
        assert filters_with_date.has_date_filter()

    def test_has_city_filter(self):
        """Test has_city_filter() helper."""
        filters_no_city = SearchFilters(category="jazz")
        assert not filters_no_city.has_city_filter()

        filters_with_city = SearchFilters(city="Paris")
        assert filters_with_city.has_city_filter()

        # Regional term is not a city filter
        filters_regional = SearchFilters(city="Île-de-France")
        assert not filters_regional.has_city_filter()


class TestSearchFiltersEdgeCases:
    """Test edge cases and error handling."""

    def test_invalid_date(self):
        """Test invalid date extraction (should log warning, not crash)."""
        raw = {"month": 2, "day": 30, "year": 2026}  # Feb 30 doesn't exist
        filters = SearchFilters.from_llm_output(raw)

        # Should handle gracefully
        assert filters.date_min is None
        assert filters.date_max is None

    def test_date_min_greater_than_max_swaps(self):
        """Test that date_min > date_max gets swapped in __post_init__."""
        filters = SearchFilters(
            date_min=date(2026, 1, 31),
            date_max=date(2026, 1, 1)
        )
        # Should swap
        assert filters.date_min == date(2026, 1, 1)
        assert filters.date_max == date(2026, 1, 31)

    def test_event_without_location(self):
        """Test matching event without location."""
        filters = SearchFilters(city="Paris")
        event_no_location = Event(
            event_id="1",
            title="Virtual Event"
        )
        assert not filters.matches(event_no_location)

    def test_event_without_date(self):
        """Test matching event without start_date."""
        filters = SearchFilters(date_min=date(2026, 1, 24))
        event_no_date = Event(
            event_id="1",
            title="TBD Event"
        )
        assert not filters.matches(event_no_date)

    def test_to_dict(self):
        """Test to_dict() serialization."""
        filters = SearchFilters(
            city="Paris",
            date_min=date(2026, 1, 24),
            category="jazz"
        )
        d = filters.to_dict()

        assert d["city"] == "Paris"
        assert d["date_min"] == "2026-01-24"
        assert d["category"] == "jazz"
        assert d["is_free"] is None
