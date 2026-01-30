"""
FILE: test_manager_coverage.py
STATUS: Active
RESPONSIBILITY: Integration tests for retrieval manager coverage.

DEPENDENCIES (Who uses this file):
- pytest test runner
- Manager logic validation

IMPORTS (What this file needs):
- pytest: Test framework
- unittest.mock: Mocking, src.retrieval.orchestrator: RetrievalOrchestrator

LAST MAJOR UPDATE: 2026-01-31
MAINTAINER: QA Team
"""

import pytest
from datetime import date
from unittest.mock import MagicMock
from src.retrieval.manager import RetrievalManager, SearchIntent
from src.data.models import Event, EventLocation


@pytest.fixture
def mock_vs():
    """Setup mock Vector Store and its dependencies."""
    mock_vs = MagicMock()
    mock_vs.city_locator = MagicMock()

    # Mock city coordinates
    def get_coords(city):
        if city.lower() == "paris":
            return (48.8566, 2.3522)
        if city.lower() == "poissy":
            return (48.9298, 2.0441)
        return None

    mock_vs.city_locator.get_coords.side_effect = get_coords
    return mock_vs


class TestRetrievalManager:
    """Tests for multi-stage search logic."""

    def test_parse_intent(self, mock_vs):
        manager = RetrievalManager(mock_vs)
        filters = {"city": "Paris", "month": 2, "day": 14, "category": "Musique"}
        intent = manager.parse_intent(filters)

        assert intent.city == "Paris"
        assert intent.month == 2
        assert intent.days == [14]
        assert intent.category == "Musique"
        assert intent.target_date == date(2026, 2, 14)

    def test_execute_search_phase_1_exact(self, mock_vs):
        manager = RetrievalManager(mock_vs, k=5)

        # Create a mock event
        evt = MagicMock(spec=Event)
        evt.event_id = "evt-1"
        evt.get_metadata.return_value = {"title": "Exact Match"}
        evt.to_text.return_value = "Content"

        # Mock vector store search to return exact match
        mock_vs.search.return_value = [(evt, 0.9)]

        intent = SearchIntent(city="Paris", month=2)
        result = manager.execute_search("jazz", intent)

        assert len(result["docs"]) == 1
        assert result["docs"][0].metadata["match_type"] == "Exact Match"
        assert result["exact_count"] == 1

    def test_execute_search_phase_2_nearby(self, mock_vs):
        manager = RetrievalManager(mock_vs, k=5)

        # 1. Setup Phase 1: 0 results
        # 2. Setup Phase 2: return 1 result in Poissy

        evt_nearby = MagicMock(spec=Event)
        evt_nearby.event_id = "evt-2"
        evt_nearby.location = MagicMock(spec=EventLocation)
        evt_nearby.location.city = "Poissy"
        evt_nearby.location.coordinates = {"lat": 48.9298, "lon": 2.0441}
        evt_nearby.get_metadata.return_value = {"title": "Nearby Match"}
        evt_nearby.to_text.return_value = "Content"

        # mock_vs.search is called multiple times:
        # _search_exact (Phase 1)
        # _search_nearby_locations (Phase 2)
        # _count_total_matches (Phase 5)
        mock_vs.search.side_with_args = {"metadata_filter": {"city": "Paris", "month": 2, "year": 2026}}

        # Define side effect to return different results based on filters
        def search_side_effect(query, k, metadata_filter, **kwargs):
            if "city" in metadata_filter:  # Exact search
                return []
            else:  # Nearby search (city filter removed)
                return [(evt_nearby, 0.8)]

        mock_vs.search.side_effect = search_side_effect

        intent = SearchIntent(city="Paris", month=2)
        result = manager.execute_search("jazz", intent)

        assert len(result["docs"]) == 1
        assert result["docs"][0].metadata["match_type"] == "Nearby Location"
        assert result["docs"][0].metadata["distance_km"] > 0

        def test_execute_search_phase_3_alt_dates(self, mock_vs):
            manager = RetrievalManager(mock_vs, k=5)

            # Mock result for Phase 1
            evt = MagicMock(spec=Event)
            evt.event_id = "evt-1"
            evt.get_metadata.return_value = {"title": "Exact Match"}
            evt.to_text.return_value = "Content"

            # Mock result for Phase 3 (different ID)
            evt_alt = MagicMock(spec=Event)
            evt_alt.event_id = "evt-alt"

            def search_side_effect(query, k, metadata_filter, **kwargs):
                if "date_min" in metadata_filter and "date_max" in metadata_filter:
                    # If it's the +/- 7 days search
                    return [(evt_alt, 0.9)]
                return [(evt, 0.9)]

            mock_vs.search.side_effect = search_side_effect

            intent = SearchIntent(city="Paris", target_date=date(2026, 2, 14), month=2, days=[14])
            result = manager.execute_search("jazz", intent)

            # Verify SYSTEM_NOTE was added
            assert "nearby_date_note" in result["docs"][0].metadata
            assert "ALTERNATIVE DATES" in result["docs"][0].metadata["nearby_date_note"]
            assert "Found 1 events" in result["docs"][0].metadata["nearby_date_note"]

    def test_execute_search_limit_enforcement(self, mock_vs):
        manager = RetrievalManager(mock_vs, k=2)

        # Return 5 events from VS
        evts = []
        for i in range(5):
            e = MagicMock(spec=Event)
            e.event_id = f"evt-{i}"
            e.get_metadata.return_value = {"title": f"Event {i}"}
            e.to_text.return_value = "Content"
            evts.append((e, 0.9 - i * 0.1))

        mock_vs.search.return_value = evts

        result = manager.execute_search("jazz", SearchIntent(city="Paris"))

        # Should be truncated to k=2
        assert len(result["docs"]) == 2
        assert result["total_count"] == 2
