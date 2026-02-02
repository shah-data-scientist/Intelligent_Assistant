"""
FILE: test_unified_analyzer_integration.py
STATUS: Active
RESPONSIBILITY: Integration tests for unified query analyzer.
LAST MAJOR UPDATE: 2026-01-31
MAINTAINER: QA Team
"""

import pytest
from datetime import date

from src.retrieval.unified_analyzer import (
    is_rate_limit_error,
    map_category_to_db,
    validate_and_correct_weekend,
    CATEGORY_MAPPING,
)


class TestIsRateLimitError:
    """Test rate limit error detection."""

    def test_detect_429_error(self):
        """Test detection of 429 status code."""
        error = Exception("HTTP 429 Too Many Requests")
        assert is_rate_limit_error(error) is True

    def test_detect_resource_exhausted(self):
        """Test detection of resource_exhausted error."""
        error = Exception("RESOURCE_EXHAUSTED: Quota exceeded")
        assert is_rate_limit_error(error) is True

    def test_detect_rate_limit_text(self):
        """Test detection of rate limit text."""
        error = Exception("Rate limit exceeded, please try again later")
        assert is_rate_limit_error(error) is True

    def test_detect_too_many_requests(self):
        """Test detection of too many requests error."""
        error = Exception("too many requests to the API")
        assert is_rate_limit_error(error) is True

    def test_detect_quota_error(self):
        """Test detection of quota error."""
        error = Exception("API quota has been exceeded")
        assert is_rate_limit_error(error) is True

    def test_not_rate_limit_error(self):
        """Test that other errors are not detected as rate limit."""
        error = Exception("Connection timeout")
        assert is_rate_limit_error(error) is False

        error = Exception("Invalid API key")
        assert is_rate_limit_error(error) is False


class TestMapCategoryToDb:
    """Test category mapping function."""

    def test_exact_match_concert(self):
        """Test exact match for 'concert'."""
        result = map_category_to_db("concert")
        assert result == "Musique"

    def test_exact_match_concerts(self):
        """Test exact match for 'concerts' (plural)."""
        result = map_category_to_db("concerts")
        assert result == "Musique"

    def test_exact_match_jazz(self):
        """Test exact match for 'jazz'."""
        result = map_category_to_db("jazz")
        assert result == "Musique"

    def test_exact_match_theatre(self):
        """Test exact match for theatre variants."""
        assert map_category_to_db("theater") == "Théâtre / Spectacle"
        assert map_category_to_db("theatre") == "Théâtre / Spectacle"
        assert map_category_to_db("théâtre") == "Théâtre / Spectacle"

    def test_case_insensitive(self):
        """Test that mapping is case insensitive."""
        assert map_category_to_db("CONCERT") == "Musique"
        assert map_category_to_db("Jazz") == "Musique"
        assert map_category_to_db("THEATER") == "Théâtre / Spectacle"

    def test_word_in_phrase_match(self):
        """Test matching word within a phrase."""
        # "concerts de jazz" contains "concert" and "jazz"
        result = map_category_to_db("concerts de jazz")
        assert result == "Musique"

    def test_none_input(self):
        """Test None input returns None."""
        result = map_category_to_db(None)
        assert result is None

    def test_empty_input(self):
        """Test empty string returns None."""
        result = map_category_to_db("")
        assert result is None

    def test_unknown_category_returned_as_is(self):
        """Test unknown category is returned as-is."""
        result = map_category_to_db("Unknown Category Type")
        assert result == "Unknown Category Type"

    def test_category_mapping_has_entries(self):
        """Test that category mapping dictionary is populated."""
        assert len(CATEGORY_MAPPING) > 10
        assert "concert" in CATEGORY_MAPPING
        assert "jazz" in CATEGORY_MAPPING


class TestValidateAndCorrectWeekend:
    """Test weekend validation and correction."""

    def test_not_weekend_query_returns_unchanged(self):
        """Test that non-weekend queries return unchanged."""
        result = validate_and_correct_weekend([15, 16], 3, 2026, "March 15-16")
        assert result == [15, 16]

    def test_first_weekend_correction(self):
        """Test first weekend calculation."""
        # First weekend of March 2026
        # March 2026: 1st is Sunday, so first weekend is Sat 7, Sun 8
        result = validate_and_correct_weekend([1, 2], 3, 2026, "first weekend of March")
        assert result == [7, 8]

    def test_second_weekend_correction(self):
        """Test second weekend calculation."""
        # Second weekend of March 2026: Sat 14, Sun 15
        result = validate_and_correct_weekend([7, 8], 3, 2026, "second weekend of March")
        assert result == [14, 15]

    def test_last_weekend(self):
        """Test last weekend calculation."""
        # Last weekend of March 2026: Sat 28, Sun 29
        result = validate_and_correct_weekend([21, 22], 3, 2026, "last weekend of March")
        assert result == [28, 29]

    def test_correct_value_unchanged(self):
        """Test that correct values are not changed."""
        # First weekend of March 2026 is [7, 8]
        result = validate_and_correct_weekend([7, 8], 3, 2026, "first weekend of March")
        assert result == [7, 8]

    def test_ordinal_variations(self):
        """Test different ordinal formats."""
        # All these should be first weekend
        assert validate_and_correct_weekend([1], 3, 2026, "1st weekend") == [7, 8]

        # 2nd weekend
        assert validate_and_correct_weekend([1], 3, 2026, "2nd weekend of march") == [14, 15]

    def test_none_inputs(self):
        """Test handling of None inputs."""
        assert validate_and_correct_weekend([15, 16], None, 2026, "first weekend") == [15, 16]
        assert validate_and_correct_weekend([15, 16], 3, None, "first weekend") == [15, 16]
        assert validate_and_correct_weekend([15, 16], 3, 2026, None) == [15, 16]
        assert validate_and_correct_weekend([15, 16], 3, 2026, "") == [15, 16]

    def test_single_day_correction(self):
        """Test correction of single day value."""
        # If LLM returns single day not in weekend, correct to weekend pair
        result = validate_and_correct_weekend(1, 3, 2026, "first weekend of March")
        assert result == [7, 8]


class TestCategoryMappingCompleteness:
    """Test category mapping coverage."""

    def test_music_categories(self):
        """Test music-related categories are mapped."""
        music_terms = ["concert", "concerts", "musique", "jazz", "opera", "opéra", "classical", "classique", "rock", "music"]
        for term in music_terms:
            result = map_category_to_db(term)
            assert result == "Musique", f"'{term}' should map to 'Musique'"

    def test_theater_categories(self):
        """Test theater-related categories are mapped."""
        theater_terms = ["theater", "theatre", "théâtre"]
        for term in theater_terms:
            result = map_category_to_db(term)
            assert result == "Théâtre / Spectacle", f"'{term}' should map to 'Théâtre / Spectacle'"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
