"""
FILE: test_post_hybrid_evaluation.py
STATUS: Active
RESPONSIBILITY: Tests for post-hybrid retrieval evaluation metrics.

DEPENDENCIES (Who uses this file):
- pytest test runner
- Hybrid search quality validation

IMPORTS (What this file needs):
- pytest: Test framework
- src.evaluation.metrics: Hybrid search metrics

LAST MAJOR UPDATE: 2026-01-31
MAINTAINER: QA Team
"""

import logging
from pathlib import Path
import uuid

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

from src.evaluation.evaluators.system_evaluator import SystemEvaluator
from src.evaluation.datasets.golden_dataset import GoldenDataset


def main():
    try:
        # Load dataset
        logger.info("Loading golden dataset...")
        dataset = GoldenDataset.load("data/evaluation/golden_dataset.json")

        # Sample 15 diverse queries (mix of simple, medium, high complexity)
        import random

        random.seed(42)

        # Get queries by complexity
        simple_queries = [q for q in dataset.queries if q.complexity == "simple"]
        medium_queries = [q for q in dataset.queries if q.complexity == "medium"]
        high_queries = [q for q in dataset.queries if q.complexity == "high"]

        # Sample from each
        sample_queries = []
        sample_queries.extend(random.sample(simple_queries, min(5, len(simple_queries))))
        sample_queries.extend(random.sample(medium_queries, min(5, len(medium_queries))))
        sample_queries.extend(random.sample(high_queries, min(5, len(high_queries))))

        logger.info(f"Testing {len(sample_queries)} queries:")
        for q in sample_queries:
            logger.info(f"  - [{q.complexity}] {q.id}: {q.query}")

        # Create subset dataset
        subset_dataset = GoldenDataset(
            created_at=dataset.created_at,
            description="Post-hybrid search evaluation",
            version=dataset.version,
            queries=sample_queries,
        )

        # Save subset temporarily
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
            subset_dataset.save(f.name)
            temp_dataset_path = f.name

        # Initialize evaluator
        logger.info("Initializing SystemEvaluator...")
        evaluator = SystemEvaluator(judge_backend="mistral")

        # Run evaluation
        logger.info("Running evaluation...")
        report = evaluator.run_full_evaluation(
            golden_dataset_path=temp_dataset_path, retrieval_k=5, session_id=f"post_hybrid_eval_{uuid.uuid4().hex[:8]}"
        )

        # Clean up
        Path(temp_dataset_path).unlink()

        # Print summary
        status = report.overall_status
        logger.info("\n" + "=" * 80)
        logger.info("POST-HYBRID SEARCH EVALUATION SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Queries Tested: {len(sample_queries)}")
        logger.info(f"  - Simple: {len([q for q in sample_queries if q.complexity == 'simple'])}")
        logger.info(f"  - Medium: {len([q for q in sample_queries if q.complexity == 'medium'])}")
        logger.info(f"  - High: {len([q for q in sample_queries if q.complexity == 'high'])}")
        logger.info("")
        logger.info(
            f"Quality Score: {status['quality_score']:.3f} (SLA: {status['quality_sla']}) - {'PASS' if status['quality_pass'] else 'FAIL'}"
        )
        logger.info(f"  - Faithfulness: {report.generation_metrics['faithfulness_score']:.3f} (target: >0.7)")
        logger.info(f"  - Relevancy: {report.generation_metrics['relevancy_score']:.3f} (target: >0.8)")
        logger.info("")
        logger.info("Retrieval Performance:")
        logger.info(f"  - Hit Rate: {report.retrieval_metrics.get('hit_rate', 'N/A'):.1%}")
        logger.info(f"  - MRR: {report.retrieval_metrics.get('mrr', 'N/A'):.3f}")
        logger.info("")
        logger.info(
            f"Avg Latency: {status['avg_latency_ms']:.0f}ms (SLA: {status['latency_sla_ms']}ms) - {'PASS' if status['latency_pass'] else 'FAIL'}"
        )
        logger.info("")
        logger.info(f"Overall: {'PASS' if status['overall_pass'] else 'FAIL'}")
        logger.info("=" * 80)

        # Complexity breakdown
        logger.info("\nPerformance by Complexity:")
        complexity_stats = {}
        for result in report.per_query_results:
            complexity = result.get("complexity", "unknown")
            if complexity not in complexity_stats:
                complexity_stats[complexity] = {"count": 0, "quality_sum": 0, "faithfulness_sum": 0, "relevancy_sum": 0}
            complexity_stats[complexity]["count"] += 1
            complexity_stats[complexity]["quality_sum"] += result.get("quality_score", 0)
            complexity_stats[complexity]["faithfulness_sum"] += result.get("faithfulness", 0)
            complexity_stats[complexity]["relevancy_sum"] += result.get("relevancy", 0)

        for complexity, stats in sorted(complexity_stats.items()):
            avg_quality = stats["quality_sum"] / stats["count"]
            avg_faith = stats["faithfulness_sum"] / stats["count"]
            avg_rel = stats["relevancy_sum"] / stats["count"]
            logger.info(
                f"  {complexity.upper()}: Quality={avg_quality:.3f}, Faith={avg_faith:.3f}, Rel={avg_rel:.3f} ({stats['count']} queries)"
            )

        # Genre-specific breakdown
        logger.info("\nGenre-Specific Query Performance:")
        genre_queries = [
            r
            for r in report.per_query_results
            if any(
                kw in r.get("query", "").lower() for kw in ["jazz", "classique", "classical", "rock", "électronique"]
            )
        ]
        if genre_queries:
            avg_genre_quality = sum(r.get("quality_score", 0) for r in genre_queries) / len(genre_queries)
            avg_genre_faith = sum(r.get("faithfulness", 0) for r in genre_queries) / len(genre_queries)
            avg_genre_rel = sum(r.get("relevancy", 0) for r in genre_queries) / len(genre_queries)
            logger.info(
                f"  Genre queries ({len(genre_queries)}): Quality={avg_genre_quality:.3f}, Faith={avg_genre_faith:.3f}, Rel={avg_genre_rel:.3f}"
            )

        # Save report
        output_dir = Path("data/evaluation/reports")
        output_dir.mkdir(parents=True, exist_ok=True)

        from src.evaluation.reports.reporter import ReportGenerator

        reporter = ReportGenerator()
        timestamp = report.timestamp.replace(":", "-").split(".")[0]
        output_file = output_dir / f"post_hybrid_eval_{timestamp}.md"

        reporter.save_report(report, str(output_file), format="markdown")
        logger.info(f"\nFull report saved to: {output_file}")

        return 0 if status["overall_pass"] else 1

    except Exception as e:
        logger.error(f"Evaluation failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    exit(main())
