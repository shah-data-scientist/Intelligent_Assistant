"""
FILE: test_unified_analyzer.py
STATUS: Active
RESPONSIBILITY: Unit tests for unified query analyzer classes and utilities.
LAST MAJOR UPDATE: 2026-01-31
MAINTAINER: QA Team
"""

import pytest
from datetime import date
from unittest.mock import MagicMock, patch

from src.retrieval.unified_analyzer import (
    QueryIntent,
    QueryDimension,
    UnifiedAnalysisResult,
    get_unified_analysis_prompt,
    is_rate_limit_error,
    map_category_to_db,
    validate_and_correct_weekend,
)


class TestQueryIntent:
    """Test QueryIntent enum."""

    def test_enum_values(self):
        """Test all enum values exist."""
        assert QueryIntent.EVENT_SEARCH.value == "event_search"
        assert QueryIntent.GREETING.value == "greeting"
        assert QueryIntent.CHITCHAT.value == "chitchat"
        assert QueryIntent.CAPABILITY.value == "capability"
        assert QueryIntent.DIRECTIONS.value == "directions"
        assert QueryIntent.ABUSE.value == "abuse"
        assert QueryIntent.OFF_TOPIC.value == "off_topic"

    def test_enum_from_value(self):
        """Test creating enum from value."""
        assert QueryIntent("event_search") == QueryIntent.EVENT_SEARCH
        assert QueryIntent("greeting") == QueryIntent.GREETING


class TestQueryDimension:
    """Test QueryDimension dataclass."""

    def test_basic_dimension(self):
        """Test creating basic dimension."""
        dim = QueryDimension(name="greeting", detected=True)
        assert dim.name == "greeting"
        assert dim.detected is True
        assert dim.value is None
        assert dim.original is None
        assert dim.action is None
        assert dim.confidence == 1.0

    def test_full_dimension(self):
        """Test creating dimension with all fields."""
        dim = QueryDimension(
            name="typo",
            detected=True,
            value="Paris",
            original="Pari",
            action="correct",
            confidence=0.95
        )
        assert dim.name == "typo"
        assert dim.detected is True
        assert dim.value == "Paris"
        assert dim.original == "Pari"
        assert dim.action == "correct"
        assert dim.confidence == 0.95

    def test_not_detected_dimension(self):
        """Test dimension that was not detected."""
        dim = QueryDimension(name="statistical", detected=False)
        assert dim.detected is False


class TestUnifiedAnalysisResult:
    """Test UnifiedAnalysisResult dataclass."""

    @pytest.fixture
    def basic_result(self):
        """Create a basic analysis result."""
        return UnifiedAnalysisResult(
            intent=QueryIntent.EVENT_SEARCH,
            intent_confidence=0.9,
        )

    @pytest.fixture
    def full_result(self):
        """Create a fully populated analysis result."""
        return UnifiedAnalysisResult(
            intent=QueryIntent.EVENT_SEARCH,
            intent_confidence=0.95,
            dimensions={
                "greeting": QueryDimension("greeting", True),
                "typo": QueryDimension("typo", True, value="Paris", original="Pari"),
                "statistical": QueryDimension("statistical", True),
                "scope": QueryDimension("scope", True, value="all"),
            },
            detected_language="fr",
            city="Paris",
            city_normalized="paris",
            event_type="concert",
            timeframe="ce weekend",
            is_complete=True,
            missing_criteria=[],
            filters={"city": "Paris", "category": "Musique"},
            refined_query="concerts à Paris ce weekend",
        )

    def test_basic_result(self, basic_result):
        """Test basic result creation."""
        assert basic_result.intent == QueryIntent.EVENT_SEARCH
        assert basic_result.intent_confidence == 0.9
        assert basic_result.detected_language == "fr"  # default
        assert basic_result.dimensions == {}

    def test_has_greeting_true(self, full_result):
        """Test has_greeting property when greeting detected."""
        assert full_result.has_greeting is True

    def test_has_greeting_false(self, basic_result):
        """Test has_greeting property when no greeting."""
        assert basic_result.has_greeting is False

    def test_has_typo_correction_true(self, full_result):
        """Test has_typo_correction when typo detected."""
        assert full_result.has_typo_correction is True

    def test_has_typo_correction_false(self, basic_result):
        """Test has_typo_correction when no typo."""
        assert basic_result.has_typo_correction is False

    def test_typo_correction_property(self, full_result):
        """Test typo_correction returns tuple."""
        correction = full_result.typo_correction
        assert correction == ("Pari", "Paris")

    def test_typo_correction_none(self, basic_result):
        """Test typo_correction returns None when no typo."""
        assert basic_result.typo_correction is None

    def test_is_statistical_true(self, full_result):
        """Test is_statistical when statistical query detected."""
        assert full_result.is_statistical is True

    def test_is_statistical_false(self, basic_result):
        """Test is_statistical when not a statistical query."""
        assert basic_result.is_statistical is False

    def test_wants_all_events_true(self, full_result):
        """Test wants_all_events when scope is 'all'."""
        assert full_result.wants_all_events is True

    def test_wants_all_events_false(self, basic_result):
        """Test wants_all_events when no scope dimension."""
        # Returns None when scope dimension doesn't exist (falsy)
        assert not basic_result.wants_all_events

    def test_default_values(self, basic_result):
        """Test default values are set correctly."""
        assert basic_result.city is None
        assert basic_result.city_normalized is None
        assert basic_result.event_type is None
        assert basic_result.timeframe is None
        assert basic_result.is_complete is False
        assert basic_result.missing_criteria == []
        assert basic_result.filters == {}
        assert basic_result.refined_query == ""
        assert basic_result.raw_response == {}


class TestGetUnifiedAnalysisPrompt:
    """Test prompt generation function."""

    def test_prompt_contains_date(self):
        """Test that prompt contains today's date."""
        today = date(2026, 3, 15)
        prompt = get_unified_analysis_prompt(today, ["Paris", "Lyon"])
        assert "2026" in prompt
        # Check month and day are included
        assert "March" in prompt or "mars" in prompt.lower() or "15" in prompt

    def test_prompt_contains_cities(self):
        """Test that prompt contains known cities."""
        today = date(2026, 3, 15)
        cities = ["Paris", "Lyon", "Versailles"]
        prompt = get_unified_analysis_prompt(today, cities)
        for city in cities:
            assert city in prompt

    def test_prompt_not_empty(self):
        """Test that prompt is not empty."""
        today = date(2026, 3, 15)
        prompt = get_unified_analysis_prompt(today, ["Paris"])
        assert len(prompt) > 100  # Should be substantial

    def test_prompt_mentions_dimensions(self):
        """Test that prompt mentions multi-dimensional output."""
        today = date(2026, 3, 15)
        prompt = get_unified_analysis_prompt(today, ["Paris"])
        # Should mention dimensions in some form
        assert "dimension" in prompt.lower() or "greeting" in prompt.lower()


class TestHelperFunctions:
    """Test standalone helper functions."""

    def test_is_rate_limit_error_with_429(self):
        """Test rate limit detection with 429 error."""
        error = Exception("HTTP 429: Too Many Requests")
        assert is_rate_limit_error(error) is True

    def test_is_rate_limit_error_with_quota(self):
        """Test rate limit detection with quota error."""
        error = Exception("Quota exceeded for this resource")
        assert is_rate_limit_error(error) is True

    def test_is_rate_limit_error_false(self):
        """Test that non-rate-limit errors return False."""
        error = Exception("Network connection failed")
        assert is_rate_limit_error(error) is False

    def test_map_category_none(self):
        """Test category mapping with None."""
        assert map_category_to_db(None) is None

    def test_map_category_empty(self):
        """Test category mapping with empty string."""
        assert map_category_to_db("") is None

    def test_map_category_known(self):
        """Test category mapping with known category."""
        assert map_category_to_db("jazz") == "Musique"
        assert map_category_to_db("theater") == "Théâtre / Spectacle"

    def test_validate_weekend_unchanged(self):
        """Test weekend validation returns unchanged for non-weekend query."""
        result = validate_and_correct_weekend([15, 16], 3, 2026, "regular date")
        assert result == [15, 16]


class TestResultIntegration:
    """Test UnifiedAnalysisResult with various dimension combinations."""

    def test_greeting_only(self):
        """Test result with greeting only."""
        result = UnifiedAnalysisResult(
            intent=QueryIntent.GREETING,
            intent_confidence=0.99,
            dimensions={
                "greeting": QueryDimension("greeting", True, value="Bonjour"),
            },
        )
        assert result.has_greeting is True
        assert result.is_statistical is False
        assert result.has_typo_correction is False

    def test_statistical_query(self):
        """Test result for statistical query."""
        result = UnifiedAnalysisResult(
            intent=QueryIntent.EVENT_SEARCH,
            intent_confidence=0.95,
            dimensions={
                "statistical": QueryDimension("statistical", True, action="count"),
            },
            city="Paris",
            is_complete=True,
        )
        assert result.is_statistical is True
        assert result.city == "Paris"

    def test_off_topic_query(self):
        """Test result for off-topic query."""
        result = UnifiedAnalysisResult(
            intent=QueryIntent.OFF_TOPIC,
            intent_confidence=0.99,
        )
        assert result.intent == QueryIntent.OFF_TOPIC
        assert result.is_complete is False

    def test_abuse_query(self):
        """Test result for abuse detection."""
        result = UnifiedAnalysisResult(
            intent=QueryIntent.ABUSE,
            intent_confidence=0.99,
        )
        assert result.intent == QueryIntent.ABUSE


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
