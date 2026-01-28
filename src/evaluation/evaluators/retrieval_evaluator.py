"""Retrieval evaluation component.

Evaluates retrieval quality against golden dataset using retrieval metrics.
Uses the PRODUCTION retrieval path (RetrievalManager) for accurate metrics.
"""

import logging
import time
from typing import Any

from src.evaluation.metrics.retrieval import RetrievalMetrics
from src.evaluation.datasets.golden_dataset import GoldenDataset, Query
from src.retrieval.manager import RetrievalManager

logger = logging.getLogger(__name__)


class RetrievalEvaluator:
    """Evaluate retrieval performance against golden dataset.

    Uses RetrievalManager (the production retrieval path) to ensure
    evaluation metrics reflect actual system behavior.
    """

    def __init__(self, retrieval_manager: RetrievalManager):
        """Initialize retrieval evaluator.

        Args:
            retrieval_manager: RetrievalManager instance (production retrieval)
        """
        self.retrieval_manager = retrieval_manager
        self.metrics = RetrievalMetrics()
        logger.info("Initialized RetrievalEvaluator with production RetrievalManager")

    def evaluate_query(
        self,
        query: Query,
        k: int = 5
    ) -> dict[str, Any]:
        """Evaluate retrieval for a single query.

        Args:
            query: Query from golden dataset
            k: Number of documents to retrieve

        Returns:
            Dictionary with retrieval metrics and metadata
        """
        # Extract relevant event IDs from ground truth
        relevant_ids = [gt.event_id for gt in query.relevance_ground_truth]

        # Measure latency
        start_time = time.time()

        try:
            # Parse filters into SearchIntent (same as production)
            raw_filters = query.expected_filters or {}
            intent = self.retrieval_manager.parse_intent(raw_filters)

            # Execute multi-stage search (same as production)
            result = self.retrieval_manager.execute_search(query.query, intent)

            latency_ms = (time.time() - start_time) * 1000

            # Extract retrieved event IDs from documents
            retrieved_ids = []
            for doc in result["docs"][:k]:  # Respect k limit
                event_id = doc.metadata.get("event_id", "")
                if event_id:
                    retrieved_ids.append(event_id)

            # Calculate metrics
            metrics_result = {
                "query_id": query.id,
                "query": query.query,
                "query_type": query.query_type,
                "retrieved_count": len(retrieved_ids),
                "relevant_count": len(relevant_ids),
                "latency_ms": latency_ms,
                "exact_matches": result.get("exact_count", 0),
                "total_in_database": result.get("total_in_database", 0),
            }

            # Add retrieval metrics if we have ground truth
            if relevant_ids:
                metrics_result.update({
                    "hit_rate": self.metrics.hit_rate(retrieved_ids, relevant_ids),
                    "mrr": self.metrics.mean_reciprocal_rank(retrieved_ids, relevant_ids),
                    f"precision@{k}": self.metrics.precision_at_k(retrieved_ids, relevant_ids, k),
                    f"recall@{k}": self.metrics.recall_at_k(retrieved_ids, relevant_ids, k),
                    f"f1@{k}": self.metrics.f1_score(retrieved_ids, relevant_ids, k),
                })
            else:
                # No ground truth, just track that retrieval succeeded
                metrics_result.update({
                    "hit_rate": None,
                    "mrr": None,
                    f"precision@{k}": None,
                    f"recall@{k}": None,
                    f"f1@{k}": None,
                })

            logger.debug(
                f"Query {query.id}: retrieved={len(retrieved_ids)}, "
                f"latency={latency_ms:.0f}ms, "
                f"hit_rate={metrics_result.get('hit_rate', 'N/A')}"
            )

            return metrics_result

        except Exception as e:
            logger.error(f"Retrieval evaluation failed for query {query.id}: {e}")
            return {
                "query_id": query.id,
                "query": query.query,
                "query_type": query.query_type,
                "error": str(e),
                "latency_ms": (time.time() - start_time) * 1000,
            }

    def evaluate_dataset(
        self,
        golden_dataset: GoldenDataset,
        k: int = 5
    ) -> dict[str, Any]:
        """Evaluate retrieval across entire golden dataset.

        Args:
            golden_dataset: GoldenDataset to evaluate against
            k: Number of documents to retrieve per query

        Returns:
            Dictionary with aggregated metrics and per-query results
        """
        logger.info(f"Starting retrieval evaluation on {golden_dataset.total_queries} queries")

        per_query_results = []
        total_latency = 0.0
        hit_rates = []
        mrrs = []
        precisions = []
        recalls = []
        f1s = []

        for i, query in enumerate(golden_dataset.queries, 1):
            logger.debug(f"Evaluating query {i}/{golden_dataset.total_queries}: {query.id}")

            result = self.evaluate_query(query, k=k)
            per_query_results.append(result)

            # Accumulate metrics
            if "error" not in result:
                total_latency += result["latency_ms"]

                if result.get("hit_rate") is not None:
                    hit_rates.append(result["hit_rate"])
                if result.get("mrr") is not None:
                    mrrs.append(result["mrr"])
                if result.get(f"precision@{k}") is not None:
                    precisions.append(result[f"precision@{k}"])
                if result.get(f"recall@{k}") is not None:
                    recalls.append(result[f"recall@{k}"])
                if result.get(f"f1@{k}") is not None:
                    f1s.append(result[f"f1@{k}"])

        # Calculate aggregated metrics
        num_successful = len([r for r in per_query_results if "error" not in r])
        num_with_ground_truth = len(hit_rates)

        aggregated = {
            "total_queries": golden_dataset.total_queries,
            "successful_queries": num_successful,
            "queries_with_ground_truth": num_with_ground_truth,
            "avg_latency_ms": total_latency / num_successful if num_successful > 0 else 0,
        }

        # Add metric averages if we have ground truth
        if num_with_ground_truth > 0:
            aggregated.update({
                "overall_hit_rate": sum(hit_rates) / len(hit_rates),
                "overall_mrr": sum(mrrs) / len(mrrs),
                f"overall_precision@{k}": sum(precisions) / len(precisions),
                f"overall_recall@{k}": sum(recalls) / len(recalls),
                f"overall_f1@{k}": sum(f1s) / len(f1s),
            })
        else:
            aggregated.update({
                "overall_hit_rate": None,
                "overall_mrr": None,
                f"overall_precision@{k}": None,
                f"overall_recall@{k}": None,
                f"overall_f1@{k}": None,
            })

        logger.info(
            f"Retrieval evaluation complete: "
            f"hit_rate={aggregated.get('overall_hit_rate', 'N/A')}, "
            f"avg_latency={aggregated['avg_latency_ms']:.0f}ms"
        )

        return {
            "aggregated_metrics": aggregated,
            "per_query_results": per_query_results
        }
