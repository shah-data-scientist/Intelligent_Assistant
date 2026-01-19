"""Focused evaluation on high-complexity queries."""

import logging
from pathlib import Path
import json

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

from src.evaluation.evaluators.system_evaluator import SystemEvaluator
from src.evaluation.datasets.golden_dataset import GoldenDataset
from src.evaluation.reports.reporter import ReportGenerator

def main():
    try:
        # Load full dataset
        logger.info("Loading golden dataset...")
        full_dataset = GoldenDataset.load("data/evaluation/golden_dataset.json")

        # Filter for high-complexity queries only
        high_complexity_queries = [
            q for q in full_dataset.queries
            if q.complexity == "high"
        ]

        logger.info(f"Found {len(high_complexity_queries)} high-complexity queries")

        # Sample 10 diverse high-complexity queries
        import random
        random.seed(42)  # Reproducible
        sample_queries = random.sample(high_complexity_queries, min(10, len(high_complexity_queries)))

        # Create subset dataset
        subset_dataset = GoldenDataset(
            created_at=full_dataset.created_at,
            description="High-complexity queries subset",
            version=full_dataset.version,
            queries=sample_queries
        )

        logger.info(f"Testing {len(sample_queries)} high-complexity queries:")
        for q in sample_queries:
            logger.info(f"  - {q.id}: {q.query} [{q.query_type}]")

        # Save subset temporarily
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
            subset_dataset.save(f.name)
            temp_dataset_path = f.name

        # Initialize evaluator
        logger.info("Initializing SystemEvaluator...")
        evaluator = SystemEvaluator(judge_backend="mistral")

        # Run evaluation
        logger.info("Running evaluation on high-complexity queries...")
        report = evaluator.run_full_evaluation(
            golden_dataset_path=temp_dataset_path,
            retrieval_k=5
        )

        # Clean up
        Path(temp_dataset_path).unlink()

        # Generate report
        logger.info("Generating report...")
        output_dir = Path("data/evaluation/reports")
        output_dir.mkdir(parents=True, exist_ok=True)

        reporter = ReportGenerator()
        timestamp = report.timestamp.replace(":", "-").split(".")[0]
        output_file = output_dir / f"complex_queries_eval_{timestamp}.md"

        reporter.save_report(report, str(output_file), format="markdown")
        logger.info(f"Report saved to: {output_file}")

        # Print detailed summary
        status = report.overall_status
        logger.info("\n" + "="*80)
        logger.info("HIGH-COMPLEXITY QUERIES EVALUATION SUMMARY")
        logger.info("="*80)
        logger.info(f"Queries Tested: {len(sample_queries)}")
        logger.info(f"Quality Score: {status['quality_score']:.3f} (SLA: {status['quality_sla']}) - {'PASS' if status['quality_pass'] else 'FAIL'}")
        logger.info(f"  - Faithfulness: {report.generation_metrics['faithfulness_score']:.3f}")
        logger.info(f"  - Relevancy: {report.generation_metrics['relevancy_score']:.3f}")
        logger.info(f"Avg Latency: {status['avg_latency_ms']:.0f}ms (SLA: {status['latency_sla_ms']}ms) - {'PASS' if status['latency_pass'] else 'FAIL'}")
        logger.info(f"Overall: {'PASS' if status['overall_pass'] else 'FAIL'}")
        logger.info("="*80)

        # Query type breakdown
        logger.info("\nPerformance by Query Type:")
        query_types = {}
        for result in report.per_query_results:
            qtype = result.get("query_type", "unknown")
            if qtype not in query_types:
                query_types[qtype] = {"count": 0, "quality_sum": 0, "relevancy_sum": 0}
            query_types[qtype]["count"] += 1
            query_types[qtype]["quality_sum"] += result.get("quality_score", 0)
            query_types[qtype]["relevancy_sum"] += result.get("relevancy", 0)

        for qtype, stats in query_types.items():
            avg_quality = stats["quality_sum"] / stats["count"]
            avg_relevancy = stats["relevancy_sum"] / stats["count"]
            logger.info(f"  - {qtype}: Quality={avg_quality:.3f}, Relevancy={avg_relevancy:.3f} ({stats['count']} queries)")

        return 0 if status['overall_pass'] else 1

    except Exception as e:
        logger.error(f"Evaluation failed: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    exit(main())
