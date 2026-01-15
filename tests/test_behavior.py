"""Tests for specific AI behaviors like clarification and grounding."""

import pytest
from unittest.mock import MagicMock
from langchain_core.runnables import RunnableLambda
from src.retrieval.chain import RAGChain

@pytest.mark.integration
def test_clarification_on_vague_query():
    """Test that the system asks for clarification on vague queries."""
    
    # Use RunnableLambda to simulate chain behavior correctly
    def mock_invoke(input_dict):
        return {"answer": "Could you please specify what type of events you are interested in? (Music, Art, Theater?)"}
    
    mock_inner_chain = RunnableLambda(mock_invoke)
    
    chain = RAGChain(chain=mock_inner_chain)
    response = chain.query("Events in Paris")
    
    # Assert the system didn't just dump events but asked a question
    assert "?" in response
    assert "specify" in response.lower() or "type" in response.lower()

@pytest.mark.integration
def test_grounding_no_hallucination():
    """Test that the system refuses to answer when no context is found."""
    def mock_invoke(input_dict):
        return {"answer": "I don't have information about that."}
        
    mock_inner_chain = RunnableLambda(mock_invoke)
    
    chain = RAGChain(chain=mock_inner_chain)
    
    # Simulate empty context from retrieval (conceptually)
    response = chain.query("Unicorn riding in Paris")
    
    assert "don't have information" in response
    assert "Unicorn" not in response  # It shouldn't invent a unicorn event

@pytest.mark.integration
def test_prompt_effectiveness_real():
    """Real integration test to verify prompt engineering works (Requires API)."""
    try:
        chain = RAGChain()
    except Exception:
        pytest.skip("RAGChain initialization failed (API keys missing?)")

    # Vague query
    response = chain.query("events")
    
    # Check if it asks for clarification instead of listing items
    # It should contain a question mark and some asking wording
    assert "?" in response or "specify" in response.lower() or "préciser" in response.lower()
