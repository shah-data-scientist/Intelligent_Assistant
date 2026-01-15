"""Tests for FastAPI endpoints."""

from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient
from src.api.main import app
from src.api.endpoints import get_rag_chain

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
            {
                "title": "Jazz Event",
                "city": "Paris",
                "date": "2026-01-01",
                "url": "http://example.com",
                "score": 0.95
            }
        ]
    }
    return mock_chain

def test_health_check():
    """Test health check endpoint."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_chat_endpoint(mock_rag_chain):
    """Test chat endpoint with mocked RAG chain."""
    # Override dependency
    app.dependency_overrides[get_rag_chain] = lambda: mock_rag_chain
    
    payload = {"question": "Tell me about jazz in Paris"}
    response = client.post("/api/v1/chat", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    assert data["answer"] == "This is a mocked answer about jazz."
    assert len(data["sources"]) == 1
    assert data["sources"][0]["title"] == "Jazz Event"
    assert data["sources"][0]["city"] == "Paris"
    
    # Verify chain was called
    mock_rag_chain.query_with_metadata.assert_called_once_with("Tell me about jazz in Paris")
    
    # Cleanup dependency override
    app.dependency_overrides = {}

def test_chat_endpoint_validation_error():
    """Test chat endpoint validation (short question)."""
    payload = {"question": "Hi"}  # Too short (< 3 chars)
    response = client.post("/api/v1/chat", json=payload)
    assert response.status_code == 422
