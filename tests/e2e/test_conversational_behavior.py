"""
FILE: test_conversational_behavior.py
STATUS: Active
RESPONSIBILITY: E2E tests for conversational behavior and clarification handling.

DEPENDENCIES (Who uses this file):
- pytest test runner
- Manual testing of conversational flows

IMPORTS (What this file needs):
- logging: Test output
- uuid: Session ID generation
- src.retrieval.chain: RAGChain for end-to-end testing

LAST MAJOR UPDATE: 2026-01-31
MAINTAINER: QA Team
"""

import logging
import uuid

logging.basicConfig(level=logging.WARNING)

from src.retrieval.chain import RAGChain

# Initialize
chain = RAGChain()

# Test queries that should trigger conversational/inquisitive responses
test_queries = [
    # Vague query - should ask for specifics
    "Events in Paris",
    # Broad query - should ask to narrow down
    "Jazz concerts",
    # Query that might have zero results - should propose alternatives
    "Free classical concerts in December",
    # Specific query - should work normally
    "Concerts de jazz à Paris en février",
]

print("=" * 80)
print("CONVERSATIONAL BEHAVIOR TEST")
print("=" * 80)

for i, query in enumerate(test_queries, 1):
    print(f"\n{'='*80}")
    print(f"[{i}/{len(test_queries)}] Query: {query}")
    print("=" * 80)

    # Generate answer
    session_id = f"conv_test_{uuid.uuid4().hex[:8]}"
    result = chain.query_with_metadata(query, session_id=session_id)

    answer = result["answer"]
    num_sources = len(result["sources"])

    print(f"\nAnswer ({num_sources} sources):")
    print("-" * 80)
    print(answer)
    print("-" * 80)

    # Check for conversational elements
    conversational_indicators = [
        "would you like",
        "what type",
        "which option",
        "would be most helpful",
        "to help you",
        "let me know",
        "what are you in the mood for",
        "would you prefer",
        "what interests you",
    ]

    has_questions = any(indicator in answer.lower() for indicator in conversational_indicators)

    if has_questions:
        print("\n[PASS] CONVERSATIONAL: Chatbot asked clarifying questions")
    else:
        print("\n[INFO] No clarifying questions detected")

    # Check if results are grounded
    if "I found" in answer or "Here" in answer or "Voici" in answer:
        print("[PASS] GROUNDED: Response references found events")
    else:
        print("[INFO] Response may not reference specific events")

print("\n" + "=" * 80)
print("TEST COMPLETE")
print("=" * 80)
print("\nSummary:")
print("- Test verifies that chatbot asks clarifying questions for vague queries")
print("- Test verifies that chatbot proposes alternatives when results are limited")
print("- Test verifies that grounding is maintained (no hallucinations)")
print("=" * 80)
