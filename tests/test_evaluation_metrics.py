"""Unit tests for evaluation metrics."""

import pytest
from src.evaluation.metrics.retrieval import RetrievalMetrics


class TestHitRate:
    """Test Hit Rate metric calculation."""

    def test_hit_rate_with_relevant_doc(self):
        """Test Hit Rate when relevant document is retrieved."""
        retrieved = ["evt_1", "evt_2", "evt_3"]
        relevant = ["evt_2", "evt_5"]

        hr = RetrievalMetrics.hit_rate(retrieved, relevant)
        assert hr == 1.0  # evt_2 is present

    def test_hit_rate_without_relevant_doc(self):
        """Test Hit Rate when no relevant documents retrieved."""
        retrieved = ["evt_1", "evt_3", "evt_4"]
        relevant = ["evt_2", "evt_5"]

        hr = RetrievalMetrics.hit_rate(retrieved, relevant)
        assert hr == 0.0  # No relevant docs

    def test_hit_rate_empty_retrieved(self):
        """Test Hit Rate with empty retrieved list."""
        hr = RetrievalMetrics.hit_rate([], ["evt_1", "evt_2"])
        assert hr == 0.0

    def test_hit_rate_empty_relevant(self):
        """Test Hit Rate with empty relevant list."""
        hr = RetrievalMetrics.hit_rate(["evt_1", "evt_2"], [])
        assert hr == 0.0

    def test_hit_rate_all_relevant(self):
        """Test Hit Rate when all retrieved docs are relevant."""
        retrieved = ["evt_1", "evt_2", "evt_3"]
        relevant = ["evt_1", "evt_2", "evt_3", "evt_4"]

        hr = RetrievalMetrics.hit_rate(retrieved, relevant)
        assert hr == 1.0


class TestMeanReciprocalRank:
    """Test Mean Reciprocal Rank (MRR) calculation."""

    def test_mrr_first_position(self):
        """Test MRR when relevant doc is at position 1."""
        retrieved = ["evt_2", "evt_1", "evt_3"]
        relevant = ["evt_2"]

        mrr = RetrievalMetrics.mean_reciprocal_rank(retrieved, relevant)
        assert mrr == 1.0  # 1/1

    def test_mrr_second_position(self):
        """Test MRR when relevant doc is at position 2."""
        retrieved = ["evt_1", "evt_2", "evt_3"]
        relevant = ["evt_2"]

        mrr = RetrievalMetrics.mean_reciprocal_rank(retrieved, relevant)
        assert mrr == 0.5  # 1/2

    def test_mrr_third_position(self):
        """Test MRR when relevant doc is at position 3."""
        retrieved = ["evt_1", "evt_3", "evt_2"]
        relevant = ["evt_2"]

        mrr = RetrievalMetrics.mean_reciprocal_rank(retrieved, relevant)
        assert mrr == pytest.approx(0.333, rel=0.01)  # 1/3

    def test_mrr_no_relevant(self):
        """Test MRR when no relevant documents retrieved."""
        retrieved = ["evt_1", "evt_3", "evt_4"]
        relevant = ["evt_2", "evt_5"]

        mrr = RetrievalMetrics.mean_reciprocal_rank(retrieved, relevant)
        assert mrr == 0.0

    def test_mrr_multiple_relevant(self):
        """Test MRR with multiple relevant docs (uses first match)."""
        retrieved = ["evt_1", "evt_2", "evt_3"]
        relevant = ["evt_2", "evt_3"]

        mrr = RetrievalMetrics.mean_reciprocal_rank(retrieved, relevant)
        assert mrr == 0.5  # First relevant is at position 2

    def test_mrr_empty_lists(self):
        """Test MRR with empty lists."""
        assert RetrievalMetrics.mean_reciprocal_rank([], ["evt_1"]) == 0.0
        assert RetrievalMetrics.mean_reciprocal_rank(["evt_1"], []) == 0.0


class TestPrecisionAtK:
    """Test Precision@k metric calculation."""

    def test_precision_at_k_basic(self):
        """Test basic Precision@k calculation."""
        retrieved = ["evt_1", "evt_2", "evt_3", "evt_4", "evt_5"]
        relevant = ["evt_2", "evt_4"]

        precision = RetrievalMetrics.precision_at_k(retrieved, relevant, k=5)
        assert precision == 0.4  # 2 out of 5

    def test_precision_at_k_perfect(self):
        """Test Precision@k with perfect results."""
        retrieved = ["evt_2", "evt_4", "evt_1"]
        relevant = ["evt_2", "evt_4"]

        precision = RetrievalMetrics.precision_at_k(retrieved, relevant, k=3)
        assert precision == pytest.approx(0.667, rel=0.01)  # 2 out of 3

    def test_precision_at_k_zero(self):
        """Test Precision@k with no relevant docs."""
        retrieved = ["evt_1", "evt_3", "evt_5"]
        relevant = ["evt_2", "evt_4"]

        precision = RetrievalMetrics.precision_at_k(retrieved, relevant, k=3)
        assert precision == 0.0

    def test_precision_at_k_smaller_retrieved(self):
        """Test Precision@k when retrieved list is smaller than k."""
        retrieved = ["evt_1", "evt_2"]
        relevant = ["evt_2", "evt_4"]

        precision = RetrievalMetrics.precision_at_k(retrieved, relevant, k=5)
        assert precision == 0.5  # 1 out of 2 (not 5)

    def test_precision_at_k_all_relevant(self):
        """Test Precision@k when all retrieved docs are relevant."""
        retrieved = ["evt_1", "evt_2", "evt_3"]
        relevant = ["evt_1", "evt_2", "evt_3", "evt_4", "evt_5"]

        precision = RetrievalMetrics.precision_at_k(retrieved, relevant, k=3)
        assert precision == 1.0

    def test_precision_empty_lists(self):
        """Test Precision@k with empty lists."""
        assert RetrievalMetrics.precision_at_k([], ["evt_1"], k=5) == 0.0
        assert RetrievalMetrics.precision_at_k(["evt_1"], [], k=5) == 0.0


class TestRecallAtK:
    """Test Recall@k metric calculation."""

    def test_recall_at_k_basic(self):
        """Test basic Recall@k calculation."""
        retrieved = ["evt_1", "evt_2", "evt_3"]
        relevant = ["evt_2", "evt_4", "evt_5"]

        recall = RetrievalMetrics.recall_at_k(retrieved, relevant, k=5)
        assert recall == pytest.approx(0.333, rel=0.01)  # 1 out of 3 relevant docs

    def test_recall_at_k_perfect(self):
        """Test Recall@k with all relevant docs retrieved."""
        retrieved = ["evt_2", "evt_4", "evt_5"]
        relevant = ["evt_2", "evt_4", "evt_5"]

        recall = RetrievalMetrics.recall_at_k(retrieved, relevant, k=3)
        assert recall == 1.0

    def test_recall_at_k_zero(self):
        """Test Recall@k with no relevant docs retrieved."""
        retrieved = ["evt_1", "evt_3", "evt_6"]
        relevant = ["evt_2", "evt_4", "evt_5"]

        recall = RetrievalMetrics.recall_at_k(retrieved, relevant, k=3)
        assert recall == 0.0

    def test_recall_at_k_partial(self):
        """Test Recall@k with some relevant docs retrieved."""
        retrieved = ["evt_1", "evt_2", "evt_3", "evt_4", "evt_6"]
        relevant = ["evt_2", "evt_4", "evt_5", "evt_7"]

        recall = RetrievalMetrics.recall_at_k(retrieved, relevant, k=5)
        assert recall == 0.5  # 2 out of 4 relevant docs

    def test_recall_empty_lists(self):
        """Test Recall@k with empty lists."""
        assert RetrievalMetrics.recall_at_k([], ["evt_1", "evt_2"], k=5) == 0.0
        assert RetrievalMetrics.recall_at_k(["evt_1"], [], k=5) == 0.0


class TestNDCGAtK:
    """Test Normalized Discounted Cumulative Gain (NDCG@k)."""

    def test_ndcg_perfect_ranking(self):
        """Test NDCG with perfect ranking."""
        retrieved = ["evt_1", "evt_2", "evt_3"]
        scores = {"evt_1": 1.0, "evt_2": 0.8, "evt_3": 0.5, "evt_4": 0.0}

        ndcg = RetrievalMetrics.ndcg_at_k(retrieved, scores, k=3)
        assert ndcg == 1.0  # Perfect ranking

    def test_ndcg_imperfect_ranking(self):
        """Test NDCG with suboptimal ranking."""
        retrieved = ["evt_3", "evt_1", "evt_2"]  # Reversed order
        scores = {"evt_1": 1.0, "evt_2": 0.8, "evt_3": 0.5, "evt_4": 0.0}

        ndcg = RetrievalMetrics.ndcg_at_k(retrieved, scores, k=3)
        assert 0.0 < ndcg < 1.0  # Not perfect, but not zero

    def test_ndcg_worst_ranking(self):
        """Test NDCG with worst possible ranking."""
        retrieved = ["evt_4", "evt_3", "evt_2"]
        scores = {"evt_1": 1.0, "evt_2": 0.8, "evt_3": 0.5, "evt_4": 0.0}

        ndcg = RetrievalMetrics.ndcg_at_k(retrieved, scores, k=3)
        assert ndcg < 0.6  # Poor ranking

    def test_ndcg_binary_relevance(self):
        """Test NDCG with binary relevance (0 or 1)."""
        retrieved = ["evt_1", "evt_3", "evt_2"]
        scores = {"evt_1": 1.0, "evt_2": 0.0, "evt_3": 1.0, "evt_4": 0.0}

        ndcg = RetrievalMetrics.ndcg_at_k(retrieved, scores, k=3)
        assert ndcg > 0.8  # Good ranking (two relevant docs at top)

    def test_ndcg_empty_scores(self):
        """Test NDCG with empty relevance scores."""
        ndcg = RetrievalMetrics.ndcg_at_k(["evt_1"], {}, k=1)
        assert ndcg == 0.0

    def test_ndcg_all_irrelevant(self):
        """Test NDCG when all docs are irrelevant."""
        retrieved = ["evt_1", "evt_2", "evt_3"]
        scores = {"evt_1": 0.0, "evt_2": 0.0, "evt_3": 0.0}

        ndcg = RetrievalMetrics.ndcg_at_k(retrieved, scores, k=3)
        assert ndcg == 0.0


class TestF1Score:
    """Test F1 score calculation."""

    def test_f1_balanced(self):
        """Test F1 with balanced precision and recall."""
        retrieved = ["evt_1", "evt_2", "evt_3", "evt_4"]
        relevant = ["evt_2", "evt_4"]

        f1 = RetrievalMetrics.f1_score(retrieved, relevant, k=4)
        assert f1 == pytest.approx(0.667, rel=0.01)

    def test_f1_perfect(self):
        """Test F1 with perfect precision and recall."""
        retrieved = ["evt_1", "evt_2"]
        relevant = ["evt_1", "evt_2"]

        f1 = RetrievalMetrics.f1_score(retrieved, relevant, k=2)
        assert f1 == 1.0

    def test_f1_zero(self):
        """Test F1 when no relevant docs retrieved."""
        retrieved = ["evt_1", "evt_3"]
        relevant = ["evt_2", "evt_4"]

        f1 = RetrievalMetrics.f1_score(retrieved, relevant, k=2)
        assert f1 == 0.0

    def test_f1_high_precision_low_recall(self):
        """Test F1 with high precision but low recall."""
        retrieved = ["evt_1", "evt_3"]
        relevant = ["evt_1", "evt_2", "evt_4", "evt_5"]

        f1 = RetrievalMetrics.f1_score(retrieved, relevant, k=2)
        assert f1 == pytest.approx(0.333, rel=0.01)


class TestEvaluateRetrieval:
    """Test comprehensive retrieval evaluation."""

    def test_evaluate_retrieval_all_metrics(self):
        """Test that evaluate_retrieval returns all metrics."""
        retrieved = ["evt_1", "evt_2", "evt_3", "evt_4", "evt_5"]
        relevant = ["evt_2", "evt_4", "evt_6"]
        scores = {"evt_1": 0.0, "evt_2": 1.0, "evt_3": 0.0, "evt_4": 0.8, "evt_5": 0.0, "evt_6": 0.5}

        metrics = RetrievalMetrics.evaluate_retrieval(retrieved, relevant, scores, k=5)

        # Verify all expected metrics are present
        assert "hit_rate" in metrics
        assert "mrr" in metrics
        assert "precision@5" in metrics
        assert "recall@5" in metrics
        assert "f1@5" in metrics
        assert "ndcg@5" in metrics

        # Verify metric values are floats in valid range
        for metric_name, value in metrics.items():
            assert isinstance(value, float)
            assert 0.0 <= value <= 1.0

    def test_evaluate_retrieval_without_ndcg(self):
        """Test evaluate_retrieval without NDCG (no relevance scores)."""
        retrieved = ["evt_1", "evt_2", "evt_3"]
        relevant = ["evt_2"]

        metrics = RetrievalMetrics.evaluate_retrieval(retrieved, relevant, k=3)

        # NDCG should not be present without relevance scores
        assert "ndcg@3" not in metrics
        assert "hit_rate" in metrics
        assert "mrr" in metrics

    def test_evaluate_retrieval_specific_values(self):
        """Test evaluate_retrieval with known expected values."""
        retrieved = ["evt_1", "evt_2", "evt_3"]
        relevant = ["evt_2", "evt_4"]

        metrics = RetrievalMetrics.evaluate_retrieval(retrieved, relevant, k=3)

        assert metrics["hit_rate"] == 1.0  # evt_2 is present
        assert metrics["mrr"] == 0.5  # evt_2 is at position 2
        assert metrics["precision@3"] == pytest.approx(0.333, rel=0.01)  # 1 out of 3
        assert metrics["recall@3"] == 0.5  # 1 out of 2 relevant docs


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
