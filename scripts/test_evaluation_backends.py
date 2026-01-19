"""Test script to verify different LLM backends for evaluation.

This script tests all three backends (Mistral, Hugging Face, Ollama) if available.
"""

import logging
import sys
from typing import Any

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def test_backend(backend_type: str, **kwargs: Any) -> None:
    """Test a specific backend.

    Args:
        backend_type: Type of backend to test
        **kwargs: Backend-specific parameters
    """
    from src.evaluation.metrics.generation import LLMAsJudge

    logger.info(f"\n{'='*60}")
    logger.info(f"Testing {backend_type.upper()} backend")
    logger.info(f"{'='*60}")

    try:
        # Initialize judge with backend
        judge = LLMAsJudge(backend_type=backend_type, **kwargs)
        logger.info(f"✓ Backend initialized: {judge.backend.get_name()}")

        # Test faithfulness evaluation
        query = "What jazz concerts are available in Paris?"
        answer = "There is a Jazz Night concert in Paris on 15/02/2026."
        sources = ["Title: Jazz Night\nCity: Paris\nDate: 15/02/2026"]

        logger.info("\nTesting faithfulness evaluation...")
        result = judge.evaluate_faithfulness(query, answer, sources)

        logger.info(f"✓ Faithfulness score: {result['score']:.2f}")
        logger.info(f"  Reasoning: {result.get('reasoning', 'N/A')}")
        logger.info(f"  Violations: {len(result['violations'])}")

        # Test relevancy evaluation
        logger.info("\nTesting relevancy evaluation...")
        result = judge.evaluate_relevancy(query, answer)

        logger.info(f"✓ Relevancy score: {result['score']:.2f}")
        logger.info(f"  Reasoning: {result.get('reasoning', 'N/A')}")

        # Test language consistency
        logger.info("\nTesting language consistency...")
        result = judge.evaluate_language_consistency(query, answer)

        logger.info(f"✓ Language consistent: {result['is_consistent']}")
        logger.info(f"  Query language: {result['query_language']}")
        logger.info(f"  Answer language: {result['answer_language']}")

        logger.info(f"\n✅ {backend_type.upper()} backend test PASSED\n")
        return True

    except Exception as e:
        logger.error(f"\n❌ {backend_type.upper()} backend test FAILED: {e}\n")
        return False


def main():
    """Run tests for all available backends."""
    import argparse

    parser = argparse.ArgumentParser(description="Test evaluation LLM backends")
    parser.add_argument(
        "--backend",
        choices=["all", "mistral", "huggingface", "ollama"],
        default="all",
        help="Which backend to test"
    )
    parser.add_argument(
        "--hf-token",
        help="Hugging Face API token (or set HF_TOKEN env var)"
    )
    parser.add_argument(
        "--hf-model",
        default="mistralai/Mistral-7B-Instruct-v0.2",
        help="Hugging Face model ID"
    )
    parser.add_argument(
        "--ollama-model",
        default="mistral",
        help="Ollama model name"
    )

    args = parser.parse_args()

    results = {}

    # Test Mistral
    if args.backend in ["all", "mistral"]:
        try:
            results["mistral"] = test_backend("mistral")
        except Exception as e:
            logger.warning(f"Skipping Mistral test: {e}")
            results["mistral"] = False

    # Test Hugging Face
    if args.backend in ["all", "huggingface"]:
        import os
        hf_token = args.hf_token or os.getenv("HF_TOKEN")

        if not hf_token:
            logger.warning(
                "Skipping Hugging Face test: No API token provided. "
                "Set HF_TOKEN environment variable or use --hf-token"
            )
            results["huggingface"] = False
        else:
            try:
                results["huggingface"] = test_backend(
                    "huggingface",
                    model_id=args.hf_model,
                    api_token=hf_token
                )
            except Exception as e:
                logger.warning(f"Skipping Hugging Face test: {e}")
                results["huggingface"] = False

    # Test Ollama
    if args.backend in ["all", "ollama"]:
        try:
            results["ollama"] = test_backend(
                "ollama",
                model=args.ollama_model
            )
        except Exception as e:
            logger.warning(f"Skipping Ollama test: {e}")
            results["ollama"] = False

    # Summary
    logger.info(f"\n{'='*60}")
    logger.info("TEST SUMMARY")
    logger.info(f"{'='*60}")

    for backend, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        logger.info(f"{backend:15s}: {status}")

    total = len(results)
    passed = sum(results.values())
    logger.info(f"\nTotal: {passed}/{total} backends passed")

    # Exit code
    sys.exit(0 if passed > 0 else 1)


if __name__ == "__main__":
    main()
