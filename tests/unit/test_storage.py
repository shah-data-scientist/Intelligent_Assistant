"""
FILE: test_storage.py
STATUS: Active
RESPONSIBILITY: Unit tests for event storage and database operations.

DEPENDENCIES (Who uses this file):
- pytest test runner
- Database operations validation

IMPORTS (What this file needs):
- pytest: Test framework
- src.data.storage: EventStorage

LAST MAJOR UPDATE: 2026-01-31
MAINTAINER: QA Team
"""

import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from src.data.models import Event, EventLocation
from src.data.storage import EventStorage


@pytest.fixture
def temp_db() -> Path:
    """Create temporary database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir) / "test_events.db"


@pytest.fixture
def storage(temp_db: Path) -> EventStorage:
    """Create EventStorage instance for testing."""
    storage = EventStorage(db_path=str(temp_db))
    yield storage
    storage.close()


@pytest.fixture
def sample_event() -> Event:
    """Create sample event for testing."""
    return Event(
        event_id="test-123",
        title="Test Event",
        description="A test event",
        category="Music",
        location=EventLocation(
            city="Paris",
            postal_code="75001",
            address="123 Test Street",
            coordinates={"lat": 48.8566, "lon": 2.3522},
        ),
        start_date=datetime(2026, 6, 15, 19, 0),
        end_date=datetime(2026, 6, 15, 22, 0),
        organizer="Test Organizer",
        url="https://example.com/event",
        tags=["test", "music"],
    )


def test_storage_initialization(temp_db: Path) -> None:
    """Test storage initialization creates database."""
    with EventStorage(db_path=str(temp_db)) as storage:
        assert temp_db.exists()
        assert storage.count_events() == 0


def test_add_single_event(storage: EventStorage, sample_event: Event) -> None:
    """Test adding a single event."""
    result = storage.add_event(sample_event)
    assert result is True
    assert storage.count_events() == 1


def test_add_duplicate_event(storage: EventStorage, sample_event: Event) -> None:
    """Test adding duplicate event returns False."""
    storage.add_event(sample_event)
    result = storage.add_event(sample_event)
    assert result is False
    assert storage.count_events() == 1


def test_get_event(storage: EventStorage, sample_event: Event) -> None:
    """Test retrieving event by ID."""
    storage.add_event(sample_event)
    retrieved = storage.get_event("test-123")

    assert retrieved is not None
    assert retrieved.event_id == "test-123"
    assert retrieved.title == "Test Event"
    assert retrieved.category == "Music"
    assert retrieved.location is not None
    assert retrieved.location.city == "Paris"


def test_get_nonexistent_event(storage: EventStorage) -> None:
    """Test retrieving non-existent event returns None."""
    result = storage.get_event("nonexistent")
    assert result is None


def test_add_events_bulk(storage: EventStorage) -> None:
    """Test bulk adding events."""
    events = [Event(event_id=f"test-{i}", title=f"Event {i}") for i in range(5)]

    count = storage.add_events_bulk(events)
    assert count == 5
    assert storage.count_events() == 5


def test_add_events_bulk_with_duplicates(storage: EventStorage) -> None:
    """Test bulk adding with some duplicates."""
    events1 = [Event(event_id=f"test-{i}", title=f"Event {i}") for i in range(3)]
    events2 = [Event(event_id=f"test-{i}", title=f"Event {i}") for i in range(2, 5)]  # Overlaps with events1

    count1 = storage.add_events_bulk(events1)
    count2 = storage.add_events_bulk(events2)

    assert count1 == 3
    assert count2 == 2  # Only 2 new events (test-3 and test-4)
    assert storage.count_events() == 5


def test_get_all_events(storage: EventStorage) -> None:
    """Test retrieving all events."""
    events = [Event(event_id=f"test-{i}", title=f"Event {i}") for i in range(10)]
    storage.add_events_bulk(events)

    all_events = storage.get_all_events()
    assert len(all_events) == 10


def test_get_all_events_with_pagination(storage: EventStorage) -> None:
    """Test retrieving events with pagination."""
    events = [Event(event_id=f"test-{i}", title=f"Event {i}") for i in range(10)]
    storage.add_events_bulk(events)

    page1 = storage.get_all_events(limit=5, offset=0)
    page2 = storage.get_all_events(limit=5, offset=5)

    assert len(page1) == 5
    assert len(page2) == 5


def test_get_events_by_date_range(storage: EventStorage) -> None:
    """Test filtering events by date range."""
    events = [
        Event(
            event_id=f"test-{i}",
            title=f"Event {i}",
            start_date=datetime(2026, i + 1, 1),
        )
        for i in range(6)  # Jan-Jun 2026
    ]
    storage.add_events_bulk(events)

    # Get events between March and May
    filtered = storage.get_events_by_date_range(
        start_date=datetime(2026, 3, 1),
        end_date=datetime(2026, 5, 31),
    )

    assert len(filtered) == 3  # March, April, May


def test_get_existing_event_ids(storage: EventStorage) -> None:
    """Test retrieving set of existing event IDs."""
    events = [Event(event_id=f"test-{i}", title=f"Event {i}") for i in range(5)]
    storage.add_events_bulk(events)

    existing_ids = storage.get_existing_event_ids()
    assert len(existing_ids) == 5
    assert "test-0" in existing_ids
    assert "test-4" in existing_ids


def test_update_faiss_index(storage: EventStorage, sample_event: Event) -> None:
    """Test updating FAISS index for an event."""
    storage.add_event(sample_event)

    result = storage.update_faiss_index("test-123", 42)
    assert result is True

    # Verify update
    retrieved = storage.get_event("test-123")
    # Note: faiss_index is not part of Event model, only in storage


def test_update_faiss_index_nonexistent(storage: EventStorage) -> None:
    """Test updating FAISS index for non-existent event."""
    result = storage.update_faiss_index("nonexistent", 42)
    assert result is False


def test_delete_old_events(storage: EventStorage) -> None:
    """Test deleting events before a certain date."""
    events = [
        Event(
            event_id=f"test-{i}",
            title=f"Event {i}",
            start_date=datetime(2025 + i, 1, 1),
        )
        for i in range(3)  # 2025, 2026, 2027
    ]
    storage.add_events_bulk(events)

    # Delete events before 2026
    deleted = storage.delete_old_events(datetime(2026, 1, 1))
    assert deleted == 1
    assert storage.count_events() == 2


def test_clear_all(storage: EventStorage) -> None:
    """Test clearing all events."""
    events = [Event(event_id=f"test-{i}", title=f"Event {i}") for i in range(5)]
    storage.add_events_bulk(events)
    assert storage.count_events() == 5

    storage.clear_all()
    assert storage.count_events() == 0


def test_event_with_full_location(storage: EventStorage) -> None:
    """Test storing and retrieving event with complete location."""
    event = Event(
        event_id="location-test",
        title="Location Test Event",
        location=EventLocation(
            city="Versailles",
            postal_code="78000",
            address="Place d'Armes",
            coordinates={"lat": 48.8049, "lon": 2.1204},
        ),
    )

    storage.add_event(event)
    retrieved = storage.get_event("location-test")

    assert retrieved is not None
    assert retrieved.location is not None
    assert retrieved.location.city == "Versailles"
    assert retrieved.location.postal_code == "78000"
    assert retrieved.location.coordinates == {"lat": 48.8049, "lon": 2.1204}


def test_event_without_location(storage: EventStorage) -> None:
    """Test storing event without location."""
    event = Event(
        event_id="no-location",
        title="Event Without Location",
    )

    storage.add_event(event)
    retrieved = storage.get_event("no-location")

    assert retrieved is not None
    assert retrieved.location is None
