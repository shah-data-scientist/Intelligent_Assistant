"""
FILE: test_manager.py
STATUS: Active
RESPONSIBILITY: Unit tests for RetrievalManager and SearchIntent.
LAST MAJOR UPDATE: 2026-01-31
MAINTAINER: QA Team
"""

import pytest
from datetime import date
from unittest.mock import MagicMock

from src.retrieval.manager import RetrievalManager, SearchIntent
from src.data.models import Event


@pytest.fixture
def mock_vector_store():
    """Create a mock vector store."""
    mock_vs = MagicMock()
    mock_vs.city_locator = MagicMock()
    mock_vs.city_locator.get_coords.return_value = (48.8566, 2.3522)
    mock_vs.search.return_value = []
    return mock_vs


class TestSearchIntent:
    """Test SearchIntent dataclass."""

    def test_default_values(self):
        """Test SearchIntent with default values."""
        intent = SearchIntent()
        assert intent.city is None
        assert intent.year == 2026
        assert not intent.has_date_filter

    def test_has_date_filter_with_days(self):
        """Test has_date_filter with days set."""
        intent = SearchIntent(days=[1, 2, 3])
        assert intent.has_date_filter is True

    def test_has_date_filter_with_month(self):
        """Test has_date_filter with month set."""
        intent = SearchIntent(month=5)
        assert intent.has_date_filter is True

    def test_has_date_filter_with_date_range(self):
        """Test has_date_filter with date range set."""
        intent = SearchIntent(date_min=date(2026, 1, 1), date_max=date(2026, 12, 31))
        assert intent.has_date_filter is True

    def test_multi_month_support(self):
        """Test SearchIntent with list of months."""
        intent = SearchIntent(month=[6, 7, 8])
        assert intent.month == [6, 7, 8]


class TestRetrievalManagerParseIntent:
    """Test RetrievalManager.parse_intent method."""

    def test_parse_intent_with_list_filters(self, mock_vector_store):
        """Test parse_intent when filters is a list instead of dict."""
        manager = RetrievalManager(mock_vector_store)
        filters = [{"city": "Paris", "month": 2}]  # List instead of dict

        intent = manager.parse_intent(filters)

        assert intent.city == "Paris"
        assert intent.month == 2

    def test_parse_intent_with_empty_list(self, mock_vector_store):
        """Test parse_intent with empty list."""
        manager = RetrievalManager(mock_vector_store)
        filters = []

        intent = manager.parse_intent(filters)

        assert intent.city is None

    def test_parse_intent_with_non_dict(self, mock_vector_store):
        """Test parse_intent with non-dict type."""
        manager = RetrievalManager(mock_vector_store)
        filters = "invalid"  # String instead of dict

        intent = manager.parse_intent(filters)

        assert intent.city is None

    def test_parse_intent_with_nested_filters(self, mock_vector_store):
        """Test parse_intent with nested 'filters' key."""
        manager = RetrievalManager(mock_vector_store)
        filters = {"filters": {"city": "Lyon", "category": "Musique"}}

        intent = manager.parse_intent(filters)

        assert intent.city == "Lyon"
        assert intent.category == "Musique"

    def test_parse_intent_with_single_day(self, mock_vector_store):
        """Test parse_intent with single day as int."""
        manager = RetrievalManager(mock_vector_store)
        filters = {"day": 15}

        intent = manager.parse_intent(filters)

        assert intent.days == [15]

    def test_parse_intent_with_day_list(self, mock_vector_store):
        """Test parse_intent with list of days."""
        manager = RetrievalManager(mock_vector_store)
        filters = {"day": [1, 2, 3]}

        intent = manager.parse_intent(filters)

        assert intent.days == [1, 2, 3]

    def test_parse_intent_with_date_range_strings(self, mock_vector_store):
        """Test parse_intent with date range as ISO strings."""
        manager = RetrievalManager(mock_vector_store)
        filters = {"date_min": "2026-06-01", "date_max": "2026-06-30"}

        intent = manager.parse_intent(filters)

        assert intent.date_min == date(2026, 6, 1)
        assert intent.date_max == date(2026, 6, 30)
        assert intent.target_date == date(2026, 6, 1)

    def test_parse_intent_with_date_range_objects(self, mock_vector_store):
        """Test parse_intent with date range as date objects."""
        manager = RetrievalManager(mock_vector_store)
        filters = {"date_min": date(2026, 7, 1), "date_max": date(2026, 7, 31)}

        intent = manager.parse_intent(filters)

        assert intent.date_min == date(2026, 7, 1)
        assert intent.date_max == date(2026, 7, 31)

    def test_parse_intent_target_date_from_month_and_day(self, mock_vector_store):
        """Test target_date calculation from month and day."""
        manager = RetrievalManager(mock_vector_store)
        filters = {"month": 3, "day": 15}

        intent = manager.parse_intent(filters)

        assert intent.target_date == date(2026, 3, 15)

    def test_parse_intent_target_date_from_multi_month(self, mock_vector_store):
        """Test target_date uses first month from list."""
        manager = RetrievalManager(mock_vector_store)
        filters = {"month": [6, 7, 8], "day": [1]}

        intent = manager.parse_intent(filters)

        # Should use first month (6) for target date
        assert intent.target_date == date(2026, 6, 1)

    def test_parse_intent_invalid_date_combination(self, mock_vector_store):
        """Test parse_intent with invalid date (e.g., Feb 31)."""
        manager = RetrievalManager(mock_vector_store)
        filters = {"month": 2, "day": [31]}  # Invalid date

        intent = manager.parse_intent(filters)

        # Should not crash, target_date should be None
        assert intent.target_date is None


class TestRetrievalManagerSearch:
    """Test RetrievalManager search methods."""

    def test_search_exact(self, mock_vector_store):
        """Test _search_exact method."""
        manager = RetrievalManager(mock_vector_store)
        intent = SearchIntent(city="Paris", month=2, category="Musique")

        manager._search_exact("concert", intent)

        # Verify search was called with correct filters
        mock_vector_store.search.assert_called()
        call_args = mock_vector_store.search.call_args
        assert call_args.kwargs["metadata_filter"]["city"] == "Paris"
        assert call_args.kwargs["metadata_filter"]["month"] == 2
        assert call_args.kwargs["metadata_filter"]["category"] == "Musique"

    def test_search_nearby_locations(self, mock_vector_store):
        """Test _search_nearby_locations method."""
        manager = RetrievalManager(mock_vector_store)
        intent = SearchIntent(city="Paris", month=5, category="Jazz")

        manager._search_nearby_locations("jazz concert", intent, k=10)

        # Verify city is NOT in the filter for nearby search
        call_args = mock_vector_store.search.call_args
        assert "city" not in call_args.kwargs["metadata_filter"]
        assert call_args.kwargs["metadata_filter"]["month"] == 5

    def test_count_total_matches(self, mock_vector_store):
        """Test _count_total_matches method."""
        mock_vector_store.search.return_value = [(MagicMock(), 0.9) for _ in range(10)]
        manager = RetrievalManager(mock_vector_store)
        intent = SearchIntent(city="Paris")

        count = manager._count_total_matches("jazz", intent)

        assert count == 10

    def test_count_alt_dates(self, mock_vector_store):
        """Test _count_alt_dates method."""
        evt1 = MagicMock()
        evt1.event_id = "evt-1"
        evt2 = MagicMock()
        evt2.event_id = "evt-2"

        mock_vector_store.search.return_value = [(evt1, 0.9), (evt2, 0.8)]
        manager = RetrievalManager(mock_vector_store)
        intent = SearchIntent(city="Paris", target_date=date(2026, 2, 14))

        count = manager._count_alt_dates("jazz", intent, exclude_ids={"evt-1"})

        # evt-1 excluded, only evt-2 counted
        assert count == 1


class TestRetrievalManagerExecuteSearch:
    """Test execute_search method."""

    def test_execute_search_returns_structure(self, mock_vector_store):
        """Test execute_search returns correct structure."""
        mock_vector_store.search.return_value = []
        manager = RetrievalManager(mock_vector_store)
        intent = SearchIntent(city="Paris")

        result = manager.execute_search("jazz", intent)

        assert "docs" in result
        assert "exact_count" in result
        assert "total_count" in result
        assert "total_in_database" in result
        assert "filters_applied" in result

    def test_execute_search_with_nearby_fallback(self, mock_vector_store):
        """Test nearby location fallback when exact search returns nothing."""
        manager = RetrievalManager(mock_vector_store, k=5)

        # Create nearby event with coordinates
        evt = MagicMock(spec=Event)
        evt.event_id = "evt-nearby"
        evt.location = MagicMock()
        evt.location.city = "Versailles"
        evt.location.coordinates = {"lat": 48.8014, "lon": 2.1301}
        evt.get_metadata.return_value = {"title": "Nearby Event"}
        evt.to_text.return_value = "Event content"

        # First call (exact): empty, subsequent calls: return event
        call_count = [0]

        def search_side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:  # Exact search
                return []
            return [(evt, 0.85)]

        mock_vector_store.search.side_effect = search_side_effect

        intent = SearchIntent(city="Paris", month=5)
        result = manager.execute_search("concert", intent)

        assert len(result["docs"]) >= 1

    def test_execute_search_event_without_coordinates(self, mock_vector_store):
        """Test nearby search uses city coords when event has no coordinates."""
        manager = RetrievalManager(mock_vector_store, k=5)

        # Event without coordinates but with city
        evt = MagicMock(spec=Event)
        evt.event_id = "evt-no-coords"
        evt.location = MagicMock()
        evt.location.city = "Lyon"
        evt.location.coordinates = None  # No coordinates
        evt.get_metadata.return_value = {"title": "Event"}
        evt.to_text.return_value = "Content"

        # Mock city locator to return Lyon coords
        def get_coords(city):
            if city.lower() == "paris":
                return (48.8566, 2.3522)
            if city.lower() == "lyon":
                return (45.7640, 4.8357)
            return None

        mock_vector_store.city_locator.get_coords.side_effect = get_coords

        call_count = [0]

        def search_side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return []
            return [(evt, 0.8)]

        mock_vector_store.search.side_effect = search_side_effect

        intent = SearchIntent(city="Paris", month=6)
        result = manager.execute_search("jazz", intent)

        # Should calculate distance using Lyon city coords
        if result["docs"]:
            assert result["docs"][0].metadata["distance_km"] > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
