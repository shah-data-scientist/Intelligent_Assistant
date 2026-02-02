"""Debug Q001 retrieval to understand hit rate issue."""

from src.evaluation.datasets.golden_dataset import GoldenDataset
from src.retrieval.retriever import EventRetriever
from src.models.vector_store import EventVectorStore

# Load Q001
dataset = GoldenDataset.load("data/evaluation/golden_dataset.json")
q001 = dataset.queries[0]

print("=" * 80)
print("Q001 Ground Truth")
print("=" * 80)
print(f"Query: {q001.query}")
print(f"Expected filters: {q001.expected_filters}")
print("Ground truth event IDs:")
for gt in q001.relevance_ground_truth:
    print(f"  - {gt.event_id} (score: {gt.relevance_score})")
print()

# Initialize retriever (same way as retrieval evaluator)
vector_store = EventVectorStore()
vector_store.load_index()
retriever = EventRetriever(vector_store=vector_store, k=5)

# Perform retrieval (same way as retrieval evaluator)
print("=" * 80)
print("Retrieval Evaluator Method")
print("=" * 80)
docs = retriever.search_with_filters(query=q001.query, k=5, metadata_filter=q001.expected_filters or None)

print(f"Retrieved {len(docs)} documents:")
for i, doc in enumerate(docs, 1):
    event_id = doc.metadata.get("event_id", "unknown")
    title = doc.metadata.get("title", "unknown")
    city = doc.metadata.get("city", "unknown")
    score = doc.metadata.get("score", 0.0)
    print(f"{i}. Event ID: {event_id}")
    print(f"   Title: {title}")
    print(f"   City: {city}")
    print(f"   Score: {score:.3f}")
    print()

# Check hit rate manually
retrieved_ids = [doc.metadata.get("event_id", "") for doc in docs]
ground_truth_ids = set([gt.event_id for gt in q001.relevance_ground_truth])

print("=" * 80)
print("Hit Rate Analysis")
print("=" * 80)
print(f"Retrieved IDs: {retrieved_ids}")
print(f"Ground truth IDs: {list(ground_truth_ids)}")

matches = [rid for rid in retrieved_ids if rid in ground_truth_ids]
print(f"Matching IDs: {matches}")
print(f"Hit Rate: {'1.0 (HIT!)' if matches else '0.0 (MISS)'}")

if not matches:
    print("\nWhy no match? Possible reasons:")
    print("1. Query semantic mismatch (needs query refinement)")
    print("2. Filters too strict (city/month filtering out ground truth events)")
    print("3. Ground truth events not in top 5")
    print("4. Event IDs don't match between ground truth and database")
