"""Retrieval evaluation metrics.

This module provides standard retrieval metrics for evaluating search quality:
- Hit Rate: Whether at least one relevant document was retrieved
- MRR (Mean Reciprocal Rank): Rank of first relevant document
- Precision@k: Fraction of retrieved documents that are relevant
- Recall@k: Fraction of relevant documents that were retrieved
- NDCG@k: Normalized Discounted Cumulative Gain (graded relevance)
"""

import math
from typing import Any


class RetrievalMetrics:
    """Compute retrieval-specific metrics."""

    @staticmethod
    def hit_rate(retrieved_ids: list[str], relevant_ids: list[str]) -> float:
        """Calculate Hit Rate@k: Did we retrieve at least one relevant document?

        Args:
            retrieved_ids: List of retrieved document IDs (in rank order)
            relevant_ids: List of relevant document IDs (ground truth)

        Returns:
            1.0 if at least one relevant doc was retrieved, 0.0 otherwise

        Example:
            >>> RetrievalMetrics.hit_rate(["doc1", "doc2", "doc3"], ["doc2", "doc5"])
            1.0  # doc2 is present
            >>> RetrievalMetrics.hit_rate(["doc1", "doc3"], ["doc2", "doc5"])
            0.0  # no relevant docs retrieved
        """
        if not relevant_ids:
            return 0.0

        relevant_set = set(relevant_ids)
        for doc_id in retrieved_ids:
            if doc_id in relevant_set:
                return 1.0
        return 0.0

    @staticmethod
    def mean_reciprocal_rank(retrieved_ids: list[str], relevant_ids: list[str]) -> float:
        """Calculate Mean Reciprocal Rank (MRR): 1/rank of first relevant document.

        MRR rewards relevant results at top positions. Perfect score is 1.0
        (relevant doc at rank 1), lower scores indicate relevant docs appear later.

        Args:
            retrieved_ids: List of retrieved document IDs (in rank order)
            relevant_ids: List of relevant document IDs (ground truth)

        Returns:
            1/rank of first relevant document, or 0.0 if none found

        Example:
            >>> RetrievalMetrics.mean_reciprocal_rank(["doc1", "doc2", "doc3"], ["doc2"])
            0.5  # doc2 is at position 2, so 1/2 = 0.5
            >>> RetrievalMetrics.mean_reciprocal_rank(["doc2", "doc1"], ["doc2"])
            1.0  # doc2 is at position 1, so 1/1 = 1.0
        """
        if not relevant_ids:
            return 0.0

        relevant_set = set(relevant_ids)
        for rank, doc_id in enumerate(retrieved_ids, start=1):
            if doc_id in relevant_set:
                return 1.0 / rank
        return 0.0

    @staticmethod
    def precision_at_k(retrieved_ids: list[str], relevant_ids: list[str], k: int = 5) -> float:
        """Calculate Precision@k: Fraction of top-k retrieved docs that are relevant.

        Precision measures the noise in search results. High precision means
        most retrieved documents are relevant.

        Args:
            retrieved_ids: List of retrieved document IDs (in rank order)
            relevant_ids: List of relevant document IDs (ground truth)
            k: Number of top documents to consider

        Returns:
            Fraction of top-k docs that are relevant (0.0 to 1.0)

        Example:
            >>> RetrievalMetrics.precision_at_k(["doc1", "doc2", "doc3", "doc4", "doc5"], ["doc2", "doc4"], k=5)
            0.4  # 2 out of 5 are relevant
            >>> RetrievalMetrics.precision_at_k(["doc2", "doc4", "doc1"], ["doc2", "doc4"], k=3)
            0.667  # 2 out of 3 are relevant
        """
        if not relevant_ids or not retrieved_ids:
            return 0.0

        relevant_set = set(relevant_ids)
        top_k = retrieved_ids[:k]

        if not top_k:
            return 0.0

        relevant_count = sum(1 for doc_id in top_k if doc_id in relevant_set)
        return relevant_count / len(top_k)

    @staticmethod
    def recall_at_k(retrieved_ids: list[str], relevant_ids: list[str], k: int = 5) -> float:
        """Calculate Recall@k: Fraction of relevant docs that were retrieved in top-k.

        Recall measures coverage. High recall means most relevant documents
        were found in the search results.

        Args:
            retrieved_ids: List of retrieved document IDs (in rank order)
            relevant_ids: List of relevant document IDs (ground truth)
            k: Number of top documents to consider

        Returns:
            Fraction of relevant docs retrieved (0.0 to 1.0)

        Example:
            >>> RetrievalMetrics.recall_at_k(["doc1", "doc2", "doc3"], ["doc2", "doc4", "doc5"], k=5)
            0.333  # 1 out of 3 relevant docs retrieved
            >>> RetrievalMetrics.recall_at_k(["doc2", "doc4", "doc5"], ["doc2", "doc4", "doc5"], k=3)
            1.0  # All relevant docs retrieved
        """
        if not relevant_ids:
            return 0.0

        relevant_set = set(relevant_ids)
        top_k = retrieved_ids[:k]

        if not top_k:
            return 0.0

        retrieved_relevant = sum(1 for doc_id in top_k if doc_id in relevant_set)
        return retrieved_relevant / len(relevant_set)

    @staticmethod
    def ndcg_at_k(
        retrieved_ids: list[str],
        relevance_scores: dict[str, float],
        k: int = 5
    ) -> float:
        """Calculate Normalized Discounted Cumulative Gain (NDCG@k).

        NDCG supports graded relevance (not just binary relevant/irrelevant).
        It measures both relevance and ranking quality, with logarithmic
        discounting for lower-ranked results.

        Args:
            retrieved_ids: List of retrieved document IDs (in rank order)
            relevance_scores: Dict mapping doc_id to relevance score (0.0 to 1.0)
            k: Number of top documents to consider

        Returns:
            NDCG score (0.0 to 1.0), where 1.0 is perfect ranking

        Example:
            >>> scores = {"doc1": 0.5, "doc2": 1.0, "doc3": 0.0, "doc4": 0.8}
            >>> RetrievalMetrics.ndcg_at_k(["doc2", "doc4", "doc1"], scores, k=3)
            0.957  # Near-perfect ranking (most relevant docs at top)
        """
        if not retrieved_ids or not relevance_scores:
            return 0.0

        def dcg(doc_ids: list[str], scores: dict[str, float], k_val: int) -> float:
            """Calculate Discounted Cumulative Gain."""
            gain = 0.0
            for rank, doc_id in enumerate(doc_ids[:k_val], start=1):
                relevance = scores.get(doc_id, 0.0)
                # DCG formula: rel / log2(rank + 1)
                gain += relevance / math.log2(rank + 1)
            return gain

        # DCG of retrieved results
        dcg_val = dcg(retrieved_ids, relevance_scores, k)

        # Ideal DCG (best possible ranking)
        ideal_ranking = sorted(
            relevance_scores.keys(),
            key=lambda doc_id: relevance_scores[doc_id],
            reverse=True
        )
        idcg_val = dcg(ideal_ranking, relevance_scores, k)

        if idcg_val == 0.0:
            return 0.0

        return dcg_val / idcg_val

    @staticmethod
    def f1_score(retrieved_ids: list[str], relevant_ids: list[str], k: int = 5) -> float:
        """Calculate F1 score: Harmonic mean of precision and recall.

        F1 provides a single metric balancing precision and recall.

        Args:
            retrieved_ids: List of retrieved document IDs (in rank order)
            relevant_ids: List of relevant document IDs (ground truth)
            k: Number of top documents to consider

        Returns:
            F1 score (0.0 to 1.0)

        Example:
            >>> RetrievalMetrics.f1_score(["doc1", "doc2", "doc3"], ["doc2", "doc4"], k=3)
            0.5  # Precision=0.33, Recall=0.5, F1=0.4
        """
        precision = RetrievalMetrics.precision_at_k(retrieved_ids, relevant_ids, k)
        recall = RetrievalMetrics.recall_at_k(retrieved_ids, relevant_ids, k)

        if precision + recall == 0.0:
            return 0.0

        return 2 * (precision * recall) / (precision + recall)

    @staticmethod
    def evaluate_retrieval(
        retrieved_ids: list[str],
        relevant_ids: list[str],
        relevance_scores: dict[str, float] | None = None,
        k: int = 5
    ) -> dict[str, float]:
        """Calculate all retrieval metrics at once.

        Convenience method to compute all metrics in a single call.

        Args:
            retrieved_ids: List of retrieved document IDs (in rank order)
            relevant_ids: List of relevant document IDs (ground truth)
            relevance_scores: Optional graded relevance scores for NDCG
            k: Number of top documents to consider

        Returns:
            Dictionary with all metric scores

        Example:
            >>> metrics = RetrievalMetrics.evaluate_retrieval(
            ...     ["doc1", "doc2", "doc3"],
            ...     ["doc2", "doc4"],
            ...     {"doc1": 0.0, "doc2": 1.0, "doc3": 0.5, "doc4": 0.8},
            ...     k=3
            ... )
            >>> metrics["hit_rate"]
            1.0
        """
        results = {
            "hit_rate": RetrievalMetrics.hit_rate(retrieved_ids, relevant_ids),
            "mrr": RetrievalMetrics.mean_reciprocal_rank(retrieved_ids, relevant_ids),
            f"precision@{k}": RetrievalMetrics.precision_at_k(retrieved_ids, relevant_ids, k),
            f"recall@{k}": RetrievalMetrics.recall_at_k(retrieved_ids, relevant_ids, k),
            f"f1@{k}": RetrievalMetrics.f1_score(retrieved_ids, relevant_ids, k),
        }

        # Add NDCG if relevance scores provided
        if relevance_scores is not None:
            results[f"ndcg@{k}"] = RetrievalMetrics.ndcg_at_k(retrieved_ids, relevance_scores, k)

        return results
