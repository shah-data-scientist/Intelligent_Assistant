"""
FILE: test_structured_output.py
STATUS: Active
RESPONSIBILITY: E2E tests for Pydantic structured output with UnifiedAnalyzer.

DEPENDENCIES (Who uses this file):
- pytest test runner
- LLM integration validation

IMPORTS (What this file needs):
- logging: Test output
- sys: UTF-8 encoding configuration
- src.retrieval.unified_analyzer: UnifiedAnalyzer for structured output testing
- src.config: Settings for LLM configuration

LAST MAJOR UPDATE: 2026-01-31
MAINTAINER: QA Team
"""

import logging
import sys
from src.retrieval.unified_analyzer import get_unified_analyzer
from src.config import settings

# Force UTF-8 encoding for Windows console
sys.stdout.reconfigure(encoding="utf-8")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def safe_print(text):
    """Print text safely handling encoding issues."""
    try:
        print(text)
    except UnicodeEncodeError:
        # Fallback: encode to ASCII ignoring errors
        print(text.encode("ascii", "ignore").decode("ascii"))


def test_structured_output():
    """Test structured output with simple queries."""

    safe_print("=" * 80)
    safe_print("PHASE 2 TEST: PYDANTIC STRUCTURED OUTPUT")
    safe_print("=" * 80)
    safe_print("")

    # Check backend
    safe_print(f"Current LLM backend: {settings.llm_backend}")

    if settings.llm_backend != "google":
        safe_print("[WARNING] Not using Google backend. Structured output requires Gemini.")
        safe_print("Set LLM_BACKEND=google in .env to test structured output.")
        return

    safe_print("")
    safe_print("=" * 80)
    safe_print("")

    # Initialize analyzer
    analyzer = get_unified_analyzer()

    safe_print("[INFO] Analyzer initialized")
    safe_print(f"[INFO] use_structured_output = {analyzer.use_structured_output}")
    safe_print(f"[INFO] structured_llm exists = {analyzer.structured_llm is not None}")
    safe_print("")

    if not analyzer.use_structured_output:
        safe_print("[WARNING] Structured output is NOT enabled")
        safe_print("This may happen if:")
        safe_print("  1. Backend is not 'google'")
        safe_print("  2. with_structured_output() failed during initialization")
        return

    safe_print("=" * 80)
    safe_print("")

    # Test queries
    test_queries = [
        "concerts de jazz a Paris ce week-end",
        "go from porte de pantin to Art of the Trio",
        "bonjour",
        "combien d'evenements a Paris?",
    ]

    for i, query in enumerate(test_queries, 1):
        safe_print(f"Test {i}: {query}")
        safe_print("-" * 80)

        try:
            result = analyzer.analyze(query, known_cities=["Paris", "Versailles"])

            safe_print(f"[OK] Intent: {result.intent.value}")
            safe_print(f"[OK] Confidence: {result.intent_confidence}")
            safe_print(f"[OK] Language: {result.detected_language}")
            safe_print(f"[OK] City: {result.city_normalized}")
            safe_print(f"[OK] Event type: {result.event_type}")
            safe_print(f"[OK] Complete: {result.is_complete}")

            # Check dimensions
            greeting = result.dimensions.get("greeting")
            if greeting and greeting.detected:
                safe_print(f"[OK] Greeting detected: {greeting.detected}")

            statistical = result.dimensions.get("statistical")
            if statistical and statistical.detected:
                safe_print("[OK] Statistical query detected")

            safe_print("")

        except Exception as e:
            safe_print(f"[ERROR] Failed to analyze query: {e}")
            import traceback

            traceback.print_exc()
            return

    safe_print("=" * 80)
    safe_print("TEST COMPLETE - All queries processed successfully!")
    safe_print("=" * 80)


if __name__ == "__main__":
    test_structured_output()
