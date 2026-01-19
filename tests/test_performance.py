"""Integration and performance tests using production data."""

import time
import pytest
from src.models.vector_store import EventVectorStore

@pytest.mark.integration
def test_semantic_search_relevance():
    """Verify that semantic search returns highly relevant results for known domains."""
    queries = {
        "théâtre": 0.70,
        "jazz": 0.70,
        "exposition": 0.70,
        "sport": 0.70
    }
    
    with EventVectorStore() as vector_store:
        try:
            vector_store.load_index()
        except FileNotFoundError:
            pytest.skip("FAISS index not found. Run ingestion and index building first.")
            
        for query, min_score in queries.items():
            results = vector_store.search(query, k=1)
            assert len(results) > 0, f"No results for query: {query}"
            score = results[0][1]
            assert score >= min_score, f"Similarity score {score:.4f} for '{query}' is below threshold {min_score}"

@pytest.mark.performance
def test_search_latency_requirement():
    """Verify that search latency is within SLA (< 2 seconds)."""
    query = "concert de jazz à Paris"
    
    with EventVectorStore() as vector_store:
        try:
            vector_store.load_index()
        except FileNotFoundError:
            pytest.skip("FAISS index not found.")
            
        start_time = time.time()
        vector_store.search(query, k=5)
        latency = time.time() - start_time
        
        assert latency < 2.0, f"Search latency {latency:.2f}s exceeded 2s SLA"

@pytest.mark.integration
def test_vector_store_completeness():
    """Verify the vector store contains the expected 1000 events."""
    with EventVectorStore() as vector_store:
        try:
            vector_store.load_index()
        except FileNotFoundError:
            pytest.skip("FAISS index not found.")
            
        assert len(vector_store.event_ids) >= 1000
        assert vector_store.index.ntotal >= 1000
