"""Retrieval evaluation with Precision/Recall metrics.

This script:
1. Loads the golden dataset with expected filters
2. Queries the database to find ground truth events matching those filters
3. Runs retrieval queries via the RAG system
4. Calculates Precision@k, Recall@k, Hit Rate, MRR, F1@k
"""

import json
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.data.storage import EventStorage
from src.models.vector_store import EventVectorStore
from src.evaluation.metrics.retrieval import RetrievalMetrics


# Suppress verbose logging
import logging

logging.getLogger("src.models.embeddings").setLevel(logging.WARNING)
logging.getLogger("src.models.vector_store").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)


def load_golden_dataset(path: str = "evaluation/golden_dataset.json") -> dict:
    """Load the golden dataset."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_ground_truth_events(storage: EventStorage, expected_filters: dict, limit: int = 50) -> list[str]:
    """Query database to find events matching expected filters.

    This creates the ground truth by finding all events that match
    the expected filters for a query.
    """
    from sqlalchemy import select, and_, or_, extract
    from src.data.storage import EventRecord

    session = storage.SessionLocal()
    try:
        query = select(EventRecord.event_id)
        conditions = []

        # City filter
        if "city" in expected_filters:
            city = expected_filters["city"]
            conditions.append(EventRecord.city.ilike(f"%{city}%"))

        # Category filter - map to actual categories in DB
        if "category" in expected_filters:
            cat = expected_filters["category"]
            # Handle category mapping
            if cat == "Musique":
                conditions.append(EventRecord.category.ilike("%Musique%"))
            elif cat == "Art / Exposition":
                conditions.append(or_(EventRecord.category.ilike("%Exposition%"), EventRecord.category.ilike("%Art%")))
            elif cat == "Théâtre / Spectacle":
                conditions.append(
                    or_(EventRecord.category.ilike("%Théâtre%"), EventRecord.category.ilike("%Spectacle%"))
                )
            elif cat == "Jeune public":
                conditions.append(
                    or_(
                        EventRecord.category.ilike("%Jeune%"),
                        EventRecord.category.ilike("%Enfant%"),
                        EventRecord.category.ilike("%Famille%"),
                    )
                )
            else:
                conditions.append(EventRecord.category.ilike(f"%{cat}%"))

        # Month filter
        if "month" in expected_filters:
            month = expected_filters["month"]
            conditions.append(extract("month", EventRecord.start_date) == month)

        # Free events filter
        if expected_filters.get("is_free"):
            conditions.append(
                or_(
                    EventRecord.price_label.ilike("%gratuit%"),
                    EventRecord.price_label.ilike("%free%"),
                    EventRecord.price_label == "Gratuit",
                )
            )

        if conditions:
            query = query.where(and_(*conditions))

        query = query.limit(limit)
        result = session.execute(query)
        event_ids = [row[0] for row in result]
        return event_ids
    finally:
        session.close()


def run_retrieval_query(vector_store: EventVectorStore, query: str, k: int = 10) -> list[str]:
    """Run a retrieval query and return event IDs."""
    # Search vector store (returns list of (Event, score) tuples)
    results = vector_store.search(query, k=k)

    # Extract event IDs
    event_ids = [event.event_id for event, score in results]
    return event_ids


def evaluate_single_query(query_data: dict, vector_store: EventVectorStore, storage: EventStorage, k: int = 10) -> dict:
    """Evaluate a single query."""
    query = query_data.get("query", "")
    expected_filters = query_data.get("expected_filters", {})
    query_id = query_data.get("turn_id", query_data.get("query_id", "unknown"))

    # Skip if no expected filters (can't determine ground truth)
    if not expected_filters:
        return {"query_id": query_id, "query": query, "skipped": True, "reason": "No expected filters defined"}

    # Get ground truth events from database
    ground_truth_ids = get_ground_truth_events(storage, expected_filters)

    if not ground_truth_ids:
        return {
            "query_id": query_id,
            "query": query,
            "skipped": True,
            "reason": f"No events found matching filters: {expected_filters}",
        }

    # Run retrieval
    retrieved_ids = run_retrieval_query(vector_store, query, k=k)

    # Calculate metrics
    metrics = RetrievalMetrics.evaluate_retrieval(retrieved_ids=retrieved_ids, relevant_ids=ground_truth_ids, k=k)

    return {
        "query_id": query_id,
        "query": query,
        "expected_filters": expected_filters,
        "ground_truth_count": len(ground_truth_ids),
        "retrieved_count": len(retrieved_ids),
        "ground_truth_sample": ground_truth_ids[:5],
        "retrieved_sample": retrieved_ids[:5],
        "metrics": metrics,
        "skipped": False,
    }


def extract_queries_from_golden_dataset(golden_data: dict) -> list[dict]:
    """Extract all queries from conversations and single_queries."""
    queries = []

    # Extract from conversations
    for conv in golden_data.get("conversations", []):
        for turn in conv.get("turns", []):
            queries.append(
                {
                    "turn_id": turn.get("turn_id"),
                    "query": turn.get("query"),
                    "expected_filters": turn.get("expected_filters", {}),
                    "query_type": turn.get("turn_type"),
                    "language": conv.get("language", "fr"),
                }
            )

    # Extract from single_queries if present
    for query in golden_data.get("single_queries", []):
        queries.append(
            {
                "query_id": query.get("query_id"),
                "query": query.get("query"),
                "expected_filters": query.get("expected_filters", {}),
                "query_type": "single",
                "language": query.get("language", "fr"),
            }
        )

    return queries


def main():
    """Run retrieval evaluation."""
    print("=" * 70)
    print("RETRIEVAL EVALUATION WITH PRECISION/RECALL")
    print("=" * 70)

    # Configuration
    k = 10  # Top-k for metrics

    # Initialize components
    print("\nInitializing components...")
    storage = EventStorage()

    # Check if vector store exists
    faiss_path = Path("data/faiss_index/index.faiss")
    if not faiss_path.exists():
        print("ERROR: FAISS index not found. Please run ingestion first.")
        sys.exit(1)

    vector_store = EventVectorStore()
    vector_store.load_index()

    print(f"  - Database: {storage.db_path}")
    print(f"  - Vector store loaded with {vector_store.index.ntotal if vector_store.index else 0} vectors")

    # Load golden dataset
    print("\nLoading golden dataset...")
    golden_data = load_golden_dataset()
    queries = extract_queries_from_golden_dataset(golden_data)
    print(f"  - Found {len(queries)} queries to evaluate")

    # Filter queries with expected_filters
    queries_with_filters = [q for q in queries if q.get("expected_filters")]
    print(f"  - {len(queries_with_filters)} queries have expected_filters (can evaluate)")

    # Run evaluation
    print(f"\nRunning evaluation (k={k})...")
    print("-" * 70)

    results = []
    metrics_sum = {"hit_rate": 0.0, "mrr": 0.0, f"precision@{k}": 0.0, f"recall@{k}": 0.0, f"f1@{k}": 0.0}
    evaluated_count = 0

    for i, query_data in enumerate(queries_with_filters):
        print(
            f"\n[{i+1}/{len(queries_with_filters)}] {query_data.get('turn_id', query_data.get('query_id', 'unknown'))}"
        )
        print(f"  Query: {query_data['query'][:60]}...")
        print(f"  Filters: {query_data.get('expected_filters', {})}")

        result = evaluate_single_query(query_data, vector_store, storage, k=k)
        results.append(result)

        if not result.get("skipped"):
            evaluated_count += 1
            for metric_name, metric_value in result["metrics"].items():
                if metric_name in metrics_sum:
                    metrics_sum[metric_name] += metric_value

            print(f"  Ground truth: {result['ground_truth_count']} events")
            print(f"  Retrieved: {result['retrieved_count']} events")
            print(f"  Hit Rate: {result['metrics']['hit_rate']:.2f}")
            print(f"  Precision@{k}: {result['metrics'][f'precision@{k}']:.2%}")
            print(f"  Recall@{k}: {result['metrics'][f'recall@{k}']:.2%}")
        else:
            print(f"  SKIPPED: {result.get('reason', 'Unknown')}")

    # Calculate averages
    print("\n" + "=" * 70)
    print("AGGREGATE RESULTS")
    print("=" * 70)

    if evaluated_count > 0:
        avg_metrics = {k: v / evaluated_count for k, v in metrics_sum.items()}

        print(f"\nQueries evaluated: {evaluated_count} / {len(queries_with_filters)}")
        print(f"\nAverage Retrieval Metrics (k={k}):")
        print(f"  - Hit Rate:      {avg_metrics['hit_rate']:.2%}")
        print(f"  - MRR:           {avg_metrics['mrr']:.2%}")
        print(f"  - Precision@{k}:  {avg_metrics[f'precision@{k}']:.2%}")
        print(f"  - Recall@{k}:     {avg_metrics[f'recall@{k}']:.2%}")
        print(f"  - F1@{k}:         {avg_metrics[f'f1@{k}']:.2%}")
    else:
        avg_metrics = {}
        print("\nNo queries could be evaluated.")

    # Save results
    report = {
        "timestamp": datetime.now().isoformat(),
        "k": k,
        "total_queries": len(queries),
        "queries_with_filters": len(queries_with_filters),
        "queries_evaluated": evaluated_count,
        "average_metrics": avg_metrics,
        "detailed_results": results,
    }

    report_path = Path("evaluation/reports") / f"retrieval_evaluation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"\nReport saved to: {report_path}")

    return report


if __name__ == "__main__":
    main()
