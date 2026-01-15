"""Tests for EventVectorStore and semantic search."""

import shutil
import tempfile
import time
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from src.data.models import Event
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
    embedder.embed_events.side_effect = lambda events: [
        np.random.rand(1024).tolist() for _ in events
    ]
    embedder.embed_query.return_value = np.random.rand(1024).tolist()
    return embedder


@pytest.fixture
def sample_events() -> list[Event]:
    """Create sample events for indexing."""
    return [
        Event(
            event_id=f"test-{i}",
            title=f"Event {i}",
            description=f"Description for event {i}",
            category="Music" if i % 2 == 0 else "Art",
        )
        for i in range(10)
    ]


@pytest.fixture
def vector_store(temp_dir: Path, mock_embedder: MagicMock) -> EventVectorStore:
    """Create EventVectorStore instance for testing."""
    # Use in-memory SQLite for tests
    with patch("src.models.vector_store.EventStorage") as mock_storage_class:
        mock_storage = MagicMock()
        mock_storage_class.return_value = mock_storage
        
        vs = EventVectorStore(
            index_path=str(temp_dir),
            embedder=mock_embedder,
        )
        # Manually set storage to the mock
        vs.storage = mock_storage
        yield vs
        vs.close()


def test_build_index(vector_store: EventVectorStore, sample_events: list[Event]) -> None:
    """Test building FAISS index."""
    stats = vector_store.build_index(sample_events)
    
    assert stats["events_indexed"] == 10
    assert vector_store.index is not None
    assert vector_store.index.ntotal == 10
    assert len(vector_store.event_ids) == 10
    
    # Verify storage update was called
    assert vector_store.storage.update_faiss_index.call_count == 10


def test_save_and_load_index(vector_store: EventVectorStore, sample_events: list[Event], temp_dir: Path) -> None:
    """Test saving and loading index from disk."""
    vector_store.build_index(sample_events)
    vector_store.save_index()
    
    assert (temp_dir / "index.faiss").exists()
    assert (temp_dir / "metadata.pkl").exists()
    
    # Create new instance and load
    with patch("src.models.vector_store.EventStorage"):
        new_vs = EventVectorStore(index_path=str(temp_dir), embedder=vector_store.embedder)
        new_vs.load_index()
        
        assert new_vs.index is not None
        assert new_vs.index.ntotal == 10
        assert new_vs.event_ids == vector_store.event_ids


def test_search(vector_store: EventVectorStore, sample_events: list[Event]) -> None:
    """Test semantic search."""
    vector_store.build_index(sample_events)
    
    # Mock storage.get_event to return the right event
    vector_store.storage.get_event.side_effect = lambda eid: next(
        (e for e in sample_events if e.event_id == eid), None
    )
    
    results = vector_store.search("test query", k=3)
    
    assert len(results) == 3
    assert isinstance(results[0][0], Event)
    assert isinstance(results[0][1], float)
    # Cosine similarity with normalized vectors should be <= 1.0
    assert results[0][1] <= 1.000001 


def test_search_with_filtering(vector_store: EventVectorStore, sample_events: list[Event]) -> None:
    """Test search with metadata filtering."""
    # Ensure some events have specific cities
    for i, event in enumerate(sample_events):
        from src.data.models import EventLocation
        event.location = EventLocation(city="Paris" if i < 5 else "Versailles")
    
    vector_store.build_index(sample_events)
    vector_store.storage.get_event.side_effect = lambda eid: next(
        (e for e in sample_events if e.event_id == eid), None
    )
    
    # Search for Paris only
    results = vector_store.search("test query", k=10, metadata_filter={"city": "Paris"})
    
    assert len(results) == 5
    for event, _ in results:
        assert event.location.city == "Paris"


def test_search_performance_latency(vector_store: EventVectorStore, sample_events: list[Event]) -> None:
    """Basic performance test for search latency."""
    vector_store.build_index(sample_events)
    
    start_time = time.time()
    vector_store.search("fast query", k=5)
    duration = time.time() - start_time
    
    # Search on small index with mocked embeddings should be very fast (< 100ms)
    assert duration < 0.1


def test_build_index_performance(vector_store: EventVectorStore) -> None:
    """Test index building performance with more events."""
    large_sample = [
        Event(event_id=f"test-{i}", title=f"Event {i}")
        for i in range(100)
    ]
    
    start_time = time.time()
    vector_store.build_index(large_sample)
    duration = time.time() - start_time
    
    # Building index for 100 events (mocked) should be fast (< 500ms)
    assert duration < 0.5
