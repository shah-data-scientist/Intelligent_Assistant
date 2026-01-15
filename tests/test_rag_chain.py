"Tests for the RAGChain orchestrator."

from unittest.mock import MagicMock, patch
import pytest
from src.retrieval.chain import RAGChain
from src.data.models import Event

@pytest.fixture
def mock_components():
    """Mock vector store and LLM."""
    with patch("src.retrieval.chain.EventVectorStore") as mock_vs_class, \
         patch("src.retrieval.chain.MistralLLM") as mock_llm_class:
        
        mock_vs = MagicMock()
        mock_vs_class.return_value = mock_vs
        
        mock_llm = MagicMock()
        # Mock the underlying ChatMistralAI instance
        mock_llm.llm = MagicMock()
        mock_llm_class.return_value = mock_llm
        
        yield mock_vs, mock_llm

def test_rag_chain_initialization(mock_components):
    """Test chain initialization."""
    mock_vs, _ = mock_components
    chain = RAGChain()
    
    assert chain.vector_store == mock_vs
    mock_vs.load_index.assert_called_once()

def test_rag_chain_query(mock_components):
    """Test full query workflow by mocking chain.invoke."""
    mock_vs, _ = mock_components
    
    chain = RAGChain()
    # Mock the full LCEL chain's invoke method to avoid Pydantic validation issues with partial mocks
    chain.chain = MagicMock()
    chain.chain.invoke.return_value = "Mocked answer about jazz."
    
    answer = chain.query("Tell me about jazz")
    
    assert answer == "Mocked answer about jazz."
    chain.chain.invoke.assert_called_once()

def test_rag_chain_query_with_metadata(mock_components):
    """Test query with source tracking by mocking internal components."""
    mock_vs, _ = mock_components
    
    # Create sample event
    sample_event = Event(event_id="1", title="Jazz Event")
    
    chain = RAGChain()
    # Mock the retriever and chain
    chain.retriever = MagicMock()
    chain.retriever.invoke.return_value = [
        MagicMock(page_content="Jazz event content", metadata={"title": "Jazz Event", "score": 0.9})
    ]
    chain.chain = MagicMock()
    chain.chain.invoke.return_value = "Mocked answer about jazz."
    
    result = chain.query_with_metadata("Tell me about jazz")
    
    assert result["answer"] == "Mocked answer about jazz."
    assert len(result["sources"]) == 1
    assert result["sources"][0]["title"] == "Jazz Event"
    assert result["sources"][0]["score"] == 0.9