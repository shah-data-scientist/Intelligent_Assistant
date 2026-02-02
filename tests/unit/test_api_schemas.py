"""
FILE: test_api_schemas.py
STATUS: Active
RESPONSIBILITY: Unit tests for API Pydantic schemas.
LAST MAJOR UPDATE: 2026-01-31
MAINTAINER: QA Team
"""

import pytest
from pydantic import ValidationError

from src.api.schemas import (
    ChatRequest,
    ChatResponse,
    FeedbackRequest,
    SourceDocument,
    StructuredEvent,
)


class TestChatRequest:
    """Test ChatRequest schema validation."""

    def test_valid_minimal_request(self):
        """Test ChatRequest with minimal required fields."""
        request = ChatRequest(question="What events are happening today?")
        assert request.question == "What events are happening today?"
        assert request.session_id == "default_session"
        assert request.language is None
        assert request.age is None

    def test_valid_full_request(self):
        """Test ChatRequest with all fields."""
        request = ChatRequest(
            question="Jazz concerts in Paris",
            session_id="user_123",
            language="fr",
            age=25,
        )
        assert request.question == "Jazz concerts in Paris"
        assert request.session_id == "user_123"
        assert request.language == "fr"
        assert request.age == 25

    def test_empty_question_fails(self):
        """Test that empty question fails validation."""
        with pytest.raises(ValidationError) as exc_info:
            ChatRequest(question="")
        # Pydantic v2 uses "string_too_short" error type
        assert "too_short" in str(exc_info.value).lower() or "at least 1" in str(exc_info.value).lower()

    def test_question_too_long_fails(self):
        """Test that question over 1000 chars fails validation."""
        with pytest.raises(ValidationError) as exc_info:
            ChatRequest(question="x" * 1001)
        # Pydantic v2 uses "string_too_long" error type
        assert "too_long" in str(exc_info.value).lower() or "at most 1000" in str(exc_info.value).lower()

    def test_question_at_max_length(self):
        """Test that question at exactly 1000 chars is valid."""
        request = ChatRequest(question="x" * 1000)
        assert len(request.question) == 1000


class TestSourceDocument:
    """Test SourceDocument schema."""

    def test_default_values(self):
        """Test SourceDocument default values."""
        doc = SourceDocument()
        assert doc.title is None
        assert doc.city is None
        assert doc.date is None
        assert doc.url is None
        assert doc.score == 0.0
        assert doc.latitude is None
        assert doc.longitude is None
        assert doc.event_id is None
        assert doc.category is None
        assert doc.match_type is None

    def test_full_document(self):
        """Test SourceDocument with all fields."""
        doc = SourceDocument(
            title="Jazz Festival",
            city="Paris",
            date="2026-02-15",
            url="https://example.com/event/123",
            score=0.95,
            latitude=48.8566,
            longitude=2.3522,
            event_id="evt_123",
            category="Musique",
            match_type="exact",
        )
        assert doc.title == "Jazz Festival"
        assert doc.city == "Paris"
        assert doc.score == 0.95


class TestStructuredEvent:
    """Test StructuredEvent schema."""

    def test_required_fields(self):
        """Test StructuredEvent with required fields only."""
        event = StructuredEvent(
            title="Concert Title",
            date="2026-02-15",
            city="Paris",
        )
        assert event.title == "Concert Title"
        assert event.date == "2026-02-15"
        assert event.city == "Paris"
        assert event.location == "Unknown"
        assert event.price_label == "Unknown"
        assert event.age_label == "Unknown"
        assert event.times == []
        assert event.times_display == "Unknown"

    def test_full_event(self):
        """Test StructuredEvent with all fields."""
        event = StructuredEvent(
            title="Concert Title",
            date="2026-02-15",
            city="Paris",
            location="Salle Pleyel",
            url="https://example.com/event",
            price_label="15€ - 45€",
            age_label="Tout public",
            times=["19:00", "21:00"],
            times_display="19:00, 21:00",
        )
        assert event.location == "Salle Pleyel"
        assert event.price_label == "15€ - 45€"
        assert len(event.times) == 2


class TestChatResponse:
    """Test ChatResponse schema."""

    def test_minimal_response(self):
        """Test ChatResponse with minimal fields."""
        response = ChatResponse(answer="Here are some events...")
        assert response.answer == "Here are some events..."
        assert response.sources == []
        assert response.structured_events == []
        assert response.message_id is None
        assert response.needs_clarification is False
        assert response.clarifying_questions == []

    def test_full_response(self):
        """Test ChatResponse with all fields."""
        response = ChatResponse(
            answer="Voici 3 événements...",
            sources=[SourceDocument(title="Event 1"), SourceDocument(title="Event 2")],
            structured_events=[
                StructuredEvent(title="Event 1", date="2026-02-15", city="Paris"),
            ],
            message_id=123,
            needs_clarification=False,
            clarifying_questions=[],
        )
        assert len(response.sources) == 2
        assert len(response.structured_events) == 1
        assert response.message_id == 123

    def test_clarification_response(self):
        """Test ChatResponse with clarification."""
        response = ChatResponse(
            answer="I need more information...",
            needs_clarification=True,
            clarifying_questions=["Which city?", "What date?"],
        )
        assert response.needs_clarification is True
        assert len(response.clarifying_questions) == 2


class TestFeedbackRequest:
    """Test FeedbackRequest schema."""

    def test_positive_feedback(self):
        """Test positive feedback."""
        feedback = FeedbackRequest(message_id=123, is_positive=True)
        assert feedback.message_id == 123
        assert feedback.is_positive is True
        assert feedback.comment is None

    def test_negative_feedback_with_comment(self):
        """Test negative feedback with comment."""
        feedback = FeedbackRequest(
            message_id=456,
            is_positive=False,
            comment="The event dates were wrong",
        )
        assert feedback.message_id == 456
        assert feedback.is_positive is False
        assert feedback.comment == "The event dates were wrong"

    def test_missing_required_fields(self):
        """Test that missing required fields fail validation."""
        with pytest.raises(ValidationError):
            FeedbackRequest(message_id=123)  # missing is_positive

        with pytest.raises(ValidationError):
            FeedbackRequest(is_positive=True)  # missing message_id


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
