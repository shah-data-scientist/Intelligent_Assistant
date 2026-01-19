"""Quick metrics check after hybrid search."""

import logging
import uuid

logging.basicConfig(level=logging.WARNING)

from src.retrieval.chain import RAGChain
from src.evaluation.llm_backends import MistralBackend
from src.evaluation.metrics.generation import LLMAsJudge

# Initialize
chain = RAGChain()
judge_backend = MistralBackend()
judge = LLMAsJudge(backend=judge_backend)

# Test queries (mix of genre-specific and general)
test_queries = [
    "Concerts classiques pour enfants de 6-12 ans le week-end dans le 75",  # Genre-specific
    "Spectacles de jazz gratuits à Paris en février",  # Genre-specific
    "Événements familiaux gratuits à Paris",  # General
    "Expositions d'art contemporain accessible en fauteuil roulant"  # Accessibility
]

print("="*80)
print("POST-HYBRID SEARCH METRICS CHECK")
print("="*80)

all_faithfulness = []
all_relevancy = []

for i, query in enumerate(test_queries, 1):
    print(f"\n[{i}/{len(test_queries)}] Query: {query[:60]}...")

    # Generate answer
    session_id = f"metrics_check_{uuid.uuid4().hex[:8]}"
    result = chain.query_with_metadata(query, session_id=session_id)

    answer = result["answer"]
    sources = result["sources"]

    # Prepare sources for judge
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
    try:
        faith_result = judge.evaluate_faithfulness(
            query=query,
            answer=answer,
            sources=sources_text
        )

        rel_result = judge.evaluate_relevancy(
            query=query,
            answer=answer
        )

        faithfulness = faith_result['score']
        relevancy = rel_result['score']

        all_faithfulness.append(faithfulness)
        all_relevancy.append(relevancy)

        print(f"  Faithfulness: {faithfulness:.2f}")
        print(f"  Relevancy: {relevancy:.2f}")
        print(f"  Quality: {(faithfulness + relevancy) / 2:.2f}")

    except Exception as e:
        print(f"  ERROR: {e}")

# Summary
print("\n" + "="*80)
print("OVERALL METRICS SUMMARY")
print("="*80)

if all_faithfulness and all_relevancy:
    avg_faith = sum(all_faithfulness) / len(all_faithfulness)
    avg_rel = sum(all_relevancy) / len(all_relevancy)
    avg_quality = (avg_faith + avg_rel) / 2

    print(f"\nAverage Faithfulness: {avg_faith:.3f} (target: >0.7) - {'PASS' if avg_faith > 0.7 else 'FAIL'}")
    print(f"Average Relevancy: {avg_rel:.3f} (target: >0.8) - {'PASS' if avg_rel > 0.8 else 'FAIL'}")
    print(f"Average Quality Score: {avg_quality:.3f} (target: >0.8) - {'PASS' if avg_quality > 0.8 else 'FAIL'}")

    print(f"\nFaithfulness Range: {min(all_faithfulness):.2f} - {max(all_faithfulness):.2f}")
    print(f"Relevancy Range: {min(all_relevancy):.2f} - {max(all_relevancy):.2f}")

    print("\n" + "="*80)
    print("COMPARISON TO PREVIOUS RESULTS")
    print("="*80)
    print("\nBefore Hybrid Search (from previous evaluation):")
    print("  - Faithfulness: 0.867")
    print("  - Relevancy: 0.520 (complex queries)")
    print("  - Quality: 0.595-0.700")
    print("\nAfter Hybrid Search:")
    print(f"  - Faithfulness: {avg_faith:.3f}")
    print(f"  - Relevancy: {avg_rel:.3f}")
    print(f"  - Quality: {avg_quality:.3f}")

    faith_change = avg_faith - 0.867
    rel_change = avg_rel - 0.520
    qual_change = avg_quality - 0.650  # Using mid-point of 0.595-0.700

    print(f"\nChange:")
    print(f"  - Faithfulness: {faith_change:+.3f} ({'↑ better' if faith_change > 0 else '↓ worse' if faith_change < 0 else '→ same'})")
    print(f"  - Relevancy: {rel_change:+.3f} ({'↑ better' if rel_change > 0 else '↓ worse' if rel_change < 0 else '→ same'})")
    print(f"  - Quality: {qual_change:+.3f} ({'↑ better' if qual_change > 0 else '↓ worse' if qual_change < 0 else '→ same'})")

print("\n" + "="*80)
