"""
FILE: test_endpoints.py
STATUS: Active
RESPONSIBILITY: Unit tests for FastAPI API endpoints.

DEPENDENCIES (Who uses this file):
- CI/CD: Runs during test suite

IMPORTS (What this file needs):
- pytest: Test framework
- unittest.mock: For mocking dependencies
- fastapi: For app creation
- fastapi.testclient: For testing endpoints

LAST MAJOR UPDATE: 2026-02-02
MAINTAINER: QA Team
"""

import pytest
from unittest.mock import MagicMock, patch
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient


# Mock RAGChain before importing endpoints to avoid import errors
@pytest.fixture(autouse=True)
def mock_rag_chain_import():
    """Mock RAGChain import at module level."""
    mock_chain_class = MagicMock()
    with patch.dict(
        "sys.modules",
        {
            "src.retrieval.chain": MagicMock(RAGChain=mock_chain_class),
        },
    ):
        yield mock_chain_class


class TestVerifyApiKey:
    """Test API key verification."""

    def test_valid_api_key(self):
        """Test that valid API key passes verification."""
        with patch("src.api.endpoints.settings") as mock_settings:
            mock_settings.app_api_key = "test-key"  # pragma: allowlist secret

            # Import after mocking
            from src.api.endpoints import verify_api_key

            # Run async function
            import asyncio

            result = asyncio.run(verify_api_key("test-key"))
            assert result == "test-key"

    def test_invalid_api_key(self):
        """Test that invalid API key raises HTTPException."""
        with patch("src.api.endpoints.settings") as mock_settings:
            mock_settings.app_api_key = "correct-key"  # pragma: allowlist secret

            from src.api.endpoints import verify_api_key

            import asyncio

            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(verify_api_key("wrong-key"))

            assert exc_info.value.status_code == 403


class TestGetRagChain:
    """Test RAG chain dependency injection."""

    def test_chain_exists(self):
        """Test getting RAG chain when initialized."""
        from src.api.endpoints import get_rag_chain

        mock_request = MagicMock()
        mock_chain = MagicMock()
        mock_request.app.state.rag_chain = mock_chain

        result = get_rag_chain(mock_request)
        assert result == mock_chain

    def test_chain_not_initialized(self):
        """Test error when RAG chain not initialized."""
        from src.api.endpoints import get_rag_chain

        mock_request = MagicMock()
        mock_request.app.state.rag_chain = None

        with pytest.raises(HTTPException) as exc_info:
            get_rag_chain(mock_request)

        assert exc_info.value.status_code == 503
        assert "not initialized" in exc_info.value.detail


class TestHealthEndpoint:
    """Test health check endpoint."""

    @pytest.fixture
    def app_with_chain(self):
        """Create test app with mocked RAG chain."""
        app = FastAPI()

        # Import router after mocking dependencies
        with patch("src.retrieval.chain.RAGChain"):
            from src.api.endpoints import router

            app.include_router(router)

        # Set up app state
        app.state.rag_chain = MagicMock()

        return app

    @pytest.fixture
    def app_without_chain(self):
        """Create test app without RAG chain."""
        app = FastAPI()

        with patch("src.retrieval.chain.RAGChain"):
            from src.api.endpoints import router

            app.include_router(router)

        return app

    def test_health_check_initialized(self, app_with_chain):
        """Test health check when RAG is initialized."""
        client = TestClient(app_with_chain)
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["rag_system"] == "initialized"

    def test_health_check_not_initialized(self, app_without_chain):
        """Test health check when RAG is not initialized."""
        client = TestClient(app_without_chain)
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "error"
        assert data["rag_system"] == "not_initialized"


class TestChatEndpoint:
    """Test chat endpoint."""

    @pytest.fixture
    def mock_app(self):
        """Create test app with all necessary mocks."""
        app = FastAPI()

        # Mock all dependencies
        with (
            patch("src.retrieval.chain.RAGChain"),
            patch("src.api.endpoints.check_safety"),
            patch("src.api.endpoints.scan_for_pii") as mock_scan,
            patch("src.api.endpoints.generate_trace_id", return_value="trace-123"),
            patch("src.api.endpoints.clear_trace_id"),
            patch("src.api.endpoints.settings") as mock_settings,
        ):
            mock_settings.app_api_key = "test-api-key"  # pragma: allowlist secret
            mock_scan.return_value = {"sanitized_text": "Test answer", "has_pii": False}

            from src.api.endpoints import router

            app.include_router(router)

        # Set up mock chain
        mock_chain = MagicMock()
        mock_chain.query_with_metadata.return_value = {
            "answer": "Test answer",
            "sources": [],
            "structured_events": [],
            "message_id": "msg-123",
            "needs_clarification": False,
            "clarifying_questions": [],
        }
        app.state.rag_chain = mock_chain

        return app

    def test_chat_without_api_key(self, mock_app):
        """Test chat endpoint without API key returns 403."""
        client = TestClient(mock_app)
        response = client.post("/chat", json={"question": "Test?"})

        assert response.status_code == 403

    def test_chat_with_wrong_api_key(self, mock_app):
        """Test chat endpoint with wrong API key returns 403."""
        with patch("src.api.endpoints.settings") as mock_settings:
            mock_settings.app_api_key = "correct-key"  # pragma: allowlist secret

            client = TestClient(mock_app)
            response = client.post("/chat", json={"question": "Test?"}, headers={"X-API-Key": "wrong-key"})

            assert response.status_code == 403


class TestFeedbackEndpoint:
    """Test feedback endpoint."""

    @pytest.fixture
    def mock_app(self):
        """Create test app for feedback tests."""
        app = FastAPI()

        with (
            patch("src.retrieval.chain.RAGChain"),
            patch("src.api.endpoints.settings") as mock_settings,
        ):
            mock_settings.app_api_key = "test-api-key"  # pragma: allowlist secret

            from src.api.endpoints import router

            app.include_router(router)

        mock_chain = MagicMock()
        mock_chain.chat_storage = MagicMock()
        app.state.rag_chain = mock_chain

        return app

    def test_feedback_without_api_key(self, mock_app):
        """Test feedback endpoint without API key returns 403."""
        client = TestClient(mock_app)
        response = client.post("/feedback", json={"message_id": "msg-123", "is_positive": True})

        assert response.status_code == 403


class TestMetricsEndpoint:
    """Test metrics endpoint."""

    @pytest.fixture
    def mock_app(self):
        """Create test app for metrics tests."""
        app = FastAPI()

        with patch("src.retrieval.chain.RAGChain"):
            from src.api.endpoints import router

            app.include_router(router)

        return app

    def test_metrics_with_breaker_enabled(self, mock_app):
        """Test metrics when circuit breaker is enabled."""
        mock_breaker = MagicMock()
        mock_breaker.name = "llm_breaker"
        mock_breaker.current_state = "closed"
        mock_breaker.fail_counter = 0
        mock_breaker.fail_max = 5
        mock_breaker.reset_timeout = 60

        with patch("src.api.endpoints.llm_breaker", mock_breaker):
            client = TestClient(mock_app)
            response = client.get("/metrics")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
            assert data["circuit_breaker"]["enabled"] is True
            assert data["circuit_breaker"]["name"] == "llm_breaker"

    def test_metrics_with_breaker_disabled(self, mock_app):
        """Test metrics when circuit breaker is disabled."""
        with patch("src.api.endpoints.llm_breaker", None):
            client = TestClient(mock_app)
            response = client.get("/metrics")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
            assert data["circuit_breaker"]["enabled"] is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
