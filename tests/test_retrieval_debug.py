"""Debug script to test retrieval pipeline."""

import logging
from src.models.vector_store import EventVectorStore
from src.retrieval.retriever import EventRetriever
from src.retrieval.chain import RAGChain

logging.basicConfig(level=logging.INFO, format='%(name)s - %(levelname)s - %(message)s')

# Test query from evaluation
query = "Concerts de jazz à Paris en février"

print(f"\n{'='*80}")
print(f"Testing Query: {query}")
print(f"{'='*80}\n")

# Test 1: Direct FAISS search (no filters)
print("Test 1: Direct FAISS search (no metadata filters)")
print("-" * 80)
vector_store = EventVectorStore()
vector_store.load_index()
results = vector_store.search(query, k=5)
print(f"Results: {len(results)} events found")
for i, (event, score) in enumerate(results, 1):
    print(f"{i}. {event.title} ({event.category}) - Score: {score:.3f}")
    if event.location and event.location.city:
        print(f"   City: {event.location.city}")
    if event.start_date:
        print(f"   Date: {event.start_date.strftime('%Y-%m-%d')}")
print()

# Test 2: FAISS search with filters
print("Test 2: FAISS search with metadata filters")
print("-" * 80)
filters = {"city": "Paris", "month": 2}
results_filtered = vector_store.search(query, k=5, metadata_filter=filters)
print(f"Results with filters {filters}: {len(results_filtered)} events found")
for i, (event, score) in enumerate(results_filtered, 1):
    print(f"{i}. {event.title} ({event.category}) - Score: {score:.3f}")
    if event.location and event.location.city:
        print(f"   City: {event.location.city}")
    if event.start_date:
        print(f"   Date: {event.start_date.strftime('%Y-%m-%d')}")
print()

# Test 3: Through RAGChain (with query refinement and metadata extraction)
print("Test 3: Full RAG pipeline with query refinement")
print("-" * 80)
chain = RAGChain()

# Test the refinement chain
refined_query = chain.refinement_chain.invoke({"question": query})
print(f"Original query: {query}")
print(f"Refined query:  {refined_query}")

# Test metadata extraction
metadata = chain.extraction_chain.invoke({"question": refined_query})
print(f"Extracted metadata: {metadata}")

# Test full query
print("\nRunning full query...")
result = chain.query(query, session_id="debug_session")
print(f"\nAnswer:\n{result}")
print()
