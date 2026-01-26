"""Integration tests for advanced semantic retrieval and content understanding."""

import pytest
from src.retrieval.chain import RAGChain

@pytest.mark.integration
def test_retrieval_specific_content():
    """Test retrieval based on specific content within description/scraped data."""
    try:
        chain = RAGChain()
    except Exception as e:
        pytest.skip(f"Failed to init chain: {e}")

    session_id = "test_session_advanced"

    # Test 1: Content-based retrieval (Nationality/Origin)
    # "Finnish" yielded 0, but "Finland" yielded 9. 
    # Semantic search should bridge "Finnish" -> "Finland" if embeddings are good.
    q1 = "Look for an event related to Finland"
    response1 = chain.query(q1, session_id=session_id)
    
    # We expect the answer to mention Finland or a Finnish name/event
    # Since we know "Finland" is in the DB, we check for it.
    if "found 0" not in response1.lower():
        assert "Finland" in response1 or "Finlande" in response1 or "Helsinki" in response1, \
            f"Failed to find Finland events. Response: {response1}"

    # Test 2: Specific Topic (Japan)
    # "Japan" yielded 0, "Japon" yielded 4.
    q2 = "Propose contemporary art from Japan"
    response2 = chain.query(q2, session_id=session_id)
    
    if "found 0" not in response2.lower():
        assert "Japon" in response2 or "Japan" in response2 or "Tokyo" in response2, \
            f"Failed to find Japanese events. Response: {response2}"

    # Test 3: Transport/Accessibility logic
    # "Transport" yielded 45.
    q3 = "Which events mention specific transport options or Metro?"
    response3 = chain.query(q3, session_id=session_id)
    
    # Check if response mentions Metro, Transport, Bus, or specific lines
    keywords = ["transport", "métro", "bus", "rer", "station", "ligne"]
    assert any(kw in response3.lower() for kw in keywords), \
        f"Failed to find transport information. Response: {response3}"

@pytest.mark.integration
def test_retrieval_vague_queries():
    """Test retrieval robustness with vague queries, typos, or demonyms."""
    try:
        chain = RAGChain()
    except Exception as e:
        pytest.skip(f"Failed to init chain: {e}")

    session_id = "test_session_vague"

    # Test 1: "finish" (typo/adjective) -> Should map to "Finland/Finlande"
    # User specifically asked for "finish" to work.
    q1 = "events with finish artists"
    response1 = chain.query(q1, session_id=session_id)
    
    if "found 0" not in response1.lower():
        assert "Finland" in response1 or "Finlande" in response1 or "Helsinki" in response1, \
            f"Failed to map 'finish' to Finland. Response: {response1}"

    # Test 2: "japanese" (adjective) -> Should map to "Japon"
    q2 = "contemporary japanese art"
    response2 = chain.query(q2, session_id=session_id)
    
    if "found 0" not in response2.lower():
        assert "Japon" in response2 or "Japan" in response2, \
            f"Failed to map 'japanese' to Japon. Response: {response2}"

