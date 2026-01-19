"""Diagnostic script to understand judge scoring."""

import logging
import uuid
from src.retrieval.chain import RAGChain
from src.evaluation.llm_backends import MistralBackend
from src.evaluation.metrics.generation import LLMAsJudge

logging.basicConfig(level=logging.WARNING)  # Reduce noise

# Initialize
chain = RAGChain()
judge_backend = MistralBackend()
judge = LLMAsJudge(backend=judge_backend)

# Test query - Try high-complexity multi-criteria type
query = "Concerts classiques pour enfants de 6-12 ans le week-end dans le 75"

print("="*80)
print(f"QUERY: {query}")
print("="*80)

# Generate answer with fresh session to avoid history influence
session_id = f"diagnostic_{uuid.uuid4().hex[:8]}"
result = chain.query_with_metadata(query, session_id=session_id)
answer = result["answer"]
sources = result["sources"]

print(f"\nANSWER ({len(answer)} chars):")
print("-"*80)
print(answer)
print()

print(f"\nSOURCES ({len(sources)} events):")
print("-"*80)
for i, src in enumerate(sources, 1):
    print(f"\nSource {i}:")
    print(f"  Title: {src.get('title', 'N/A')}")
    print(f"  City: {src.get('city', 'N/A')}")
    print(f"  Date: {src.get('date', 'N/A')}")
    print(f"  URL: {src.get('url', 'N/A')}")
    if 'full_text' in src:
        full_text = src['full_text']
        print(f"  Full text ({len(full_text)} chars): {full_text[:200]}...")

# Prepare sources for judge (same as evaluator does)
sources_text = []
for src in sources:
    if "full_text" in src and src["full_text"]:
        sources_text.append(src["full_text"])
    else:
        source_text = f"Title: {src.get('title', 'N/A')}\n"
        source_text += f"City: {src.get('city', 'N/A')}\n"
        source_text += f"Date: {src.get('date', 'N/A')}\n"
        source_text += f"URL: {src.get('url', 'N/A')}"
        sources_text.append(source_text)

# Evaluate
print("\n" + "="*80)
print("JUDGE EVALUATION")
print("="*80)

try:
    # Faithfulness
    faith_result = judge.evaluate_faithfulness(
        query=query,
        answer=answer,
        sources=sources_text
    )

    print(f"\nFAITHFULNESS SCORE: {faith_result['score']:.2f}")
    print(f"Reasoning: {faith_result.get('reasoning', 'N/A')}")
    print(f"Violations ({len(faith_result.get('violations', []))}):")
    for v in faith_result.get('violations', []):
        print(f"  - {v}")

    # Relevancy
    rel_result = judge.evaluate_relevancy(
        query=query,
        answer=answer
    )

    print(f"\nRELEVANCY SCORE: {rel_result['score']:.2f}")
    print(f"Reasoning: {rel_result.get('reasoning', 'N/A')}")
    print(f"Strengths: {rel_result.get('strengths', [])}")
    print(f"Weaknesses: {rel_result.get('weaknesses', [])}")

except Exception as e:
    print(f"\nERROR: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*80)
print("ANALYSIS")
print("="*80)
print("\nIf faithfulness is low, check:")
print("1. Are violations legitimate? (answer contains info not in sources)")
print("2. Is judge too strict? (penalizing paraphrasing/formatting)")
print("3. Are sources complete? (full_text includes all event details)")
print("\nIf relevancy is low, check:")
print("1. Does answer address ALL parts of the query?")
print("2. Does answer provide actionable information (dates, locations, links)?")
print("3. Is answer well-structured and clear?")
