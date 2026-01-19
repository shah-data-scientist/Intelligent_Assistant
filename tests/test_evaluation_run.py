"""Quick test script to verify evaluation system works."""

import logging
from pathlib import Path

# Setup logging
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
        # Load subset of golden dataset
        logger.info("Loading golden dataset...")
        golden_dataset = GoldenDataset.load("data/evaluation/golden_dataset.json")
        subset_dataset = golden_dataset.get_subset(n=3)  # Just 3 queries for quick test

        logger.info(f"Testing with {subset_dataset.total_queries} queries")

        # Save subset temporarily
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
            subset_dataset.save(f.name)
            temp_dataset_path = f.name

        # Initialize evaluator with Mistral backend
        logger.info("Initializing SystemEvaluator...")
        evaluator = SystemEvaluator(judge_backend="mistral")

        # Run evaluation
        logger.info("Running evaluation...")
        report = evaluator.run_full_evaluation(
            golden_dataset_path=temp_dataset_path,
            retrieval_k=5
        )

        # Clean up temp file
        Path(temp_dataset_path).unlink()

        # Generate markdown report
        logger.info("Generating report...")
        output_dir = Path("data/evaluation/reports")
        output_dir.mkdir(parents=True, exist_ok=True)

        reporter = ReportGenerator()
        timestamp = report.timestamp.replace(":", "-").split(".")[0]
        output_file = output_dir / f"test_evaluation_report_{timestamp}.md"

        reporter.save_report(report, str(output_file), format="markdown")

        logger.info(f"Report saved to: {output_file}")

        # Print summary
        status = report.overall_status
        logger.info("\n" + "="*70)
        logger.info("EVALUATION COMPLETE - SUMMARY")
        logger.info("="*70)
        logger.info(f"Quality Score: {status['quality_score']:.3f} (SLA: {status['quality_sla']}) - {'PASS' if status['quality_pass'] else 'FAIL'}")
        logger.info(f"Avg Latency: {status['avg_latency_ms']:.0f}ms (SLA: {status['latency_sla_ms']}ms) - {'PASS' if status['latency_pass'] else 'FAIL'}")
        logger.info(f"Overall: {'PASS' if status['overall_pass'] else 'FAIL'}")
        logger.info("="*70)

        return 0 if status['overall_pass'] else 1

    except Exception as e:
        logger.error(f"Evaluation failed: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    exit(main())
