"""
FILE: test_tracing.py
STATUS: Active
RESPONSIBILITY: Unit tests for request tracing utilities.
LAST MAJOR UPDATE: 2026-01-31
MAINTAINER: QA Team
"""

import logging
import pytest
from unittest.mock import MagicMock, patch

from src.utils.tracing import (
    TraceIDFilter,
    get_trace_id,
    set_trace_id,
    clear_trace_id,
    generate_trace_id,
    configure_trace_logging,
    trace_id_var,
    TRACE_LOG_FORMAT,
)


class TestTraceIDFilter:
    """Test TraceIDFilter class."""

    @pytest.fixture(autouse=True)
    def reset_trace_id(self):
        """Reset trace ID before each test."""
        clear_trace_id()
        yield
        clear_trace_id()

    def test_filter_adds_trace_id_to_record(self):
        """Test that filter adds trace_id attribute to log record."""
        trace_filter = TraceIDFilter()
        record = MagicMock()

        set_trace_id("test-trace-123")
        result = trace_filter.filter(record)

        assert result is True
        assert record.trace_id == "test-trace-123"

    def test_filter_uses_no_trace_when_not_set(self):
        """Test that filter uses 'no-trace' when trace ID is not set."""
        trace_filter = TraceIDFilter()
        record = MagicMock()

        clear_trace_id()
        result = trace_filter.filter(record)

        assert result is True
        assert record.trace_id == "no-trace"


class TestGetTraceId:
    """Test get_trace_id function."""

    @pytest.fixture(autouse=True)
    def reset_trace_id(self):
        """Reset trace ID before each test."""
        clear_trace_id()
        yield
        clear_trace_id()

    def test_returns_existing_trace_id(self):
        """Test that existing trace ID is returned."""
        set_trace_id("existing-trace")
        result = get_trace_id()
        assert result == "existing-trace"

    def test_generates_new_trace_id_if_none(self):
        """Test that new trace ID is generated if not set."""
        clear_trace_id()
        result = get_trace_id()

        assert result is not None
        assert len(result) == 36  # UUID format

    def test_generated_id_is_stored(self):
        """Test that generated trace ID is stored in context."""
        clear_trace_id()
        trace_id = get_trace_id()

        # Second call should return same ID
        assert get_trace_id() == trace_id


class TestSetTraceId:
    """Test set_trace_id function."""

    @pytest.fixture(autouse=True)
    def reset_trace_id(self):
        """Reset trace ID before each test."""
        clear_trace_id()
        yield
        clear_trace_id()

    def test_sets_trace_id(self):
        """Test that trace ID is set correctly."""
        set_trace_id("my-custom-trace")
        assert trace_id_var.get() == "my-custom-trace"

    def test_overwrites_existing_trace_id(self):
        """Test that existing trace ID is overwritten."""
        set_trace_id("first-trace")
        set_trace_id("second-trace")
        assert trace_id_var.get() == "second-trace"


class TestClearTraceId:
    """Test clear_trace_id function."""

    def test_clears_trace_id(self):
        """Test that trace ID is cleared."""
        set_trace_id("to-be-cleared")
        clear_trace_id()
        assert trace_id_var.get() is None


class TestGenerateTraceId:
    """Test generate_trace_id function."""

    @pytest.fixture(autouse=True)
    def reset_trace_id(self):
        """Reset trace ID before each test."""
        clear_trace_id()
        yield
        clear_trace_id()

    def test_generates_uuid(self):
        """Test that generated trace ID is a valid UUID."""
        trace_id = generate_trace_id()
        assert len(trace_id) == 36
        assert trace_id.count('-') == 4

    def test_sets_generated_id(self):
        """Test that generated ID is set in context."""
        trace_id = generate_trace_id()
        assert trace_id_var.get() == trace_id

    def test_generates_unique_ids(self):
        """Test that each call generates unique ID."""
        id1 = generate_trace_id()
        clear_trace_id()
        id2 = generate_trace_id()
        assert id1 != id2


class TestConfigureTraceLogging:
    """Test configure_trace_logging function."""

    def test_configures_logging_handlers(self):
        """Test that logging handlers are configured with trace filter."""
        # Create a mock handler
        mock_handler = MagicMock()
        mock_handler.addFilter = MagicMock()
        mock_handler.setFormatter = MagicMock()

        with patch('src.utils.tracing.logging.getLogger') as mock_get_logger:
            mock_logger = MagicMock()
            mock_logger.handlers = [mock_handler]
            mock_get_logger.return_value = mock_logger

            configure_trace_logging()

            # Handler should have filter added and formatter set
            mock_handler.addFilter.assert_called_once()
            mock_handler.setFormatter.assert_called_once()


class TestConstants:
    """Test module constants."""

    def test_trace_log_format_contains_trace_id(self):
        """Test that log format includes trace_id placeholder."""
        assert "%(trace_id)s" in TRACE_LOG_FORMAT

    def test_trace_log_format_contains_standard_fields(self):
        """Test that log format includes standard logging fields."""
        assert "%(asctime)s" in TRACE_LOG_FORMAT
        assert "%(levelname)s" in TRACE_LOG_FORMAT
        assert "%(name)s" in TRACE_LOG_FORMAT


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
