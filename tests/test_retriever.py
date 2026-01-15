"""Tests for the EventRetriever component."""

from unittest.mock import MagicMock
import pytest
from langchain_core.documents import Document
from src.retrieval.retriever import EventRetriever
from src.data.models import Event, EventLocation

@pytest.fixture
def mock_vector_store():
    """Create a mock vector store."""
    vs = MagicMock()
    # Mock search return value: list[tuple[Event, float]]
    sample_event = Event(
        event_id="test-1",
        title="Jazz Concert",
        description="A great jazz concert",
        category="Music",
        location=EventLocation(city="Paris")
    )
    vs.search.return_value = [(sample_event, 0.95)]
    return vs

def test_retriever_get_relevant_documents(mock_vector_store):
    """Test standard document retrieval."""
    retriever = EventRetriever(vector_store=mock_vector_store, k=1)
    
    # We use invoke because BaseRetriever is a Runnable
    docs = retriever.invoke("jazz in paris")
    
    assert len(docs) == 1
    assert isinstance(docs[0], Document)
    assert "Jazz Concert" in docs[0].page_content
    assert docs[0].metadata["city"] == "Paris"
    assert docs[0].metadata["score"] == 0.95
    
    mock_vector_store.search.assert_called_once_with("jazz in paris", k=1)

def test_retriever_search_with_filters(mock_vector_store):
    """Test retrieval with explicit metadata filters."""
    retriever = EventRetriever(vector_store=mock_vector_store, k=5)
    
    filters = {"city": "Paris"}
    docs = retriever.search_with_filters("concert", k=2, metadata_filter=filters)
    
    assert len(docs) == 1
    mock_vector_store.search.assert_called_once_with("concert", k=2, metadata_filter=filters)
