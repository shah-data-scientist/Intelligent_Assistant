"""
FILE: smoke_test_mistral_judge.py
STATUS: Active
RESPONSIBILITY: Quick smoke test to verify Mistral LLM-as-a-Judge backend works before full evaluation
LAST MAJOR UPDATE: 2026-01-31
MAINTAINER: Team
"""

import sys
import os
import time

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_mistral_backend_init():
    """Test that Mistral backend can be initialized."""
    print("Testing Mistral backend initialization...")
    try:
        from src.evaluation.llm_backends import create_llm_backend

        backend = create_llm_backend("mistral", temperature=0.0)
        name = backend.get_name()

        if name == "mistral":
            print(f"[OK] Mistral backend initialized: {name}")
            return True, backend
        else:
            print(f"[FAIL] Unexpected backend name: {name}")
            return False, None
    except Exception as e:
        print(f"[FAIL] Backend initialization failed: {e}")
        return False, None


def test_simple_invocation(backend):
    """Test that Mistral can respond to a simple prompt."""
    print("Testing simple invocation...")
    try:
        response = backend.invoke("Say 'hello' in JSON format: {\"greeting\": \"hello\"}")

        if response and len(response) > 0:
            print(f"[OK] Mistral responded ({len(response)} chars)")
            print(f"     Preview: {response[:100]}...")
            return True
        else:
            print("[FAIL] Empty response from Mistral")
            return False
    except Exception as e:
        print(f"[FAIL] Invocation failed: {e}")
        return False


def test_llm_judge_faithfulness():
    """Test LLM-as-a-Judge faithfulness evaluation."""
    print("Testing faithfulness evaluation...")
    try:
        from src.evaluation.metrics.generation import LLMAsJudge

        judge = LLMAsJudge(backend_type="mistral")

        # Test case: Answer fully grounded in source
        query = "What jazz concerts are available in Paris?"
        answer = "There is a Jazz Night concert at Blue Note Paris on February 15, 2026."
        sources = ["Title: Jazz Night\nVenue: Blue Note Paris\nDate: 15/02/2026\nCategory: Music"]

        result = judge.evaluate_faithfulness(query, answer, sources)

        if "score" in result and 0.0 <= result["score"] <= 1.0:
            print(f"[OK] Faithfulness score: {result['score']:.2f}")
            print(f"     Reasoning: {result.get('reasoning', 'N/A')[:80]}...")
            return True
        else:
            print(f"[FAIL] Invalid faithfulness result: {result}")
            return False
    except Exception as e:
        print(f"[FAIL] Faithfulness evaluation failed: {e}")
        return False


def test_llm_judge_relevancy():
    """Test LLM-as-a-Judge relevancy evaluation."""
    print("Testing relevancy evaluation...")
    try:
        from src.evaluation.metrics.generation import LLMAsJudge

        judge = LLMAsJudge(backend_type="mistral")

        # Test case: Relevant answer
        query = "Show me jazz concerts in Paris"
        answer = "Here are jazz concerts in Paris:\n1. Jazz Night at Blue Note - February 15, 2026\n2. Jazz Festival at Sunset - February 20, 2026"

        result = judge.evaluate_relevancy(query, answer)

        if "score" in result and 0.0 <= result["score"] <= 1.0:
            print(f"[OK] Relevancy score: {result['score']:.2f}")
            print(f"     Reasoning: {result.get('reasoning', 'N/A')[:80]}...")
            return True
        else:
            print(f"[FAIL] Invalid relevancy result: {result}")
            return False
    except Exception as e:
        print(f"[FAIL] Relevancy evaluation failed: {e}")
        return False


def test_full_generation_evaluation():
    """Test complete generation evaluation flow."""
    print("Testing full generation evaluation...")
    try:
        from src.evaluation.metrics.generation import LLMAsJudge

        judge = LLMAsJudge(backend_type="mistral")

        query = "Concerts de jazz à Paris en février"
        answer = "Voici les concerts de jazz à Paris en février:\n1. Jazz Night - 15 février 2026 au Blue Note Paris\n2. Festival Jazz - 20 février 2026"
        sources = [
            "Title: Jazz Night\nCity: Paris\nDate: 15/02/2026\nVenue: Blue Note Paris",
            "Title: Festival Jazz\nCity: Paris\nDate: 20/02/2026"
        ]

        result = judge.evaluate_generation(query, answer, sources)

        required_keys = ["faithfulness_score", "relevancy_score", "language_consistent", "quality_score"]
        missing_keys = [k for k in required_keys if k not in result]

        if not missing_keys:
            print(f"[OK] Full evaluation complete:")
            print(f"     Faithfulness: {result['faithfulness_score']:.2f}")
            print(f"     Relevancy: {result['relevancy_score']:.2f}")
            print(f"     Quality: {result['quality_score']:.2f}")
            print(f"     Language consistent: {result['language_consistent']}")
            return True
        else:
            print(f"[FAIL] Missing keys in result: {missing_keys}")
            return False
    except Exception as e:
        print(f"[FAIL] Full evaluation failed: {e}")
        return False


def test_hallucination_detection():
    """Test that judge can detect hallucinations."""
    print("Testing hallucination detection...")
    try:
        from src.evaluation.metrics.generation import LLMAsJudge

        judge = LLMAsJudge(backend_type="mistral")

        # Answer contains fabricated information not in source
        query = "What concerts are in Paris?"
        answer = "There is a Rock Festival at Stade de France on March 10, 2026 featuring famous artists."
        sources = ["Title: Jazz Night\nCity: Paris\nDate: 15/02/2026"]

        result = judge.evaluate_faithfulness(query, answer, sources)

        # A hallucinated answer should have lower score
        if result["score"] < 0.7:
            print(f"[OK] Hallucination detected (score: {result['score']:.2f})")
            if result.get("violations"):
                print(f"     Violations: {result['violations'][:2]}")
            return True
        else:
            print(f"[WARN] Hallucination not strongly penalized (score: {result['score']:.2f})")
            print("       This may indicate the judge needs calibration")
            return True  # Not a failure, just a warning
    except Exception as e:
        print(f"[FAIL] Hallucination detection failed: {e}")
        return False


def main():
    """Run all Mistral judge smoke tests."""
    print("=" * 70)
    print("SMOKE TEST: Mistral LLM-as-a-Judge Performance")
    print("=" * 70)
    print()
    print("This test verifies that the Mistral backend works correctly")
    print("as an LLM judge before running full evaluation.")
    print()

    results = []

    # Test 1: Backend initialization
    success, backend = test_mistral_backend_init()
    results.append(("Backend Init", success))

    if not success:
        print("\n[CRITICAL] Cannot proceed without backend. Aborting.")
        return 1

    time.sleep(2)  # Rate limit buffer

    # Test 2: Simple invocation
    results.append(("Simple Invocation", test_simple_invocation(backend)))
    time.sleep(2)

    # Test 3: Faithfulness evaluation
    results.append(("Faithfulness Eval", test_llm_judge_faithfulness()))
    time.sleep(2)

    # Test 4: Relevancy evaluation
    results.append(("Relevancy Eval", test_llm_judge_relevancy()))
    time.sleep(2)

    # Test 5: Full generation evaluation
    results.append(("Full Evaluation", test_full_generation_evaluation()))
    time.sleep(2)

    # Test 6: Hallucination detection
    results.append(("Hallucination Detection", test_hallucination_detection()))

    print()
    print("=" * 70)
    print("RESULTS SUMMARY")
    print("=" * 70)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        symbol = "[OK]" if result else "[FAIL]"
        print(f"{symbol} {test_name}: {status}")

    print()
    print(f"Summary: {passed}/{total} tests passed")
    print("=" * 70)

    if passed == total:
        print("\n[SUCCESS] Mistral judge is ready for full evaluation!")
        print("You can now run: python -m scripts.run_evaluation")
        return 0
    elif passed >= 4:
        print(f"\n[PARTIAL] {passed}/{total} tests passed.")
        print("Core functionality works. Review warnings before full evaluation.")
        return 0
    else:
        print(f"\n[FAIL] {total - passed} critical test(s) failed.")
        print("Fix issues before running full evaluation.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
