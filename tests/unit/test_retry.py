"""
FILE: test_retry.py
STATUS: Active
RESPONSIBILITY: Unit tests for retry decorator utilities.
LAST MAJOR UPDATE: 2026-01-31
MAINTAINER: QA Team
"""

import pytest

from src.utils.retry import (
    RetryExhaustedError,
    retry_with_backoff,
    retry_on_network_error,
    retry_on_api_error,
)


class TestRetryWithBackoff:
    """Test retry_with_backoff decorator."""

    def test_successful_first_attempt(self):
        """Test function that succeeds on first attempt."""
        call_count = {"count": 0}

        @retry_with_backoff(max_attempts=3, initial_delay=0.01)
        def successful_func():
            call_count["count"] += 1
            return "success"

        result = successful_func()
        assert result == "success"
        assert call_count["count"] == 1

    def test_retry_on_failure_then_success(self):
        """Test function that fails then succeeds."""
        call_count = {"count": 0}

        @retry_with_backoff(max_attempts=3, initial_delay=0.01)
        def flaky_func():
            call_count["count"] += 1
            if call_count["count"] < 2:
                raise ConnectionError("Temporary failure")
            return "success"

        result = flaky_func()
        assert result == "success"
        assert call_count["count"] == 2

    def test_retry_exhausted(self):
        """Test that RetryExhaustedError is raised after max attempts."""
        call_count = {"count": 0}

        @retry_with_backoff(max_attempts=3, initial_delay=0.01)
        def always_fails():
            call_count["count"] += 1
            raise ValueError("Always fails")

        with pytest.raises(RetryExhaustedError) as exc_info:
            always_fails()

        assert "Failed after 3 attempts" in str(exc_info.value)
        assert call_count["count"] == 3

    def test_specific_exceptions_only(self):
        """Test that only specified exceptions are caught."""
        call_count = {"count": 0}

        @retry_with_backoff(max_attempts=3, initial_delay=0.01, exceptions=(ConnectionError,))
        def raises_value_error():
            call_count["count"] += 1
            raise ValueError("Not a network error")

        # ValueError should not be caught, should propagate immediately
        with pytest.raises(ValueError):
            raises_value_error()

        assert call_count["count"] == 1  # Only one attempt

    def test_on_retry_callback(self):
        """Test that on_retry callback is called."""
        retry_calls = []

        def on_retry_callback(exc, attempt, delay):
            retry_calls.append((type(exc).__name__, attempt, delay))

        call_count = {"count": 0}

        @retry_with_backoff(
            max_attempts=3,
            initial_delay=0.01,
            backoff_factor=2.0,
            on_retry=on_retry_callback,
        )
        def flaky_func():
            call_count["count"] += 1
            if call_count["count"] < 3:
                raise ConnectionError("Temp error")
            return "success"

        result = flaky_func()
        assert result == "success"
        assert len(retry_calls) == 2
        assert retry_calls[0][0] == "ConnectionError"
        assert retry_calls[0][1] == 1  # First retry attempt

    def test_max_delay_respected(self):
        """Test that max_delay caps the delay."""
        call_count = {"count": 0}
        delays = []

        def capture_delay(exc, attempt, delay):
            delays.append(delay)

        @retry_with_backoff(
            max_attempts=5,
            initial_delay=10.0,
            backoff_factor=10.0,
            max_delay=0.01,  # Cap at 10ms
            on_retry=capture_delay,
        )
        def always_fails():
            call_count["count"] += 1
            raise ConnectionError("Fail")

        with pytest.raises(RetryExhaustedError):
            always_fails()

        # All delays should be capped at max_delay
        for delay in delays:
            assert delay <= 0.01

    def test_preserves_function_metadata(self):
        """Test that functools.wraps preserves function metadata."""

        @retry_with_backoff(max_attempts=3)
        def documented_function():
            """This is a docstring."""
            pass

        assert documented_function.__name__ == "documented_function"
        assert "docstring" in documented_function.__doc__


class TestRetryOnNetworkError:
    """Test retry_on_network_error convenience decorator."""

    def test_retries_connection_error(self):
        """Test that ConnectionError triggers retry."""
        call_count = {"count": 0}

        @retry_on_network_error(max_attempts=3, initial_delay=0.01)
        def network_func():
            call_count["count"] += 1
            if call_count["count"] < 2:
                raise ConnectionError("Network down")
            return "connected"

        result = network_func()
        assert result == "connected"
        assert call_count["count"] == 2

    def test_retries_timeout_error(self):
        """Test that TimeoutError triggers retry."""
        call_count = {"count": 0}

        @retry_on_network_error(max_attempts=3, initial_delay=0.01)
        def slow_func():
            call_count["count"] += 1
            if call_count["count"] < 2:
                raise TimeoutError("Timed out")
            return "completed"

        result = slow_func()
        assert result == "completed"
        assert call_count["count"] == 2


class TestRetryOnApiError:
    """Test retry_on_api_error convenience decorator."""

    def test_retries_connection_error(self):
        """Test that ConnectionError triggers retry."""
        call_count = {"count": 0}

        @retry_on_api_error(max_attempts=3, initial_delay=0.01)
        def api_func():
            call_count["count"] += 1
            if call_count["count"] < 2:
                raise ConnectionError("API unavailable")
            return {"status": "ok"}

        result = api_func()
        assert result == {"status": "ok"}
        assert call_count["count"] == 2

    def test_exhausts_retries(self):
        """Test that all retries are exhausted on persistent failure."""
        call_count = {"count": 0}

        @retry_on_api_error(max_attempts=3, initial_delay=0.01)
        def always_fails():
            call_count["count"] += 1
            raise TimeoutError("API timeout")

        with pytest.raises(RetryExhaustedError):
            always_fails()

        assert call_count["count"] == 3


class TestRetryExhaustedError:
    """Test RetryExhaustedError exception."""

    def test_exception_message(self):
        """Test exception message format."""
        error = RetryExhaustedError("Failed after 5 attempts. Last error: Connection refused")
        assert "Failed after 5 attempts" in str(error)
        assert "Connection refused" in str(error)

    def test_is_exception(self):
        """Test that RetryExhaustedError is an Exception."""
        assert issubclass(RetryExhaustedError, Exception)


class TestHttpxImportFallback:
    """Test fallback behavior when httpx is not available."""

    def test_retry_on_network_error_without_httpx(self):
        """Test that retry_on_network_error falls back when httpx not available."""
        import sys

        # Temporarily hide httpx from imports
        httpx_module = sys.modules.get("httpx")
        sys.modules["httpx"] = None

        try:
            # Force reimport
            import importlib
            import src.utils.retry as retry_module

            importlib.reload(retry_module)

            call_count = {"count": 0}

            @retry_module.retry_on_network_error(max_attempts=3, initial_delay=0.01)
            def test_func():
                call_count["count"] += 1
                if call_count["count"] < 2:
                    raise ConnectionError("Test error")
                return "success"

            result = test_func()
            assert result == "success"
            assert call_count["count"] == 2
        finally:
            # Restore httpx
            if httpx_module:
                sys.modules["httpx"] = httpx_module
            elif "httpx" in sys.modules:
                del sys.modules["httpx"]

    def test_retry_on_api_error_without_httpx(self):
        """Test that retry_on_api_error falls back when httpx not available."""
        import sys

        httpx_module = sys.modules.get("httpx")
        sys.modules["httpx"] = None

        try:
            import importlib
            import src.utils.retry as retry_module

            importlib.reload(retry_module)

            call_count = {"count": 0}

            @retry_module.retry_on_api_error(max_attempts=3, initial_delay=0.01)
            def api_func():
                call_count["count"] += 1
                if call_count["count"] < 2:
                    raise TimeoutError("Timeout")
                return {"status": "ok"}

            result = api_func()
            assert result == {"status": "ok"}
            assert call_count["count"] == 2
        finally:
            if httpx_module:
                sys.modules["httpx"] = httpx_module
            elif "httpx" in sys.modules:
                del sys.modules["httpx"]


class TestRetryWithHttpx:
    """Test retry with httpx exceptions when available."""

    def test_retry_on_network_error_with_httpx(self):
        """Test that httpx errors trigger retry."""
        try:
            import httpx
        except ImportError:
            pytest.skip("httpx not installed")

        call_count = {"count": 0}

        @retry_on_network_error(max_attempts=3, initial_delay=0.01)
        def network_func():
            call_count["count"] += 1
            if call_count["count"] < 2:
                raise httpx.ConnectError("Connection failed")
            return "connected"

        result = network_func()
        assert result == "connected"
        assert call_count["count"] == 2

    def test_retry_on_api_error_with_httpx_timeout(self):
        """Test that httpx TimeoutException triggers retry."""
        try:
            import httpx
        except ImportError:
            pytest.skip("httpx not installed")

        call_count = {"count": 0}

        @retry_on_api_error(max_attempts=3, initial_delay=0.01)
        def api_func():
            call_count["count"] += 1
            if call_count["count"] < 2:
                raise httpx.TimeoutException("Request timed out")
            return {"data": "success"}

        result = api_func()
        assert result == {"data": "success"}
        assert call_count["count"] == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
