
"""Tests for the RAGChain orchestrator."""

from unittest.mock import MagicMock, patch
import pytest
from langchain_core.runnables import RunnableLambda
from src.retrieval.chain import RAGChain
from src.data.models import Event

@pytest.fixture
def mock_chain_dependencies():
    """Mock vector store and LLM."""
    with patch("src.retrieval.chain.EventVectorStore") as mock_vs_class, \
         patch("src.retrieval.chain.MistralLLM") as mock_llm_class:
        
        mock_vs = MagicMock()
        mock_vs_class.return_value = mock_vs
        
        mock_llm = MagicMock()
        mock_llm_class.return_value = mock_llm
        
        yield mock_vs, mock_llm

def test_rag_chain_initialization(mock_chain_dependencies):
    """Test chain initialization."""
    mock_vs, _ = mock_chain_dependencies
    chain = RAGChain()
    assert chain.vector_store == mock_vs
    mock_vs.load_index.assert_called_once()

def test_rag_chain_query(mock_chain_dependencies):
    """Test full query workflow."""
    mock_vs, mock_llm = mock_chain_dependencies

    # Mock the query_with_metadata to return a simple response
    chain = RAGChain()

    with patch.object(chain, 'query_with_metadata') as mock_query:
        mock_query.return_value = {"answer": "Mocked answer about jazz.", "sources": []}
        answer = chain.query("Tell me about jazz")

        assert answer == "Mocked answer about jazz."
        mock_query.assert_called_once()

def test_rag_chain_query_with_metadata(mock_chain_dependencies):
    """Test query with source tracking."""
    mock_vs, mock_llm = mock_chain_dependencies

    chain = RAGChain()

    # Mock query_with_metadata to return a structured response
    with patch.object(chain, 'query_with_metadata') as mock_query:
        mock_query.return_value = {
            "answer": "Mocked answer about jazz.",
            "sources": [
                {
                    "title": "Jazz Event",
                    "score": 0.9,
                    "event_id": "jazz-1",
                    "content": "Jazz event content"
                }
            ],
            "retrieval_stats": {"exact_count": 1, "total_count": 1}
        }

        result = chain.query_with_metadata("Tell me about jazz")

        assert result["answer"] == "Mocked answer about jazz."
        assert len(result["sources"]) == 1
        assert result["sources"][0]["title"] == "Jazz Event"
        assert result["sources"][0]["score"] == 0.9