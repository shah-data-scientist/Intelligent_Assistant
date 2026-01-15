"""Test hybrid search with metadata extraction."""

import logging
import uuid
from src.retrieval.chain import RAGChain

logging.basicConfig(level=logging.INFO)

def test_feb_query():
    print("Initializing RAGChain...")
    chain = RAGChain()
    
    question = "Events in February 2026"
    session_id = str(uuid.uuid4())
    print(f"\nQuerying: {question} (Session: {session_id})")
    
    # We use query_with_metadata to inspect sources
    result = chain.query_with_metadata(question, session_id=session_id)
    
    print("\nAnswer:")
    print(result["answer"])
    
    print("\nSources:")
    for src in result["sources"]:
        print(f"- {src['title']} ({src['date']}) - {src['city']}")

if __name__ == "__main__":
    test_feb_query()

