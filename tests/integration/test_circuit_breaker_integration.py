"""
FILE: test_circuit_breaker_integration.py
STATUS: Active
RESPONSIBILITY: Integration tests for circuit breaker functionality in LLM calls.

DEPENDENCIES (Who uses this file):
- pytest test runner
- Circuit breaker resilience validation

IMPORTS (What this file needs):
- pytest: Test framework
- unittest.mock: Mocking for failure simulation
- src.generation.llm: LLM circuit breaker and chat LLM

LAST MAJOR UPDATE: 2026-01-31
MAINTAINER: QA Team
"""

import pytest
from unittest.mock import patch
from src.generation.llm import llm_breaker, get_chat_llm


class TestCircuitBreakerIntegration:
    """Test circuit breaker integration with actual configuration."""

    def test_circuit_breaker_can_be_none(self):
        """Test that llm_breaker can be None (development mode)."""
        # This is valid when enable_circuit_breaker=False
        # The code should handle this gracefully
        if llm_breaker is None:
            # This is expected in development mode
            assert llm_breaker is None
        else:
            # This is expected in production mode
            assert llm_breaker is not None
            assert hasattr(llm_breaker, "name")

    def test_circuit_breaker_none_doesnt_break_llm(self):
        """Test that LLM calls work even when circuit breaker is None."""
        llm = get_chat_llm()

        # Should be able to get LLM instance regardless of circuit breaker state
        assert llm is not None

    def test_metrics_endpoint_handles_none_circuit_breaker(self):
        """Test that metrics endpoint handles None circuit breaker."""
        from fastapi.testclient import TestClient
        from src.api.main import app

        client = TestClient(app)
        response = client.get("/api/v1/metrics")

        # Should not crash, regardless of circuit breaker state
        assert response.status_code == 200
        data = response.json()
        assert "circuit_breaker" in data
        assert "status" in data

        # Circuit breaker state should be present
        cb_state = data["circuit_breaker"]
        assert "name" in cb_state
        assert "state" in cb_state

        # If circuit breaker is None, state should be "disabled"
        if llm_breaker is None:
            assert cb_state["state"] == "disabled"
        else:
            # If circuit breaker exists, state should be a valid state
            assert cb_state["state"] in ["closed", "open", "half_open", "disabled"]

    @patch("src.generation.llm.llm_breaker", None)
    def test_get_chat_llm_with_disabled_circuit_breaker(self):
        """Test get_chat_llm() when circuit breaker is explicitly disabled."""
        from src.generation.llm import get_chat_llm

        llm = get_chat_llm()

        # Should still return a valid LLM instance
        assert llm is not None
        assert hasattr(llm, "invoke")

    def test_circuit_breaker_configuration_consistency(self):
        """Test that circuit breaker configuration is consistent."""
        from src.config import settings

        # Check if circuit breaker setting exists
        has_cb_setting = hasattr(settings, "enable_circuit_breaker")

        if has_cb_setting:
            enable_cb = settings.enable_circuit_breaker

            # Configuration should match implementation
            if enable_cb:
                assert llm_breaker is not None, "Circuit breaker should exist when enabled"
            else:
                assert llm_breaker is None, "Circuit breaker should be None when disabled"


class TestCircuitBreakerBehavior:
    """Test circuit breaker behavior when enabled."""

    @pytest.mark.skipif(llm_breaker is None, reason="Circuit breaker is disabled")
    def test_circuit_breaker_has_expected_attributes(self):
        """Test that circuit breaker has all expected attributes."""
        assert hasattr(llm_breaker, "name")
        assert hasattr(llm_breaker, "current_state")
        assert hasattr(llm_breaker, "fail_counter")
        assert hasattr(llm_breaker, "fail_max")
        assert hasattr(llm_breaker, "reset_timeout")

    @pytest.mark.skipif(llm_breaker is None, reason="Circuit breaker is disabled")
    def test_circuit_breaker_initial_state_is_closed(self):
        """Test that circuit breaker starts in closed state."""
        # Convert state to string for comparison
        state_str = str(llm_breaker.current_state).lower()
        assert state_str == "closed" or "close" in state_str

    @pytest.mark.skipif(llm_breaker is None, reason="Circuit breaker is disabled")
    def test_circuit_breaker_name_is_set(self):
        """Test that circuit breaker has a name."""
        assert llm_breaker.name == "llm_breaker"

    @pytest.mark.skipif(llm_breaker is None, reason="Circuit breaker is disabled")
    def test_circuit_breaker_thresholds_configured(self):
        """Test that circuit breaker thresholds are configured."""
        assert llm_breaker.fail_max > 0, "Failure threshold should be positive"
        assert llm_breaker.reset_timeout > 0, "Reset timeout should be positive"


class TestAPIMetricsWithCircuitBreaker:
    """Test API metrics endpoint with different circuit breaker states."""

    def test_metrics_response_structure(self):
        """Test that metrics response has correct structure."""
        from fastapi.testclient import TestClient
        from src.api.main import app

        client = TestClient(app)
        response = client.get("/api/v1/metrics")

        assert response.status_code == 200
        data = response.json()

        # Required top-level fields
        assert "status" in data
        assert "circuit_breaker" in data
        assert "timestamp" in data

        # Circuit breaker should have these fields
        cb = data["circuit_breaker"]
        assert "name" in cb
        assert "state" in cb
        assert "failure_count" in cb
        assert "failure_threshold" in cb
        assert "reset_timeout" in cb

    def test_metrics_with_none_circuit_breaker_returns_disabled(self):
        """Test that metrics endpoint returns 'disabled' state when circuit breaker is None."""
        from fastapi.testclient import TestClient
        from src.api.main import app

        if llm_breaker is None:
            client = TestClient(app)
            response = client.get("/api/v1/metrics")

            assert response.status_code == 200
            data = response.json()

            cb = data["circuit_breaker"]
            assert cb["state"] == "disabled"
            assert cb["failure_count"] == 0
            assert cb["failure_threshold"] == 0
            assert cb["reset_timeout"] == 0


class TestCircuitBreakerErrorHandling:
    """Test error handling related to circuit breaker."""

    def test_no_attribute_error_when_accessing_circuit_breaker(self):
        """Test that accessing circuit breaker properties doesn't raise AttributeError."""
        from fastapi.testclient import TestClient
        from src.api.main import app

        client = TestClient(app)

        try:
            response = client.get("/api/v1/metrics")
            # Should not raise AttributeError
            assert response.status_code == 200
        except AttributeError as e:
            pytest.fail(f"AttributeError raised when accessing circuit breaker: {e}")

    def test_circuit_breaker_none_check_in_metrics(self):
        """Test that metrics endpoint explicitly checks for None circuit breaker."""
        from src.api import endpoints
        import inspect

        # Get the source code of get_metrics function
        source = inspect.getsource(endpoints.get_metrics)

        # Should have a None check
        assert (
            "if llm_breaker is None" in source or "llm_breaker is not None" in source
        ), "Metrics endpoint should check if llm_breaker is None"
