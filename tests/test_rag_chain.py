
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

def test_rag_chain_query():
    """Test full query workflow using injected mock chain."""
    def mock_invoke(input_dict):
        return {"answer": "Mocked answer about jazz."}
    
    mock_inner_chain = RunnableLambda(mock_invoke)
    
    # Inject the mock chain
    chain = RAGChain(chain=mock_inner_chain)
    answer = chain.query("Tell me about jazz")
    
    assert answer == "Mocked answer about jazz."

def test_rag_chain_query_with_metadata():
    """Test query with source tracking using injected mock chain."""
    # Create mock doc
    mock_doc = MagicMock()
    mock_doc.metadata = {"title": "Jazz Event", "score": 0.9}
    mock_doc.page_content = "Jazz event content"
    
    def mock_invoke(input_dict):
        return {
            "answer": "Mocked answer about jazz.",
            "context": [mock_doc]
        }
    
    mock_inner_chain = RunnableLambda(mock_invoke)
    
    chain = RAGChain(chain=mock_inner_chain)
    result = chain.query_with_metadata("Tell me about jazz")
    
    assert result["answer"] == "Mocked answer about jazz."
    assert len(result["sources"]) == 1
    assert result["sources"][0]["title"] == "Jazz Event"
    assert result["sources"][0]["score"] == 0.9