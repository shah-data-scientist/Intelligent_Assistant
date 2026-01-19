import pytest
from src.retrieval.chain import RAGChain

@pytest.mark.integration
def test_rag_global_stats_integration():
    """Test that the RAG chain correctly uses global stats in the prompt."""
    try:
        chain = RAGChain()
    except Exception as e:
        pytest.skip(f"Failed to init chain (likely no DB/Index): {e}")

    session_id = "test_session_global_stats"
    
    # Test 1: Total count query
    q1 = "How many events do you have in your database?"
    response1 = chain.query(q1, session_id=session_id)
    
    # We expect the bot to mention the count (around 1000) or the date range.
    # It might say "1009" or "over 1000".
    assert "1009" in response1 or "1,009" in response1 or "1000" in response1
    
    # Test 2: Date range check (implicit)
    # The prompt should enable it to answer this, but specific phrasing varies.
    # We just check it doesn't say "I don't know" or "I don't have information".
    assert "don't have information" not in response1.lower()

    # Test 3: Specific category (Jazz)
    q2 = "Do you have any jazz concerts?"
    response2 = chain.query(q2, session_id=session_id)
    assert len(response2) > 50  # Should be a substantive answer

@pytest.mark.integration
def test_fallback_logic():
    """Test that querying a non-existent city triggers fallback to regional search."""
    try:
        chain = RAGChain()
    except Exception as e:
        pytest.skip(f"Failed to init chain: {e}")

    session_id = "test_session_fallback"
    
    # Query for a fake city but valid date/category
    # We know Nov 2026 has many events
    q = "Music events in Atlantis in November 2026"
    
    response = chain.query(q, session_id=session_id)
    
    # The extraction chain might be smart enough to NOT extract Atlantis if it knows valid cities, 
    # but assuming it extracts "Atlantis", the retrieval will fail and fallback.
    
    # Check if the response acknowledges the missing city or offers nearby events
    # We look for keywords like "found", "nearby", "Île-de-France", "Atlantis"
    
    print(f"Fallback Response: {response}")
    
    # It should NOT say "I don't have information".
    assert "don't have information" not in response.lower()
    
    # It SHOULD ideally mention it's showing other events
    assert "Île-de-France" in response or "nearby" in response or "Atlantis" in response
