"""Tests for EventVectorStore and semantic search."""

import shutil
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from src.data.models import Event, EventLocation
from src.models.vector_store import EventVectorStore


@pytest.fixture
def temp_dir() -> Path:
    """Create temporary directory for testing."""
    tmpdir = tempfile.mkdtemp()
    yield Path(tmpdir)
    shutil.rmtree(tmpdir)


@pytest.fixture
def mock_embedder() -> MagicMock:
    """Mock EventEmbedder to avoid API calls."""
    embedder = MagicMock()
    # Return 1024-dim random vectors
    embedder.embed_events.side_effect = lambda events: [np.random.rand(1024).tolist() for _ in events]
    embedder.embed_query.return_value = np.random.rand(1024).tolist()
    return embedder


@pytest.fixture
def sample_events() -> list[Event]:
    """Create sample events for indexing."""
    events = []
    for i in range(10):
        e = Event(
            event_id=f"test-{i}",
            title=f"Event {i}",
            description=f"Description for event {i}",
            category="Music" if i % 2 == 0 else "Art",
        )
        # Add location data for geo tests
        if i < 5:
            e.location = EventLocation(city="Paris", coordinates={"lat": 48.85, "lon": 2.35})
        else:
            e.location = EventLocation(city="Versailles", coordinates={"lat": 48.80, "lon": 2.13})
        events.append(e)
    return events


@pytest.fixture
def vector_store(temp_dir: Path, mock_embedder: MagicMock) -> EventVectorStore:
    """Create EventVectorStore instance for testing."""
    # Mock EventStorage AND CityLocator
    with (
        patch("src.models.vector_store.EventStorage") as mock_storage_class,
        patch("src.models.vector_store.CityLocator") as mock_locator_class,
    ):

        mock_storage = MagicMock()
        mock_storage_class.return_value = mock_storage

        # Mock CityLocator to return fixed coords for Paris
        mock_locator = MagicMock()
        mock_locator.get_coords.side_effect = lambda city: (48.85, 2.35) if city.lower() == "paris" else None
        mock_locator_class.return_value = mock_locator

        vs = EventVectorStore(
            index_path=str(temp_dir),
            embedder=mock_embedder,
        )
        # Manually set mocks
        vs.storage = mock_storage
        vs.city_locator = mock_locator

        yield vs
        vs.close()


def test_build_index(vector_store: EventVectorStore, sample_events: list[Event]) -> None:
    """Test building Hybrid index (FAISS + BM25)."""
    stats = vector_store.build_index(sample_events)

    assert stats["events_indexed"] == 10
    assert vector_store.index is not None
    assert vector_store.index.ntotal == 10
    assert len(vector_store.event_ids) == 10
    assert vector_store.bm25 is not None  # Verify BM25 is built

    # Verify storage update was called
    assert vector_store.storage.update_faiss_index.call_count == 10


def test_save_and_load_index(vector_store: EventVectorStore, sample_events: list[Event], temp_dir: Path) -> None:
    """Test saving and loading hybrid index from disk."""
    vector_store.build_index(sample_events)
    vector_store.save_index()

    assert (temp_dir / "index.faiss").exists()
    assert (temp_dir / "metadata.pkl").exists()

    # Create new instance and load
    with patch("src.models.vector_store.EventStorage"), patch("src.models.vector_store.CityLocator"):
        new_vs = EventVectorStore(index_path=str(temp_dir), embedder=vector_store.embedder)
        new_vs.load_index()

        assert new_vs.index is not None
        assert new_vs.index.ntotal == 10
        assert new_vs.bm25 is not None  # Verify BM25 is loaded
        assert new_vs.event_ids == vector_store.event_ids


def test_search(vector_store: EventVectorStore, sample_events: list[Event]) -> None:
    """Test semantic search."""
    vector_store.build_index(sample_events)

    # Mock storage.get_event to return the right event
    vector_store.storage.get_event.side_effect = lambda eid: next((e for e in sample_events if e.event_id == eid), None)

    results = vector_store.search("test query", k=3)

    assert len(results) == 3
    assert isinstance(results[0][0], Event)
    assert isinstance(results[0][1], float)


def test_search_with_filtering(vector_store: EventVectorStore, sample_events: list[Event]) -> None:
    """Test search with geospatial filtering."""
    vector_store.build_index(sample_events)
    vector_store.storage.get_event.side_effect = lambda eid: next((e for e in sample_events if e.event_id == eid), None)

    # Search for Paris (mocked geo-coordinates)
    results = vector_store.search("test query", k=10, metadata_filter={"city": "Paris"})

    # Results should be sorted: Paris events first (Exact match), then neighbors (Versailles)
    assert len(results) == 10
    for i in range(5):
        assert results[i][0].location.city == "Paris"

    # Next 5 should be Versailles (neighbors included via radius)
    for i in range(5, 10):
        assert results[i][0].location.city == "Versailles"


def test_search_performance_latency(vector_store: EventVectorStore, sample_events: list[Event]) -> None:
    """Basic performance test for search latency."""
    vector_store.build_index(sample_events)

    start_time = time.time()
    vector_store.search("fast query", k=5)
    duration = time.time() - start_time

    assert duration < 0.1
