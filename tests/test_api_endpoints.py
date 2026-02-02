"""Tests for FastAPI endpoints."""

from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient
from src.api.main import app
from src.api.endpoints import get_rag_chain
from src.config import settings

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_app_state():
    """Ensure app state has a rag_chain mock for all API tests."""
    app.state.rag_chain = MagicMock()
    yield
    app.state.rag_chain = None


@pytest.fixture
def mock_rag_chain():
    """Mock the RAGChain dependency."""
    mock_chain = MagicMock()
    mock_chain.query_with_metadata.return_value = {
        "answer": "This is a mocked answer about jazz.",
        "sources": [
            {"title": "Jazz Event", "city": "Paris", "date": "2026-01-01", "url": "http://example.com", "score": 0.95}
        ],
        "structured_events": [],
        "message_id": 123,
        "needs_clarification": False,
        "clarifying_questions": [],
    }
    return mock_chain


def test_health_check():
    """Test health check endpoint."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@patch("src.api.endpoints.scan_for_pii")
@patch("src.api.endpoints.check_safety")
def test_chat_endpoint(mock_check_safety, mock_scan, mock_rag_chain):
    """Test chat endpoint with mocked RAG chain."""
    # Override dependency
    app.dependency_overrides[get_rag_chain] = lambda: mock_rag_chain

    # Mock PII scan to match what endpoints.py expects (dict with sanitized_text and has_pii)
    mock_scan.return_value = {"sanitized_text": "This is a mocked answer about jazz.", "has_pii": False}

    payload = {"question": "Tell me about jazz in Paris"}
    headers = {"X-API-Key": settings.app_api_key}
    response = client.post("/api/v1/chat", json=payload, headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["answer"] == "This is a mocked answer about jazz."
    assert len(data["sources"]) == 1
    assert data["sources"][0]["title"] == "Jazz Event"
    assert data["sources"][0]["city"] == "Paris"

    # Verify chain was called (allow any kwargs like language)
    mock_rag_chain.query_with_metadata.assert_called_with(
        "Tell me about jazz in Paris", session_id="default_session", language=None
    )

    # Verify PII scan was called with redact=True
    mock_scan.assert_called_with("This is a mocked answer about jazz.", redact=True)

    # Cleanup dependency override
    app.dependency_overrides = {}


def test_chat_endpoint_auth_error():
    """Test chat endpoint with missing or invalid API key."""
    payload = {"question": "Tell me about jazz"}

    # Missing key
    response = client.post("/api/v1/chat", json=payload)
    assert response.status_code == 403

    # Invalid key
    headers = {"X-API-Key": "wrong-key"}
    response = client.post("/api/v1/chat", json=payload, headers=headers)
    assert response.status_code == 403


def test_feedback_endpoint(mock_rag_chain):
    """Test feedback submission endpoint."""
    app.dependency_overrides[get_rag_chain] = lambda: mock_rag_chain

    payload = {"message_id": 123, "is_positive": True, "comment": "Great answer!"}
    headers = {"X-API-Key": settings.app_api_key}
    response = client.post("/api/v1/feedback", json=payload, headers=headers)

    assert response.status_code == 200
    assert response.json()["status"] == "success"

    # Verify feedback was saved to storage via chain
    mock_rag_chain.chat_storage.add_feedback.assert_called_with(
        message_id=123, is_positive=True, comment="Great answer!"
    )

    app.dependency_overrides = {}


def test_metrics_endpoint():
    """Test metrics and circuit breaker status endpoint."""
    response = client.get("/api/v1/metrics")
    assert response.status_code == 200
    data = response.json()
    assert "circuit_breaker" in data
    assert "status" in data
    assert data["status"] == "ok"
