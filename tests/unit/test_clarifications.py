"""
FILE: test_clarifications.py
STATUS: Active
RESPONSIBILITY: Unit tests for clarification question generation.

DEPENDENCIES (Who uses this file):
- pytest test runner
- Clarification logic validation

IMPORTS (What this file needs):
- pytest: Test framework
- src.retrieval.clarifications: Clarification templates

LAST MAJOR UPDATE: 2026-02-02
MAINTAINER: QA Team
"""

import pytest
from src.retrieval.clarifications import get_clarification_response


class TestGetClarificationResponse:
    """Test get_clarification_response function."""

    def test_single_missing_city(self):
        """Test clarification for missing city only."""
        prefix, questions = get_clarification_response("missing_city", "fr")

        assert prefix is not None
        assert questions is not None
        assert len(questions) >= 1
        # Should ask about city/location
        combined_text = (prefix + " ".join(questions)).lower()
        assert "ville" in combined_text or "zone" in combined_text or "région" in combined_text

    def test_single_missing_event_type(self):
        """Test clarification for missing event type only."""
        prefix, questions = get_clarification_response("missing_event_type", "fr")

        assert prefix is not None
        assert questions is not None
        assert len(questions) >= 1
        # Should ask about event type
        combined_text = (prefix + " ".join(questions)).lower()
        assert "type" in combined_text or "événement" in combined_text or "musique" in combined_text

    def test_single_missing_date(self):
        """Test clarification for missing date only."""
        prefix, questions = get_clarification_response("missing_date", "fr")

        assert prefix is not None
        assert questions is not None
        assert len(questions) >= 1
        # Should ask about date/time
        combined_text = (prefix + " ".join(questions)).lower()
        assert (
            "période" in combined_text
            or "quand" in combined_text
            or "date" in combined_text
            or "week-end" in combined_text
        )

    def test_unknown_reason_returns_none(self):
        """Test that unknown reason returns (None, None)."""
        prefix, questions = get_clarification_response("unknown_reason_xyz", "fr")

        assert prefix is None
        assert questions is None

    def test_english_language(self):
        """Test clarification in English."""
        prefix, questions = get_clarification_response("missing_city", "en")

        # Should return valid response (may be None if not defined in en.json)
        if prefix is not None:
            assert questions is not None
            combined_text = (prefix + " ".join(questions)).lower()
            # Should NOT contain French-only words
            assert "quelle" not in combined_text

    def test_language_fallback(self):
        """Test that invalid language handles gracefully."""
        prefix, questions = get_clarification_response("missing_city", "es")

        # Should either return None or fallback to default language
        # The behavior depends on i18n implementation


class TestClarificationResponseContent:
    """Test that clarification responses have valid content."""

    def test_missing_city_has_questions(self):
        """Test missing_city has meaningful questions."""
        prefix, questions = get_clarification_response("missing_city", "fr")

        if prefix is not None:
            assert len(prefix) > 10, "Prefix should be meaningful text"
            assert all(len(q) > 5 for q in questions), "Questions should be meaningful"

    def test_missing_event_type_has_questions(self):
        """Test missing_event_type has meaningful questions."""
        prefix, questions = get_clarification_response("missing_event_type", "fr")

        if prefix is not None:
            assert len(prefix) > 10, "Prefix should be meaningful text"
            assert all(len(q) > 5 for q in questions), "Questions should be meaningful"

    def test_missing_date_has_questions(self):
        """Test missing_date has meaningful questions."""
        prefix, questions = get_clarification_response("missing_date", "fr")

        if prefix is not None:
            assert len(prefix) > 10, "Prefix should be meaningful text"
            assert all(len(q) > 5 for q in questions), "Questions should be meaningful"


class TestClarificationLanguageConsistency:
    """Test language consistency in clarification responses."""

    def test_french_response_is_french(self):
        """Test that French responses contain French content."""
        prefix, questions = get_clarification_response("missing_city", "fr")

        if prefix is not None:
            combined = (prefix + " ".join(questions)).lower()
            # French indicators
            french_words = ["vous", "cherchez", "ville", "événements", "région", "souhaitez"]
            has_french = any(word in combined for word in french_words)
            assert has_french, "French response should contain French words"

    def test_english_response_is_english(self):
        """Test that English responses contain English content."""
        prefix, questions = get_clarification_response("missing_city", "en")

        if prefix is not None:
            combined = (prefix + " ".join(questions)).lower()
            # Should not have French-only grammar
            assert "vous" not in combined or "cherchez" not in combined


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
