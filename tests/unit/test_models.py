"""
FILE: test_models.py
STATUS: Active
RESPONSIBILITY: Unit tests for data models.
LAST MAJOR UPDATE: 2026-01-31
MAINTAINER: QA Team
"""

import pytest
from datetime import datetime

from src.data.models import Event, EventLocation


class TestEventLocation:
    """Test EventLocation model."""

    def test_empty_location(self):
        """Test creating empty location."""
        loc = EventLocation()
        assert loc.address is None
        assert loc.city is None
        assert loc.postal_code is None
        assert loc.coordinates is None

    def test_full_location(self):
        """Test creating location with all fields."""
        loc = EventLocation(
            address="15 rue de la Paix",
            city="Paris",
            postal_code="75001",
            coordinates={"lat": 48.8566, "lon": 2.3522}
        )
        assert loc.address == "15 rue de la Paix"
        assert loc.city == "Paris"
        assert loc.postal_code == "75001"
        assert loc.coordinates == {"lat": 48.8566, "lon": 2.3522}


class TestEvent:
    """Test Event model."""

    @pytest.fixture
    def basic_event(self):
        """Create a basic event fixture."""
        return Event(
            event_id="evt-001",
            title="Jazz Concert",
        )

    @pytest.fixture
    def full_event(self):
        """Create a fully populated event fixture."""
        return Event(
            event_id="evt-002",
            title="Festival de Musique",
            description="Un grand festival de musique à Paris.",
            category="Concert",
            location=EventLocation(
                address="1 Place de la Concorde",
                city="Paris",
                postal_code="75008",
            ),
            start_date=datetime(2025, 6, 15, 19, 0),
            end_date=datetime(2025, 6, 15, 23, 0),
            organizer="Association Musicale",
            url="https://example.com/festival",
            image_url="https://example.com/image.jpg",
            tags=["musique", "festival", "été"],
            scraped_content="Contenu enrichi de la page web.",
            timings=["19:00", "21:00"],
            periods=["soir"],
            is_full_day=False,
            has_evening=True,
            conditions="Gratuit",
            accessibility="Accessible PMR",
        )

    def test_basic_event_creation(self, basic_event):
        """Test creating a basic event."""
        assert basic_event.event_id == "evt-001"
        assert basic_event.title == "Jazz Concert"
        assert basic_event.description is None
        assert basic_event.tags == []

    def test_to_text_basic(self, basic_event):
        """Test to_text with minimal data."""
        text = basic_event.to_text()
        assert "Titre: Jazz Concert" in text

    def test_to_text_with_url(self, full_event):
        """Test to_text includes URL."""
        text = full_event.to_text()
        assert "https://example.com/festival" in text

    def test_to_text_with_metadata_prefix(self, full_event):
        """Test to_text includes metadata prefix."""
        text = full_event.to_text(include_metadata_prefix=True)
        assert "[Ville: Paris]" in text
        assert "[Catégorie: Concert]" in text

    def test_to_text_without_metadata_prefix(self, full_event):
        """Test to_text without metadata prefix."""
        text = full_event.to_text(include_metadata_prefix=False)
        # Should still have title but not bracketed metadata
        assert "Titre: Festival de Musique" in text

    def test_to_text_with_dates(self, full_event):
        """Test to_text includes date information."""
        text = full_event.to_text()
        assert "Date de début:" in text
        assert "15/06/2025" in text
        assert "Date de fin:" in text

    def test_to_text_with_location(self, full_event):
        """Test to_text includes location information."""
        text = full_event.to_text()
        assert "Ville: Paris" in text
        assert "Adresse: 1 Place de la Concorde" in text
        assert "Code postal: 75008" in text

    def test_to_text_with_timings(self, full_event):
        """Test to_text includes timing information."""
        text = full_event.to_text()
        assert "Horaires: 19:00, 21:00" in text
        assert "Créneaux: soir" in text

    def test_to_text_with_full_day_event(self):
        """Test to_text with full day event."""
        event = Event(
            event_id="evt-003",
            title="Journée Portes Ouvertes",
            is_full_day=True,
        )
        text = event.to_text()
        assert "toute la journée" in text

    def test_to_text_with_description(self, full_event):
        """Test to_text includes description."""
        text = full_event.to_text()
        assert "Description:" in text
        assert "Un grand festival" in text

    def test_to_text_with_scraped_content(self, full_event):
        """Test to_text includes scraped content."""
        text = full_event.to_text()
        assert "Description complète:" in text
        assert "Contenu enrichi" in text

    def test_to_text_with_tags(self, full_event):
        """Test to_text includes tags."""
        text = full_event.to_text()
        assert "Mots-clés:" in text
        assert "musique" in text

    def test_to_text_with_organizer(self, full_event):
        """Test to_text includes organizer."""
        text = full_event.to_text()
        assert "Organisateur: Association Musicale" in text

    def test_to_text_with_conditions(self, full_event):
        """Test to_text includes conditions."""
        text = full_event.to_text()
        assert "Conditions et Tarifs: Gratuit" in text

    def test_to_text_with_accessibility(self, full_event):
        """Test to_text includes accessibility."""
        text = full_event.to_text()
        assert "Accessibilité: Accessible PMR" in text

    def test_to_chunks_short_event(self, basic_event):
        """Test to_chunks with short event returns single chunk."""
        chunks = basic_event.to_chunks()
        assert len(chunks) == 1
        assert "Jazz Concert" in chunks[0]

    def test_to_chunks_long_event(self):
        """Test to_chunks with long event creates multiple chunks."""
        # Create event with very long description
        long_description = " ".join(["This is a long sentence about the event."] * 100)
        event = Event(
            event_id="evt-004",
            title="Long Event",
            description=long_description,
            category="Festival",
            location=EventLocation(city="Paris"),
        )
        chunks = event.to_chunks(max_tokens=200)

        # Should have multiple chunks
        assert len(chunks) > 1
        # Each chunk should have the title (metadata header)
        for chunk in chunks:
            assert "Long Event" in chunk

    def test_get_metadata_basic(self, basic_event):
        """Test get_metadata with basic event."""
        metadata = basic_event.get_metadata()

        assert metadata["event_id"] == "evt-001"
        assert metadata["title"] == "Jazz Concert"
        assert metadata["category"] == "unknown"  # Default when None

    def test_get_metadata_full(self, full_event):
        """Test get_metadata with full event."""
        metadata = full_event.get_metadata()

        assert metadata["event_id"] == "evt-002"
        assert metadata["title"] == "Festival de Musique"
        assert metadata["category"] == "Concert"
        assert metadata["city"] == "Paris"
        assert metadata["url"] == "https://example.com/festival"
        assert metadata["start_date"] == "2025-06-15T19:00:00"
        assert metadata["year"] == 2025
        assert metadata["month"] == 6

    def test_get_metadata_with_conditions(self, full_event):
        """Test get_metadata includes conditions."""
        metadata = full_event.get_metadata()
        assert metadata["conditions"] == "Gratuit"

    def test_get_metadata_with_age_limits(self):
        """Test get_metadata with age limits."""
        event = Event(
            event_id="evt-005",
            title="Kids Event",
            age_min=5,
            age_max=12,
        )
        metadata = event.get_metadata()

        assert metadata["age_min"] == 5
        assert metadata["age_max"] == 12

    def test_get_metadata_with_timings(self, full_event):
        """Test get_metadata includes timings."""
        metadata = full_event.get_metadata()

        assert metadata["timings"] == ["19:00", "21:00"]
        assert metadata["periods"] == ["soir"]

    def test_get_metadata_with_full_day(self):
        """Test get_metadata with full day event."""
        event = Event(
            event_id="evt-006",
            title="Full Day Event",
            is_full_day=True,
        )
        metadata = event.get_metadata()
        assert metadata["is_full_day"] is True

    def test_get_metadata_with_location_details(self, full_event):
        """Test get_metadata includes location details."""
        metadata = full_event.get_metadata()

        assert metadata["address"] == "1 Place de la Concorde"
        assert metadata["postal_code"] == "75008"

    def test_default_labels(self, basic_event):
        """Test default price and age labels."""
        assert basic_event.price_label == "Non spécifié"
        assert basic_event.age_label == "Tout public"

    def test_period_flags(self):
        """Test period flags for time-based filtering."""
        event = Event(
            event_id="evt-007",
            title="Morning Event",
            has_morning=True,
            has_afternoon=False,
            has_evening=False,
        )
        assert event.has_morning is True
        assert event.has_afternoon is False
        assert event.has_evening is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
