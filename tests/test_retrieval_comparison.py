"""Compare retrieval evaluator vs RAG chain retrieval."""

import logging
from src.evaluation.datasets.golden_dataset import GoldenDataset
from src.retrieval.retriever import EventRetriever
from src.models.vector_store import EventVectorStore
from src.retrieval.chain import RAGChain

logging.basicConfig(level=logging.INFO, format='%(name)s - %(message)s')

# Load first query (Q001 - jazz concerts)
dataset = GoldenDataset.load("data/evaluation/golden_dataset.json")
query = dataset.queries[0]

print(f"Query: {query.query}")
print(f"Ground truth event IDs: {[gt.event_id for gt in query.relevance_ground_truth]}")
print(f"Expected filters: {query.expected_filters}")
print()

# Test 1: Direct retrieval (what evaluation uses)
print("="*80)
print("Test 1: Retrieval Evaluator Method (search_with_filters)")
print("="*80)
vector_store = EventVectorStore()
vector_store.load_index()
retriever = EventRetriever(vector_store=vector_store, k=5)

docs = retriever.search_with_filters(
    query=query.query,
    k=5,
    metadata_filter=query.expected_filters or None
)

print(f"Retrieved {len(docs)} documents:")
for i, doc in enumerate(docs, 1):
    event_id = doc.metadata.get("event_id", "unknown")
    title = doc.metadata.get("title", "unknown")
    score = doc.metadata.get("score", 0.0)
    print(f"{i}. Event ID: {event_id} - {title} (score: {score:.3f})")

retrieved_ids = [doc.metadata.get("event_id", "") for doc in docs]
ground_truth_ids = set([gt.event_id for gt in query.relevance_ground_truth])

# Check hit rate
hit = any(rid in ground_truth_ids for rid in retrieved_ids)
print(f"\nHit Rate: {'1.0 (HIT!)' if hit else '0.0 (MISS)'}")
print(f"Matching IDs: {[rid for rid in retrieved_ids if rid in ground_truth_ids]}")
print()

# Test 2: RAG Chain method (with query refinement)
print("="*80)
print("Test 2: RAG Chain Method (with query refinement + metadata extraction)")
print("="*80)

chain = RAGChain(k=5)
result = chain.query_with_metadata(query.query, session_id="comparison_test")
sources = result["sources"]

print(f"Retrieved {len(sources)} documents:")
for i, source in enumerate(sources, 1):
    # Note: sources don't include event_id in the API response schema, only title/city/etc
    print(f"{i}. Title: {source['title']} in {source['city']} (score: {source.get('score', 0):.3f})")

print("\nNote: RAG chain query_with_metadata doesn't expose event_ids in sources!")
print("This might be why retrieval metrics fail even when generation works.")
