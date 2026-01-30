"""
FILE: test_data_models.py
STATUS: Active
RESPONSIBILITY: Unit tests for Pydantic data models (Event, SearchIntent, SearchFilters).

DEPENDENCIES (Who uses this file):
- pytest test runner
- Data model validation

IMPORTS (What this file needs):
- pytest: Test framework
- pydantic: Model validation, src.data.models: Data models

LAST MAJOR UPDATE: 2026-01-31
MAINTAINER: QA Team
"""

from datetime import datetime


from src.data.models import Event, EventLocation


def test_event_location_creation() -> None:
    """Test EventLocation model creation."""
    location = EventLocation(
        address="123 Rue de Rivoli",
        city="Paris",
        postal_code="75001",
        coordinates={"lat": 48.8566, "lon": 2.3522},
    )

    assert location.address == "123 Rue de Rivoli"
    assert location.city == "Paris"
    assert location.postal_code == "75001"
    assert location.coordinates == {"lat": 48.8566, "lon": 2.3522}


def test_event_creation_minimal() -> None:
    """Test Event model with minimal required fields."""
    event = Event(
        event_id="test-123",
        title="Test Event",
    )

    assert event.event_id == "test-123"
    assert event.title == "Test Event"
    assert event.description is None
    assert event.tags == []


def test_event_creation_full() -> None:
    """Test Event model with all fields."""
    location = EventLocation(city="Paris", postal_code="75001")
    start_date = datetime(2026, 2, 15, 18, 0)
    end_date = datetime(2026, 2, 15, 22, 0)

    event = Event(
        event_id="test-456",
        title="Concert de Jazz",
        description="Un concert exceptionnel",
        category="Music",
        location=location,
        start_date=start_date,
        end_date=end_date,
        organizer="Jazz Club Paris",
        url="https://example.com/event",
        image_url="https://example.com/image.jpg",
        tags=["jazz", "music", "concert"],
    )

    assert event.event_id == "test-456"
    assert event.title == "Concert de Jazz"
    assert event.category == "Music"
    assert event.location.city == "Paris"
    assert event.start_date == start_date
    assert len(event.tags) == 3


def test_event_to_text() -> None:
    """Test Event to_text method."""
    location = EventLocation(
        address="10 Boulevard de la Chapelle",
        city="Paris",
    )
    start_date = datetime(2026, 3, 20, 19, 0)

    event = Event(
        event_id="test-789",
        title="Exposition d'Art",
        description="Une exposition fascinante",
        category="Art",
        location=location,
        start_date=start_date,
        organizer="Musée d'Art Moderne",
        tags=["art", "exposition"],
    )

    text = event.to_text()

    assert "Titre: Exposition d'Art" in text
    assert "Description: Une exposition fascinante" in text
    assert "Catégorie: Art" in text
    assert "Ville: Paris" in text
    assert "20/03/2026 19:00" in text
    assert "Organisateur: Musée d'Art Moderne" in text
    assert "art, exposition" in text


def test_event_get_metadata() -> None:
    """Test Event get_metadata method."""
    start_date = datetime(2026, 4, 10, 14, 30)

    event = Event(
        event_id="test-999",
        title="Workshop Photographie",
        category="Photography",
        location=EventLocation(city="Paris"),
        start_date=start_date,
        url="https://example.com/workshop",
    )

    metadata = event.get_metadata()

    assert metadata["event_id"] == "test-999"
    assert metadata["title"] == "Workshop Photographie"
    assert metadata["category"] == "Photography"
    assert metadata["city"] == "Paris"
    assert metadata["year"] == 2026
    assert metadata["month"] == 4
    assert metadata["url"] == "https://example.com/workshop"
    assert "start_date" in metadata


def test_event_metadata_with_missing_fields() -> None:
    """Test Event get_metadata with missing optional fields."""
    event = Event(
        event_id="test-111",
        title="Minimal Event",
    )

    metadata = event.get_metadata()

    assert metadata["event_id"] == "test-111"
    assert metadata["title"] == "Minimal Event"
    assert metadata["category"] == "unknown"
    assert "city" not in metadata
    assert "year" not in metadata
