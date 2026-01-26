"""Tests for RetrievalOrchestrator - Phase 2 & 4 refactoring validation.

This test suite validates the multi-stage retrieval orchestrator that separates
concerns between retrieval (vector_store), filtering (SearchFilters), and
orchestration (RetrievalOrchestrator).
"""

import pytest
from datetime import date, datetime
from unittest.mock import Mock, MagicMock, patch

from src.retrieval.orchestrator import RetrievalOrchestrator
from src.retrieval.filters import SearchFilters
from src.data.models import Event, EventLocation


@pytest.fixture
def mock_vector_store():
    """Create a mock EventVectorStore."""
    mock_store = Mock()
    mock_store.city_locator = Mock()
    return mock_store


@pytest.fixture
def sample_events():
    """Create sample events for testing."""
    # Paris event
    event_paris = Event(
        event_id="paris-1",
        title="Jazz Concert in Paris",
        category="Musique",
        location=EventLocation(
            city="Paris",
            address="Place de la Bastille",
            coordinates={"lat": 48.8534, "lon": 2.3698}
        ),
        start_date=datetime(2026, 1, 24, 20, 0)
    )

    # Versailles event (nearby Paris)
    event_versailles = Event(
        event_id="versailles-1",
        title="Classical Concert in Versailles",
        category="Musique",
        location=EventLocation(
            city="Versailles",
            address="Château de Versailles",
            coordinates={"lat": 48.8049, "lon": 2.1204}
        ),
        start_date=datetime(2026, 1, 24, 19, 0)
    )

    # Pantin event (nearby Paris)
    event_pantin = Event(
        event_id="pantin-1",
        title="Hip-Hop Concert in Pantin",
        category="Musique",
        location=EventLocation(
            city="Pantin",
            address="Cabaret Sauvage",
            coordinates={"lat": 48.8975, "lon": 2.3939}
        ),
        start_date=datetime(2026, 1, 24, 21, 0)
    )

    # Alternative date event
    event_alt_date = Event(
        event_id="paris-alt",
        title="Jazz Concert Paris (Alt Date)",
        category="Musique",
        location=EventLocation(
            city="Paris",
            coordinates={"lat": 48.8566, "lon": 2.3522}
        ),
        start_date=datetime(2026, 1, 30, 20, 0)  # +6 days
    )

    return [event_paris, event_versailles, event_pantin, event_alt_date]


class TestOrchestratorExactMatchOnly:
    """Test exact match retrieval (no fallback needed)."""

    def test_exact_match_sufficient_results(self, mock_vector_store, sample_events):
        """Test when exact matches are sufficient (no fallback needed)."""
        # Setup: Return Paris event only
        event_paris = sample_events[0]
        mock_vector_store.search_raw.return_value = [(event_paris, 0.85)]

        # Create orchestrator
        orchestrator = RetrievalOrchestrator(mock_vector_store, k=1)

        # Search with Paris filter
        filters = SearchFilters(city="Paris", date_min=date(2026, 1, 24), date_max=date(2026, 1, 24))
        result = orchestrator.search("jazz concert", filters)

        # Verify
        assert result["total_count"] == 1
        assert result["exact_count"] == 1
        assert result["docs"][0].metadata["event_id"] == "paris-1"
        assert result["docs"][0].metadata["match_type"] == "Exact Match"

    def test_exact_match_filters_by_city(self, mock_vector_store, sample_events):
        """Test city filtering during exact match stage."""
        # Setup: Return both Paris and Versailles
        event_paris, event_versailles = sample_events[0], sample_events[1]
        mock_vector_store.search_raw.return_value = [
            (event_paris, 0.85),
            (event_versailles, 0.80)
        ]
        mock_vector_store.city_locator.get_coords.return_value = (48.8566, 2.3522)  # Paris coords

        # Use k=1 to prevent nearby fallback from triggering
        orchestrator = RetrievalOrchestrator(mock_vector_store, k=1)

        # Search with Paris filter only
        filters = SearchFilters(city="Paris")
        result = orchestrator.search("concert", filters)

        # Verify: Only Paris event returned (exact match)
        assert result["total_count"] == 1
        assert result["exact_count"] == 1
        assert result["docs"][0].metadata["event_id"] == "paris-1"
        assert result["docs"][0].metadata["match_type"] == "Exact Match"

    def test_exact_match_filters_by_date(self, mock_vector_store, sample_events):
        """Test date filtering during exact match stage."""
        # Setup: Return event on Jan 24
        event_paris = sample_events[0]
        mock_vector_store.search_raw.return_value = [(event_paris, 0.85)]

        orchestrator = RetrievalOrchestrator(mock_vector_store, k=5)

        # Search with wrong date filter
        filters = SearchFilters(city="Paris", date_min=date(2026, 1, 25), date_max=date(2026, 1, 25))
        result = orchestrator.search("jazz", filters)

        # Verify: No matches (date mismatch)
        assert result["total_count"] == 0
        assert result["exact_count"] == 0


class TestOrchestratorNearbyFallback:
    """Test nearby location fallback when exact matches insufficient."""

    def test_nearby_fallback_triggers_when_insufficient(self, mock_vector_store, sample_events):
        """Test that nearby search triggers when exact results < k."""
        # Setup: Only Versailles and Pantin available (no Paris)
        event_versailles, event_pantin = sample_events[1], sample_events[2]
        mock_vector_store.search_raw.return_value = [
            (event_versailles, 0.80),
            (event_pantin, 0.75)
        ]
        mock_vector_store.city_locator.get_coords.return_value = (48.8566, 2.3522)  # Paris coords

        orchestrator = RetrievalOrchestrator(mock_vector_store, k=8)

        # Search with Paris filter (but no exact matches)
        filters = SearchFilters(city="Paris", date_min=date(2026, 1, 24), date_max=date(2026, 1, 24))
        result = orchestrator.search("concert", filters)

        # Verify: Nearby matches returned
        assert result["total_count"] == 2
        assert result["exact_count"] == 0  # No exact Paris matches
        assert any(doc.metadata["match_type"] == "Nearby Location" for doc in result["docs"])

    def test_nearby_sorted_by_distance(self, mock_vector_store, sample_events):
        """Test that nearby results are sorted by distance from target city."""
        # Setup: Return Versailles (18km) and Pantin (8km) from Paris
        event_versailles, event_pantin = sample_events[1], sample_events[2]
        mock_vector_store.search_raw.return_value = [
            (event_versailles, 0.80),
            (event_pantin, 0.75)
        ]
        mock_vector_store.city_locator.get_coords.return_value = (48.8566, 2.3522)  # Paris coords

        orchestrator = RetrievalOrchestrator(mock_vector_store, k=8)

        filters = SearchFilters(city="Paris")
        result = orchestrator.search("concert", filters)

        # Verify: Pantin comes before Versailles (closer to Paris)
        assert result["docs"][0].metadata["event_id"] == "pantin-1"
        assert result["docs"][1].metadata["event_id"] == "versailles-1"
        assert result["docs"][0].metadata["distance_km"] < result["docs"][1].metadata["distance_km"]

    def test_nearby_respects_date_filters(self, mock_vector_store, sample_events):
        """Test that nearby fallback still respects date filters."""
        # Setup: Return events with different dates
        event_paris = sample_events[0]  # Jan 24
        event_alt_date = sample_events[3]  # Jan 30
        mock_vector_store.search_raw.return_value = [
            (event_paris, 0.85),
            (event_alt_date, 0.80)
        ]
        mock_vector_store.city_locator.get_coords.return_value = (48.8566, 2.3522)

        orchestrator = RetrievalOrchestrator(mock_vector_store, k=8)

        # Search with strict date filter (Jan 24 only)
        filters = SearchFilters(city="Versailles", date_min=date(2026, 1, 24), date_max=date(2026, 1, 24))
        result = orchestrator.search("jazz", filters)

        # Verify: Only Jan 24 event (even though it's not in Versailles)
        assert result["total_count"] == 1
        assert result["docs"][0].metadata["event_id"] == "paris-1"


class TestOrchestratorAlternativeDates:
    """Test alternative date detection (metadata only)."""

    def test_alternative_date_note_added(self, mock_vector_store, sample_events):
        """Test that alternative date note is added to metadata."""
        # Setup: Return exact match
        event_paris = sample_events[0]
        event_alt_date = sample_events[3]  # Alternative date event (Jan 30)
        mock_vector_store.search_raw.side_effect = [
            [(event_paris, 0.85)],  # First call: exact match search
            [],  # Second call: nearby fallback (triggered since 1 < k=8)
            [(event_alt_date, 0.80)]  # Third call: alternative dates search
        ]
        mock_vector_store.city_locator.get_coords.return_value = (48.8566, 2.3522)

        orchestrator = RetrievalOrchestrator(mock_vector_store, k=8)

        # Search with city + date
        filters = SearchFilters(city="Paris", date_min=date(2026, 1, 24), date_max=date(2026, 1, 24))
        result = orchestrator.search("jazz", filters)

        # Verify: Alternative date note present
        assert "nearby_date_note" in result["docs"][0].metadata
        assert "ALTERNATIVE DATES" in result["docs"][0].metadata["nearby_date_note"]

    def test_no_alternative_date_note_without_filters(self, mock_vector_store, sample_events):
        """Test no alternative date check when no city or date filters."""
        event_paris = sample_events[0]
        mock_vector_store.search_raw.return_value = [(event_paris, 0.85)]

        orchestrator = RetrievalOrchestrator(mock_vector_store, k=8)

        # Search without filters
        filters = SearchFilters()
        result = orchestrator.search("jazz", filters)

        # Verify: No alt date note (no filters to expand)
        assert "nearby_date_note" not in result["docs"][0].metadata


class TestOrchestratorDeduplication:
    """Test deduplication across stages."""

    def test_deduplication_across_stages(self, mock_vector_store, sample_events):
        """Test that same event ID is not returned twice."""
        # Setup: Same event returned in both calls
        event_paris = sample_events[0]
        mock_vector_store.search_raw.return_value = [
            (event_paris, 0.85),
            (event_paris, 0.82)  # Duplicate
        ]

        orchestrator = RetrievalOrchestrator(mock_vector_store, k=8)

        filters = SearchFilters(city="Paris")
        result = orchestrator.search("jazz", filters)

        # Verify: Only one instance
        assert result["total_count"] == 1
        event_ids = [doc.metadata["event_id"] for doc in result["docs"]]
        assert len(event_ids) == len(set(event_ids))  # All unique


class TestOrchestratorMetadataEnrichment:
    """Test metadata enrichment in results."""

    def test_metadata_enrichment_score(self, mock_vector_store, sample_events):
        """Test that similarity score is added to metadata."""
        event_paris = sample_events[0]
        mock_vector_store.search_raw.return_value = [(event_paris, 0.85)]

        orchestrator = RetrievalOrchestrator(mock_vector_store, k=1)

        filters = SearchFilters(city="Paris")
        result = orchestrator.search("jazz", filters)

        # Verify: Score in metadata
        assert result["docs"][0].metadata["score"] == 0.85

    def test_metadata_enrichment_match_type(self, mock_vector_store, sample_events):
        """Test that match_type is added to metadata."""
        event_paris = sample_events[0]
        mock_vector_store.search_raw.return_value = [(event_paris, 0.85)]

        orchestrator = RetrievalOrchestrator(mock_vector_store, k=1)

        filters = SearchFilters(city="Paris")
        result = orchestrator.search("jazz", filters)

        # Verify: Match type present
        assert result["docs"][0].metadata["match_type"] == "Exact Match"

    def test_metadata_enrichment_distance(self, mock_vector_store, sample_events):
        """Test that distance_km is added for nearby matches."""
        event_versailles = sample_events[1]
        mock_vector_store.search_raw.return_value = [(event_versailles, 0.80)]
        mock_vector_store.city_locator.get_coords.return_value = (48.8566, 2.3522)  # Paris

        orchestrator = RetrievalOrchestrator(mock_vector_store, k=8)

        filters = SearchFilters(city="Paris")
        result = orchestrator.search("concert", filters)

        # Verify: Distance present and >0 (Versailles is ~18km from Paris)
        assert result["docs"][0].metadata["distance_km"] > 10


class TestOrchestratorEmptyResults:
    """Test empty result handling."""

    def test_empty_results_when_no_matches(self, mock_vector_store):
        """Test that empty results are handled gracefully."""
        mock_vector_store.search_raw.return_value = []

        orchestrator = RetrievalOrchestrator(mock_vector_store, k=8)

        filters = SearchFilters(city="Tokyo")  # No events in Tokyo
        result = orchestrator.search("concert", filters)

        # Verify: Empty but valid response
        assert result["total_count"] == 0
        assert result["exact_count"] == 0
        assert result["docs"] == []

    def test_empty_exact_triggers_nearby(self, mock_vector_store, sample_events):
        """Test that 0 exact matches triggers nearby search."""
        # First call: no exact matches, Second call: nearby match
        event_versailles = sample_events[1]
        mock_vector_store.search_raw.side_effect = [
            [],  # No exact matches
            [(event_versailles, 0.80)]  # Nearby match
        ]
        mock_vector_store.city_locator.get_coords.return_value = (48.8566, 2.3522)

        orchestrator = RetrievalOrchestrator(mock_vector_store, k=8)

        filters = SearchFilters(city="Paris")
        result = orchestrator.search("concert", filters)

        # Verify: Nearby match returned
        assert result["total_count"] == 1
        assert result["exact_count"] == 0
        assert result["docs"][0].metadata["match_type"] == "Nearby Location"
