"""Test end-to-end RAG system with hybrid search for classical query."""

import logging
import uuid
from src.retrieval.chain import RAGChain

logging.basicConfig(level=logging.WARNING)  # Reduce noise
logger = logging.getLogger(__name__)

# Initialize chain
chain = RAGChain()

# Test query
query = "Concerts classiques pour enfants de 6-12 ans le week-end dans le 75"

print("="*80)
print("END-TO-END RAG TEST - Classical Music Query with Hybrid Search")
print("="*80)
print(f"\nQuery: {query}")
print(f"Expected: Classical music concerts for children ages 6-12 on weekends in Paris (75)")
print()

# Generate answer with fresh session
session_id = f"test_classical_{uuid.uuid4().hex[:8]}"
result = chain.query_with_metadata(query, session_id=session_id)

answer = result["answer"]
sources = result["sources"]

print("\n" + "="*80)
print("ANSWER")
print("="*80)
print(answer)
print()

print("="*80)
print(f"SOURCES ({len(sources)} events)")
print("="*80)

# Analyze sources
classical_keywords = ['classique', 'classical', 'orchestre', 'mozart', 'opéra', 'opera', 'symphony', 'concert classique']
jazz_keywords = ['jazz']

classical_count = 0
jazz_count = 0
other_count = 0

for i, src in enumerate(sources, 1):
    title = src.get('title', 'N/A')
    city = src.get('city', 'N/A')
    date = src.get('date', 'N/A')
    full_text = src.get('full_text', '').lower()

    is_classical = any(kw in full_text for kw in classical_keywords)
    is_jazz = any(kw in full_text for kw in jazz_keywords)

    if is_classical:
        classical_count += 1
        genre_label = "[CLASSICAL]"
    elif is_jazz:
        jazz_count += 1
        genre_label = "[JAZZ - WRONG]"
    else:
        other_count += 1
        genre_label = "[OTHER]"

    print(f"\n{i}. {genre_label} {title}")
    print(f"   City: {city}")
    print(f"   Date: {date}")

print("\n" + "="*80)
print("ANALYSIS")
print("="*80)
print(f"\nSources Breakdown:")
print(f"  - Classical: {classical_count}/{len(sources)} ({classical_count/len(sources)*100:.0f}%)")
print(f"  - Jazz: {jazz_count}/{len(sources)} ({jazz_count/len(sources)*100:.0f}%)")
print(f"  - Other: {other_count}/{len(sources)} ({other_count/len(sources)*100:.0f}%)")

# Check if answer mentions genres
answer_lower = answer.lower()
mentions_classical = any(kw in answer_lower for kw in ['classique', 'classical', 'orchestre', 'opéra'])
mentions_jazz = 'jazz' in answer_lower

print(f"\nAnswer Content:")
print(f"  - Mentions classical: {'YES' if mentions_classical else 'NO'}")
print(f"  - Mentions jazz: {'YES (WRONG)' if mentions_jazz else 'NO (GOOD)'}")

# Overall assessment
print(f"\nOVERALL ASSESSMENT:")
if classical_count >= 7 and not mentions_jazz:
    print("  SUCCESS - System correctly retrieved classical events and answer is grounded")
    print(f"  Quality: EXCELLENT ({classical_count}/{len(sources)} classical sources)")
elif classical_count >= 4:
    print("  PARTIAL SUCCESS - Some classical events retrieved but could be better")
    print(f"  Quality: GOOD ({classical_count}/{len(sources)} classical sources)")
else:
    print("  FAILURE - Still retrieving mostly non-classical events")
    print(f"  Quality: POOR ({classical_count}/{len(sources)} classical sources)")

print("\n" + "="*80)
