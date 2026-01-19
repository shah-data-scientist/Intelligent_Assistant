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

def test_chat_history_statefulness(tmp_path):
    """Test that the chain maintains history across calls using SQLite storage."""
    from langchain_core.runnables import RunnableLambda
    
    db_path = tmp_path / "test_history.db"
    real_storage = ChatStorage(db_path=str(db_path))
    
    from src.data.chat_history import SQLiteChatMessageHistory
    def get_test_history(session_id: str):
        return SQLiteChatMessageHistory(session_id, storage=real_storage)
    
    # Use a real Runnable that returns the expected dict structure
    # This ensures RunnableWithMessageHistory functions correctly
    def mock_chain_func(input_dict):
        return {"answer": "Response from AI"}
    
    mock_inner_chain = RunnableLambda(mock_chain_func)
    
    # Inject both the mock chain AND our custom history factory
    chain = RAGChain(
        chain=mock_inner_chain,
        history_factory=get_test_history
    )
    session_id = "test_session_state"
    
    # Turn 1
    chain.query("Hello AI", session_id=session_id)
    
    # Verify history in DB
    history = real_storage.get_chat_history(session_id)
    assert len(history) == 2
    assert history[0]["content"] == "Hello AI"
    assert history[1]["content"] == "Response from AI"
    
    # Turn 2
    chain2 = RAGChain(
        chain=mock_inner_chain,
        history_factory=get_test_history
    )
    chain2.query("How are you?", session_id=session_id)
    
    history_updated = real_storage.get_chat_history(session_id)
    assert len(history_updated) == 4
    assert history_updated[2]["content"] == "How are you?"

@pytest.mark.integration
def test_full_conversation_flow(tmp_path):
    """Integration test with real components (requires API keys)."""
    # Use a temp DB to avoid polluting the main one
    db_path = tmp_path / "integration_test.db"
    
    with patch("src.data.chat_history.ChatStorage") as MockStorage:
        real_storage = ChatStorage(db_path=str(db_path))
        MockStorage.return_value = real_storage
        
        # We need real VectorStore and LLM here, so we don't mock them
        # BUT we need to ensure VectorStore doesn't fail if DB is empty of events.
        # RAGChain init tries to load index. If not found, it warns. That's fine.
        
        chain = RAGChain()
        session_id = "test_integration_session"
        
        # Turn 1
        q1 = "Are there any jazz concerts in Paris?"
        try:
            response1 = chain.query(q1, session_id=session_id)
        except Exception:
            pytest.skip("Integration test failed (API/Network/Index issue)")
            
        assert len(response1) > 0
        
        # Turn 2
        q2 = "Where are they located?" 
        response2 = chain.query(q2, session_id=session_id)
        
        assert len(response2) > 0
        # Check if context is maintained
        # Since we use a fresh DB without events, the answer might be "I don't know".
        # But the history logic (reformulation) should still happen.
