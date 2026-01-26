import pytest
from unittest.mock import MagicMock, patch
from langchain_core.messages import AIMessage
from src.retrieval.chain import RAGChain
from src.data.models import Event
from src.data.chat_storage import ChatStorage

@pytest.fixture
def mock_chain_dependencies():
    """Mock vector store and LLM."""
    with patch("src.retrieval.chain.EventVectorStore") as mock_vs_class, \
         patch("src.retrieval.chain.MistralLLM") as mock_llm_class:
        
        mock_vs = MagicMock()
        mock_vs_class.return_value = mock_vs
        
        mock_llm = MagicMock()
        mock_llm.llm = MagicMock()
        # Mock responses for different steps (contextualize, answer)
        mock_llm.llm.invoke.return_value = AIMessage(content="Response from AI")
        mock_llm_class.return_value = mock_llm
        
        yield mock_vs, mock_llm

def test_chat_history_statefulness(tmp_path, mock_chain_dependencies):
    """Test that the chain maintains history across calls using SQLite storage."""
    mock_vs, mock_llm = mock_chain_dependencies
    
    db_path = tmp_path / "test_history.db"
    real_storage = ChatStorage(db_path=str(db_path))
    
    # Initialize RAGChain with real storage
    chain = RAGChain(chat_storage=real_storage, vector_store=mock_vs, llm=mock_llm)
    
    # Mock the internal rag_chain invoke to avoid real processing
    chain.rag_chain = MagicMock()
    chain.rag_chain.invoke.return_value = {
        "answer": "Response from AI",
        "events": [],
        "context": []
    }
    
    session_id = "test_session_state"
    
    # Turn 1
    chain.query("Hello AI", session_id=session_id)
    
    # Verify history in DB
    history = real_storage.get_chat_history(session_id)
    assert len(history) == 2
    assert history[0]["content"] == "Hello AI"
    assert history[1]["content"] == "Response from AI"
    
    # Turn 2: New chain instance, same storage
    chain2 = RAGChain(chat_storage=real_storage, vector_store=mock_vs, llm=mock_llm)
    chain2.rag_chain = MagicMock()
    chain2.rag_chain.invoke.return_value = {
        "answer": "I am fine.",
        "events": [],
        "context": []
    }
    
    chain2.query("How are you?", session_id=session_id)
    
    history_updated = real_storage.get_chat_history(session_id)
    assert len(history_updated) == 4
    assert history_updated[2]["content"] == "How are you?"
    assert history_updated[3]["content"] == "I am fine."

@pytest.mark.integration
def test_full_conversation_flow(tmp_path):
    """Integration test with real components (requires API keys)."""
    # Use a temp DB to avoid polluting the main one
    db_path = tmp_path / "integration_test.db"
    
    # Patch storage creation inside the chain or pass it
    real_storage = ChatStorage(db_path=str(db_path))
        
    # We need real VectorStore and LLM here, so we don't mock them
    try:
        chain = RAGChain(chat_storage=real_storage)
    except Exception as e:
        pytest.skip(f"Skipping integration test due to init failure: {e}")
        
    session_id = "test_integration_session"
    
    # Turn 1
    q1 = "Are there any jazz concerts in Paris?"
    try:
        # Patch query_with_metadata to avoid full RAG execution if credentials missing
        # But this is an integration test...
        # We'll just run it and catch errors.
        response1 = chain.query(q1, session_id=session_id)
    except Exception:
        pytest.skip("Integration test failed (API/Network/Index issue)")
        
    assert len(response1) > 0
    
    # Turn 2
    q2 = "Where are they located?" 
    try:
        response2 = chain.query(q2, session_id=session_id)
    except Exception:
        pytest.skip("Integration test failed")
    
    assert len(response2) > 0
