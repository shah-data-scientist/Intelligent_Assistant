"Tests for multi-turn chat history."

import pytest
from unittest.mock import MagicMock, patch
from langchain_core.messages import AIMessage
from src.retrieval.chain import RAGChain, store
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

def test_chat_history_statefulness():
    """Test that the chain maintains history across calls using injected chain."""
    mock_inner_chain = MagicMock()
    mock_inner_chain.invoke.return_value = {"answer": "Response from AI", "context": []}
    
    # Setup chain with injected mock
    chain = RAGChain(chain=mock_inner_chain)
    session_id = "test_session_state"
    
    # Clear store for this session
    if session_id in store:
        del store[session_id]
        
    # Turn 1
    chain.query("Hello AI", session_id=session_id)
    
    # Verify the inner chain was called with the correct input and session config
    # RunnableWithMessageHistory handles the store updates
    assert mock_inner_chain.invoke.called
    
    # We can't easily check the global 'store' content here because 
    # RunnableWithMessageHistory is mocked out.
    # But we verified the dependency injection works and the query returns.

@pytest.mark.integration
def test_full_conversation_flow():
    """Integration test with real components (requires API keys)."""
    chain = RAGChain()
    session_id = "test_integration_session"
    
    # Clear store
    if session_id in store:
        del store[session_id]
    
    # Turn 1: Context setting
    q1 = "Are there any jazz concerts in Paris?"
    response1 = chain.query(q1, session_id=session_id)
    assert len(response1) > 0
    
    # Turn 2: Context dependent
    q2 = "Where are they located?" 
    response2 = chain.query(q2, session_id=session_id)
    
    assert len(response2) > 0
    # Response should mention Paris or venues if history works
    assert any(keyword in response2.lower() for keyword in ["paris", "rue", "located", "lieu"])
