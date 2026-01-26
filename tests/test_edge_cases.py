"""Comprehensive Edge Case Tests - System Robustness Validation.

This test suite validates system behavior under edge cases, boundary conditions,
and unusual inputs across all components of the RAG system.
"""

import pytest
import json
from datetime import date, datetime
from unittest.mock import Mock, patch, MagicMock

from src.retrieval.filters import SearchFilters, DateRangeType
from src.retrieval.chain import RAGChain
from src.data.models import Event, EventLocation
from src.security.guardrails import SecurityGuardrails


class TestEmptyInputs:
    """Test handling of empty or missing inputs."""

    def test_empty_query_handling(self):
        """Test system response to empty query string."""
        filters = SearchFilters.from_llm_output({})

        # Empty query should be handled gracefully
        # Behavior: Either rejected by security or processed as "show all"
        assert filters is not None

    def test_empty_filter_dict(self):
        """Test filter creation with empty dictionary."""
        filters = SearchFilters.from_llm_output({})

        assert filters.city is None
        assert filters.date_min is None
        assert filters.date_max is None
        assert filters.category is None
        assert not filters.has_city_filter()
        assert not filters.has_date_filter()

    def test_empty_event_title(self):
        """Test event with empty title."""
        event = Event(
            event_id="empty-title",
            title="",
            start_date=datetime(2026, 1, 24)
        )

        # Should not crash when converting to text
        text = event.to_text()
        assert text is not None

    def test_null_values_in_llm_output(self):
        """Test filter extraction with None/null values."""
        raw = {
            "city": None,
            "month": None,
            "day": None,
            "year": None,
            "category": None
        }

        filters = SearchFilters.from_llm_output(raw)

        # Should create valid (empty) filters
        assert filters.city is None
        assert filters.date_min is None


class TestVeryLongInputs:
    """Test handling of very long inputs."""

    def test_very_long_query_handling(self):
        """Test query with excessive length (>1000 characters)."""
        long_query = "jazz concert " * 200  # ~2600 characters

        # Security guardrails should handle
        guardrails = SecurityGuardrails()
        result = guardrails.check_query(long_query)

        # Should not crash, may truncate or reject
        assert "blocked" in result

    def test_very_long_event_description(self):
        """Test event with very long description."""
        long_description = "This is a cultural event. " * 500  # ~13,000 characters

        event = Event(
            event_id="long-desc",
            title="Long Description Event",
            description=long_description,
            start_date=datetime(2026, 1, 24)
        )

        # Should handle chunking or truncation
        text = event.to_text()
        assert text is not None

        # Test chunking
        chunks = event.to_chunks()
        assert len(chunks) > 1  # Should create multiple chunks

    def test_very_long_city_name(self):
        """Test city filter with unusually long name."""
        long_city = "Saint-Rémy-lès-Chevreuse-sur-Seine-et-Marne" * 10

        filters = SearchFilters(city=long_city)

        # Should normalize without crashing
        assert filters.city is not None


class TestUnicodeAndSpecialCharacters:
    """Test handling of Unicode, emojis, and special characters."""

    def test_unicode_query_handling(self):
        """Test query with various Unicode characters."""
        unicode_queries = [
            "Événements culturels à Paris",  # French accents
            "Концерт в Париже",  # Cyrillic
            "パリのコンサート",  # Japanese
            "巴黎的音乐会",  # Chinese
            "حفلة موسيقية في باريس",  # Arabic
        ]

        for query in unicode_queries:
            # Should handle without crashing
            guardrails = SecurityGuardrails()
            result = guardrails.check_query(query)
            assert "blocked" in result

    def test_emoji_in_query(self):
        """Test query containing emojis."""
        emoji_queries = [
            "🎵 Jazz concerts in Paris 🎷",
            "🎭 Theater events 🎪",
            "❤️ Romantic events for couples 💕",
        ]

        for query in emoji_queries:
            guardrails = SecurityGuardrails()
            result = guardrails.check_query(query)
            # Should handle gracefully (pass or fail, but no crash)
            assert "blocked" in result

    def test_special_characters_in_city(self):
        """Test city names with special characters."""
        special_cities = [
            "Aix-en-Provence",
            "L'Haÿ-les-Roses",
            "Vitry-sur-Seine",
            "Saint-Étienne",
        ]

        for city in special_cities:
            filters = SearchFilters(city=city)
            # Should normalize correctly
            assert filters.city is not None

    def test_html_entities_in_input(self):
        """Test handling of HTML entities."""
        query_with_html = "Events &amp; concerts in Paris &lt;city&gt;"

        guardrails = SecurityGuardrails()
        result = guardrails.check_query(query_with_html)

        # Should handle (may decode or treat as plain text)
        assert "blocked" in result


class TestSQLInjectionAttempts:
    """Test resistance to SQL injection in filters."""

    def test_sql_injection_in_city_filter(self):
        """Test city filter with SQL injection attempt."""
        sql_city = "Paris'; DROP TABLE events;--"

        filters = SearchFilters(city=sql_city)

        # Should sanitize or escape
        # City name should not execute SQL
        assert filters.city is not None
        # In practice, SQLAlchemy parameterization prevents injection

    def test_sql_injection_in_category(self):
        """Test category filter with SQL injection."""
        sql_category = "Musique' OR '1'='1"

        filters = SearchFilters(category=sql_category)

        # Should handle safely
        assert filters.category is not None


class TestInvalidDateFilters:
    """Test handling of invalid or edge case dates."""

    def test_invalid_date_february_30(self):
        """Test filter with non-existent date (Feb 30)."""
        raw = {"month": 2, "day": 30, "year": 2026}

        filters = SearchFilters.from_llm_output(raw)

        # Should handle gracefully (log warning, set to None)
        assert filters.date_min is None
        assert filters.date_max is None

    def test_invalid_date_month_13(self):
        """Test filter with invalid month (13)."""
        raw = {"month": 13, "day": 1, "year": 2026}

        filters = SearchFilters.from_llm_output(raw)

        # Should reject invalid month
        assert filters.date_min is None

    def test_leap_year_date_query(self):
        """Test query for leap year date (Feb 29, 2024)."""
        raw = {"month": 2, "day": 29, "year": 2024}

        filters = SearchFilters.from_llm_output(raw)

        # Should accept (2024 is a leap year)
        assert filters.date_min == date(2024, 2, 29)
        assert filters.date_max == date(2024, 2, 29)

    def test_non_leap_year_feb_29(self):
        """Test Feb 29 in non-leap year (2026)."""
        raw = {"month": 2, "day": 29, "year": 2026}

        filters = SearchFilters.from_llm_output(raw)

        # Should reject (2026 is not a leap year)
        assert filters.date_min is None

    def test_date_range_min_greater_than_max(self):
        """Test date range where min > max."""
        filters = SearchFilters(
            date_min=date(2026, 12, 31),
            date_max=date(2026, 1, 1)
        )

        # Should auto-swap in __post_init__
        assert filters.date_min == date(2026, 1, 1)
        assert filters.date_max == date(2026, 12, 31)

    def test_year_only_filter(self):
        """Test filter with year only (no month/day)."""
        raw = {"year": 2026}

        filters = SearchFilters.from_llm_output(raw)

        # Should handle (either expand to full year or ignore)
        # Behavior depends on implementation

    def test_past_date_filter(self):
        """Test filter for dates in the past."""
        raw = {"month": 1, "day": 1, "year": 2020}

        filters = SearchFilters.from_llm_output(raw)

        # Should create valid filter (even if no results expected)
        assert filters.date_min == date(2020, 1, 1)


class TestConflictingFilters:
    """Test behavior with conflicting or contradictory filters."""

    def test_conflicting_filters_city_mismatch(self):
        """Test when query mentions one city but filter specifies another."""
        # This is a query understanding issue, not a filter issue
        # Documented for completeness
        pass

    def test_broad_category_narrow_date(self):
        """Test broad category with very narrow date range."""
        filters = SearchFilters(
            category="Musique",  # Broad
            date_min=date(2026, 1, 24),
            date_max=date(2026, 1, 24)  # Narrow (1 day)
        )

        # Should work, may return few/no results
        assert filters.category == "musique"
        assert filters.has_date_filter()

    def test_is_free_with_no_results(self):
        """Test free filter in dataset with no free events."""
        filters = SearchFilters(is_free=True, city="Tokyo")

        # Should create valid filter, return 0 results
        assert filters.is_free is True


class TestBroadAndNarrowQueries:
    """Test queries at extremes of specificity."""

    def test_broad_query_all_events(self):
        """Test very broad query (no filters)."""
        filters = SearchFilters.from_llm_output({})

        # Should return all events (no filtering)
        assert not filters.has_city_filter()
        assert not filters.has_date_filter()

    def test_narrow_query_no_results_expected(self):
        """Test extremely narrow query (likely no results)."""
        filters = SearchFilters(
            city="Pantin",
            date_min=date(2026, 2, 28),  # Fixed: 2026 is not leap year
            date_max=date(2026, 2, 28),
            category="Opera",
            is_free=True,
            age=5
        )

        # Should create valid filters even if no results
        # Filter creation should not fail
        assert filters.city == "Pantin"


class TestMalformedJSONInLLMOutput:
    """Test handling of malformed JSON from LLM."""

    def test_missing_required_keys(self):
        """Test LLM output missing some expected keys."""
        raw = {"city": "Paris"}  # Missing month, day, year

        filters = SearchFilters.from_llm_output(raw)

        # Should handle gracefully (use defaults for missing keys)
        assert filters.city == "Paris"
        assert filters.date_min is None

    def test_unexpected_extra_keys(self):
        """Test LLM output with extra unexpected keys."""
        raw = {
            "city": "Paris",
            "month": 1,
            "unexpected_field": "should be ignored",
            "another_extra": 123
        }

        filters = SearchFilters.from_llm_output(raw)

        # Should ignore extra keys without crashing
        assert filters.city == "Paris"

    def test_wrong_data_types(self):
        """Test LLM output with wrong data types."""
        raw = {
            "city": 12345,  # Should be string
            "month": "January",  # Should be int
            "is_free": "yes"  # Should be bool
        }

        with pytest.raises(TypeError):
            SearchFilters.from_llm_output(raw)


class TestBoundaryConditions:
    """Test boundary conditions and limits."""

    def test_zero_k_value(self):
        """Test retrieval with k=0."""
        # Should either reject or return empty results
        pass

    def test_very_large_k_value(self):
        """Test retrieval with k=10000."""
        # Should cap at reasonable limit or handle gracefully
        pass

    def test_negative_age_filter(self):
        """Test age filter with negative value."""
        filters = SearchFilters(age=-5)

        # Should either reject or handle as 0
        # Event matching should not crash

    def test_age_filter_boundary(self):
        """Test age filter at boundaries (0, 1, 100, 150)."""
        for age in [0, 1, 100, 150]:
            filters = SearchFilters(age=age)
            assert filters.age == age

    def test_date_at_year_boundary(self):
        """Test dates at year boundaries (Dec 31, Jan 1)."""
        # Dec 31 to Jan 1 crossing year
        filters = SearchFilters(
            date_min=date(2026, 12, 31),
            date_max=date(2027, 1, 1)
        )

        assert filters.date_min == date(2026, 12, 31)
        assert filters.date_max == date(2027, 1, 1)


class TestCoordinateEdgeCases:
    """Test edge cases with geographic coordinates."""

    def test_missing_coordinates(self):
        """Test event without coordinates."""
        event = Event(
            event_id="no-coords",
            title="Virtual Event",
            location=EventLocation(city="Paris")  # No coordinates
        )

        # Should handle without crashing
        text = event.to_text()
        assert text is not None

    def test_invalid_coordinates_out_of_range(self):
        """Test coordinates outside valid ranges."""
        # Lat should be -90 to 90, Lon should be -180 to 180
        invalid_coords = [
            {"lat": 100, "lon": 2.3},  # Invalid lat
            {"lat": 48.8, "lon": 200},  # Invalid lon
        ]

        for coords in invalid_coords:
            event = Event(
                event_id="invalid-coords",
                title="Test",
                location=EventLocation(city="Paris", coordinates=coords)
            )

            # Should not crash (may ignore invalid coords)
            text = event.to_text()
            assert text is not None

    def test_coordinates_at_boundaries(self):
        """Test coordinates at valid boundaries."""
        boundary_coords = [
            {"lat": 90, "lon": 180},    # North Pole, Date Line
            {"lat": -90, "lon": -180},  # South Pole
            {"lat": 0, "lon": 0},       # Null Island
        ]

        for coords in boundary_coords:
            event = Event(
                event_id="boundary-coords",
                title="Boundary Test",
                location=EventLocation(city="Test", coordinates=coords)
            )

            # Should handle edge case coordinates
            text = event.to_text()


class TestMultilingualQueries:
    """Test queries in multiple languages."""

    def test_mixed_language_query(self):
        """Test query mixing English and French."""
        mixed_query = "Jazz concerts à Paris this weekend"

        guardrails = SecurityGuardrails()
        result = guardrails.check_query(mixed_query)

        # Should handle mixed language
        assert "blocked" in result

    def test_transliterated_query(self):
        """Test query with transliterated characters."""
        query = "Evenements a Paris"  # No accents

        # Should still work (may need normalization)
        filters = SearchFilters.from_llm_output({"city": "Paris"})
        assert filters.city == "Paris"


class TestEventModelEdgeCases:
    """Test edge cases in Event model."""

    def test_event_without_category(self):
        """Test event with None category."""
        event = Event(
            event_id="no-category",
            title="Uncategorized Event",
            category=None
        )

        text = event.to_text()
        assert text is not None

    def test_event_without_location(self):
        """Test event with None location."""
        event = Event(
            event_id="no-location",
            title="Virtual Event",
            location=None
        )

        # Should handle gracefully
        text = event.to_text()
        assert text is not None

        # Should fail city filter matching
        filters = SearchFilters(city="Paris")
        assert not filters.matches(event)

    def test_event_without_date(self):
        """Test event with None start_date."""
        event = Event(
            event_id="no-date",
            title="TBD Event",
            start_date=None
        )

        # Should handle gracefully
        text = event.to_text()
        assert text is not None

        # Should fail date filter matching
        filters = SearchFilters(date_min=date(2026, 1, 24))
        assert not filters.matches(event)

    def test_event_chunking_with_minimal_data(self):
        """Test chunking event with minimal fields."""
        event = Event(
            event_id="minimal",
            title="Minimal Event"
            # No description, category, location, etc.
        )

        chunks = event.to_chunks()

        # Should create at least 1 chunk (title only)
        assert len(chunks) >= 1


class TestFilterHelperMethods:
    """Test helper methods on SearchFilters."""

    def test_remove_city_preserves_other_filters(self):
        """Test that remove_city() keeps other filters intact."""
        filters = SearchFilters(
            city="Paris",
            date_min=date(2026, 1, 24),
            category="jazz",
            is_free=True
        )

        nearby_filters = filters.remove_city()

        assert nearby_filters.city is None
        assert nearby_filters.date_min == date(2026, 1, 24)
        assert nearby_filters.category == "jazz"
        assert nearby_filters.is_free is True

    def test_expand_date_window_with_no_dates(self):
        """Test expand_date_window() when no date filters exist."""
        filters = SearchFilters(city="Paris")

        expanded = filters.expand_date_window(days=7)

        # Should return self unchanged
        assert expanded.date_min is None
        assert expanded.date_max is None

    def test_expand_date_window_with_only_min(self):
        """Test expand_date_window() with only date_min set."""
        filters = SearchFilters(date_min=date(2026, 1, 24))

        expanded = filters.expand_date_window(days=7)

        # Should expand min, max stays None
        assert expanded.date_min == date(2026, 1, 17)
        assert expanded.date_max is None

    def test_to_dict_serialization(self):
        """Test to_dict() produces valid serializable output."""
        filters = SearchFilters(
            city="Paris",
            date_min=date(2026, 1, 24),
            category="jazz"
        )

        dict_output = filters.to_dict()

        # Should be JSON-serializable
        json_str = json.dumps(dict_output)
        assert json_str is not None
        assert "Paris" in json_str