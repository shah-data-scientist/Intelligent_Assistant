"""Run full evaluation suite on golden dataset.

This script orchestrates the complete evaluation process:
1. Loads golden dataset
2. Runs retrieval evaluation
3. Runs generation quality evaluation (LLM-as-a-Judge)
4. Generates reports in multiple formats
5. Checks SLA compliance

Usage:
    # Full evaluation with default settings
    python scripts/run_evaluation.py

    # Quick test (first 5 queries)
    python scripts/run_evaluation.py --subset 5

    # Use free Hugging Face backend
    python scripts/run_evaluation.py --judge-backend huggingface

    # Custom dataset
    python scripts/run_evaluation.py --dataset data/evaluation/custom.json

    # Generate HTML report
    python scripts/run_evaluation.py --format html
"""

import argparse
import logging
import sys
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Main evaluation runner."""
    parser = argparse.ArgumentParser(
        description="Evaluate RAG system performance",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Full evaluation
  python scripts/run_evaluation.py

  # Quick test (first 10 queries)
  python scripts/run_evaluation.py --subset 10

  # Use free Hugging Face backend (set HF_TOKEN env var)
  python scripts/run_evaluation.py --judge-backend huggingface

  # Use local Ollama (free, unlimited)
  python scripts/run_evaluation.py --judge-backend ollama

  # Generate all report formats
  python scripts/run_evaluation.py --format json --format markdown --format html
        """
    )

    parser.add_argument(
        "--dataset",
        default=None,
        help="Path to golden dataset (default: from config)"
    )

    parser.add_argument(
        "--subset",
        type=int,
        help="Evaluate only first N queries (for quick tests)"
    )

    parser.add_argument(
        "--output-dir",
        default="data/evaluation/reports",
        help="Directory to save reports (default: data/evaluation/reports)"
    )

    parser.add_argument(
        "--format",
        action="append",
        choices=["json", "markdown", "html"],
        default=None,
        help="Report format(s) to generate (can specify multiple, default: markdown)"
    )

    parser.add_argument(
        "--judge-backend",
        choices=["mistral", "huggingface", "ollama"],
        default="mistral",
        help="LLM backend for LLM-as-a-Judge (default: mistral)"
    )

    parser.add_argument(
        "--hf-token",
        help="Hugging Face API token (or set HF_TOKEN env var)"
    )

    parser.add_argument(
        "--hf-model",
        default="mistralai/Mistral-7B-Instruct-v0.2",
        help="Hugging Face model ID (default: mistralai/Mistral-7B-Instruct-v0.2)"
    )

    parser.add_argument(
        "--ollama-model",
        default="mistral",
        help="Ollama model name (default: mistral)"
    )

    parser.add_argument(
        "--retrieval-k",
        type=int,
        default=5,
        help="Number of documents to retrieve (default: 5)"
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )

    args = parser.parse_args()

    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Default format
    if args.format is None:
        args.format = ["markdown"]

    # Import here to avoid loading heavy dependencies if just showing help
    from src.evaluation.evaluators.system_evaluator import SystemEvaluator
    from src.evaluation.datasets.golden_dataset import GoldenDataset
    from src.evaluation.reports.reporter import ReportGenerator
    from src.config import settings

    try:
        logger.info("="*70)
        logger.info("RAG System Evaluation Suite")
        logger.info("="*70)

        # Load golden dataset
        dataset_path = args.dataset or settings.golden_dataset_path
        logger.info(f"Loading golden dataset from: {dataset_path}")
        golden_dataset = GoldenDataset.load(dataset_path)

        # Subset if requested
        if args.subset:
            logger.info(f"Using subset: first {args.subset} queries")
            golden_dataset = golden_dataset.get_subset(n=args.subset)

        logger.info(f"Dataset loaded: {golden_dataset.total_queries} queries")

        # Prepare judge kwargs
        judge_kwargs = {}
        if args.judge_backend == "huggingface":
            import os
            judge_kwargs["model_id"] = args.hf_model
            judge_kwargs["api_token"] = args.hf_token or os.getenv("HF_TOKEN")
            if not judge_kwargs["api_token"]:
                logger.error(
                    "Hugging Face backend requires API token. "
                    "Set HF_TOKEN environment variable or use --hf-token"
                )
                sys.exit(1)
        elif args.judge_backend == "ollama":
            judge_kwargs["model"] = args.ollama_model

        # Initialize evaluator
        logger.info(f"Initializing evaluator with judge backend: {args.judge_backend}")
        evaluator = SystemEvaluator(
            judge_backend=args.judge_backend,
            **judge_kwargs
        )

        # Save dataset to temp location for evaluation
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
            golden_dataset.save(f.name)
            temp_dataset_path = f.name

        # Run evaluation
        logger.info("")
        logger.info("Starting evaluation...")
        logger.info("")

        report = evaluator.run_full_evaluation(
            golden_dataset_path=temp_dataset_path,
            retrieval_k=args.retrieval_k
        )

        # Clean up temp file
        Path(temp_dataset_path).unlink()

        # Generate reports
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        reporter = ReportGenerator()

        logger.info("")
        logger.info("="*70)
        logger.info("Generating Reports")
        logger.info("="*70)

        for fmt in args.format:
            timestamp = report.timestamp.replace(":", "-").split(".")[0]
            output_file = output_dir / f"evaluation_report_{timestamp}.{fmt}"

            reporter.save_report(report, str(output_file), format=fmt)
            logger.info(f"✅ {fmt.upper()} report: {output_file}")

        # Print summary
        logger.info("")
        logger.info("="*70)
        logger.info("Evaluation Summary")
        logger.info("="*70)

        status = report.overall_status
        logger.info(f"Quality Score: {status['quality_score']:.3f} (SLA: {status['quality_sla']}) "
                   f"- {'✅ PASS' if status['quality_pass'] else '❌ FAIL'}")
        logger.info(f"Avg Latency: {status['avg_latency_ms']:.0f}ms (SLA: {status['latency_sla_ms']}ms) "
                   f"- {'✅ PASS' if status['latency_pass'] else '❌ FAIL'}")
        logger.info(f"Overall: {'✅ PASS' if status['overall_pass'] else '❌ FAIL'}")
        logger.info("="*70)

        # Exit code
        sys.exit(0 if status['overall_pass'] else 1)

    except KeyboardInterrupt:
        logger.info("\nEvaluation interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Evaluation failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
