"""
FILE: test_processor.py
STATUS: Active
RESPONSIBILITY: Unit tests for data processor utilities.
LAST MAJOR UPDATE: 2026-01-31
MAINTAINER: QA Team
"""

import pytest
from datetime import datetime

from src.data.processor import EventProcessor


class TestEventProcessor:
    """Test EventProcessor class."""

    @pytest.fixture
    def processor(self):
        """Create processor instance."""
        return EventProcessor()

    def test_safe_normalize_empty(self, processor):
        """Test normalization with empty input."""
        assert processor.safe_normalize(None) == ""
        assert processor.safe_normalize("") == ""

    def test_safe_normalize_list_input(self, processor):
        """Test normalization with list input."""
        result = processor.safe_normalize(["item1", "item2", "item3"])
        assert result == "item1, item2, item3"

    def test_safe_normalize_unicode(self, processor):
        """Test unicode normalization preserves French characters."""
        result = processor.safe_normalize("événement culturel à Paris")
        assert "événement" in result
        assert "à" in result

    def test_safe_normalize_removes_double_spaces(self, processor):
        """Test that double spaces are removed."""
        result = processor.safe_normalize("hello   world")
        assert result == "hello world"

    def test_safe_normalize_fixes_punctuation(self, processor):
        """Test punctuation spacing fixes."""
        result = processor.safe_normalize("Hello . World")
        assert result == "Hello. World"

        result = processor.safe_normalize("( test )")
        assert result == "(test)"

    def test_remove_boilerplate_empty(self, processor):
        """Test boilerplate removal with empty input."""
        assert processor.remove_boilerplate(None) == ""
        assert processor.remove_boilerplate("") == ""

    def test_remove_boilerplate_urls(self, processor):
        """Test URL removal."""
        text = "Visit us at http://example.com for more info"
        result = processor.remove_boilerplate(text)
        assert "http://example.com" not in result
        assert "Visit us at" in result

    def test_deduplicate_sentences_empty(self, processor):
        """Test deduplication with empty input."""
        assert processor.deduplicate_sentences(None) == ""
        assert processor.deduplicate_sentences("") == ""

    def test_deduplicate_sentences_removes_duplicates(self, processor):
        """Test that duplicate sentences are removed."""
        text = "Hello world. This is a test. Hello world."
        result = processor.deduplicate_sentences(text)
        assert result.count("Hello world") == 1

    def test_deduplicate_sentences_preserves_unique(self, processor):
        """Test that unique sentences are preserved."""
        text = "First sentence. Second sentence. Third sentence."
        result = processor.deduplicate_sentences(text)
        assert "First sentence" in result
        assert "Second sentence" in result
        assert "Third sentence" in result

    def test_clean_title_shouting(self, processor):
        """Test that ALL CAPS titles are fixed."""
        result = processor.clean_title("CONCERT DE JAZZ")
        # Should convert to title case or normal case
        assert result != "CONCERT DE JAZZ" or result.istitle() or result.islower()

    def test_clean_title_empty(self, processor):
        """Test clean_title with empty input."""
        result = processor.clean_title("")
        assert result == ""


class TestProcessorHelpers:
    """Test processor helper methods."""

    @pytest.fixture
    def processor(self):
        """Create processor instance."""
        return EventProcessor()

    def test_junk_phrases_defined(self, processor):
        """Test that junk phrases are defined."""
        assert hasattr(processor, 'JUNK_PHRASES')
        assert len(processor.JUNK_PHRASES) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
