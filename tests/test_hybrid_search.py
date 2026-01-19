"""Test hybrid search with genre boosting."""

import logging
from src.models.vector_store import EventVectorStore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize vector store
vector_store = EventVectorStore()
vector_store.load_index()

# Test query
query = "concerts classique enfants 6-12 ans week-end 75"

print("="*80)
print("HYBRID SEARCH TEST - Classical vs Jazz Retrieval")
print("="*80)
print(f"\nQuery: {query}")
print(f"Expected: Classical music events for children")
print()

# Test 1: WITHOUT hybrid (semantic only)
print("\n" + "="*80)
print("TEST 1: Semantic Search ONLY (enable_hybrid=False)")
print("="*80)

results_semantic = vector_store.search(
    query,
    k=10,
    metadata_filter={'city': 'Paris'},
    enable_hybrid=False
)

print(f"\nFound {len(results_semantic)} events:")
print("-"*80)

classical_keywords = ['classique', 'classical', 'orchestre', 'mozart', 'opéra', 'opera', 'symphony', 'concert classique']
jazz_keywords = ['jazz']

classical_count_sem = 0
jazz_count_sem = 0

for i, (event, score) in enumerate(results_semantic, 1):
    text = f"{event.title} {event.description or ''} {event.tags or []}".lower()
    is_classical = any(kw in text for kw in classical_keywords)
    is_jazz = any(kw in text for kw in jazz_keywords)

    if is_classical:
        classical_count_sem += 1
        genre_label = "[CLASSICAL]"
    elif is_jazz:
        jazz_count_sem += 1
        genre_label = "[JAZZ - WRONG]"
    else:
        genre_label = "[OTHER]"

    print(f"\n{i}. [Score: {score:.3f}] {genre_label}")
    print(f"   {event.title}")
    print(f"   Category: {event.category}")
    print(f"   Tags: {event.tags[:3] if event.tags else []}")

print(f"\nResults: {classical_count_sem} classical, {jazz_count_sem} jazz, {len(results_semantic) - classical_count_sem - jazz_count_sem} other")

# Test 2: WITH hybrid (semantic + genre boosting)
print("\n" + "="*80)
print("TEST 2: HYBRID Search (enable_hybrid=True)")
print("="*80)

results_hybrid = vector_store.search(
    query,
    k=10,
    metadata_filter={'city': 'Paris'},
    enable_hybrid=True
)

print(f"\nFound {len(results_hybrid)} events:")
print("-"*80)

classical_count_hyb = 0
jazz_count_hyb = 0

for i, (event, score) in enumerate(results_hybrid, 1):
    text = f"{event.title} {event.description or ''} {event.tags or []}".lower()
    is_classical = any(kw in text for kw in classical_keywords)
    is_jazz = any(kw in text for kw in jazz_keywords)

    if is_classical:
        classical_count_hyb += 1
        genre_label = "[CLASSICAL]"
    elif is_jazz:
        jazz_count_hyb += 1
        genre_label = "[JAZZ - WRONG]"
    else:
        genre_label = "[OTHER]"

    print(f"\n{i}. [Score: {score:.3f}] {genre_label}")
    print(f"   {event.title}")
    print(f"   Category: {event.category}")
    print(f"   Tags: {event.tags[:3] if event.tags else []}")

print(f"\nResults: {classical_count_hyb} classical, {jazz_count_hyb} jazz, {len(results_hybrid) - classical_count_hyb - jazz_count_hyb} other")

# Summary
print("\n" + "="*80)
print("COMPARISON SUMMARY")
print("="*80)
print(f"\nSemantic Only:  {classical_count_sem} classical / {jazz_count_sem} jazz")
print(f"Hybrid Search:  {classical_count_hyb} classical / {jazz_count_hyb} jazz")
print()

if classical_count_hyb > classical_count_sem:
    print("SUCCESS: Hybrid search found MORE classical events!")
    print(f"   Improvement: +{classical_count_hyb - classical_count_sem} classical events")
elif classical_count_hyb == classical_count_sem:
    print("NEUTRAL: No change in classical event count")
else:
    print("REGRESSION: Hybrid search found FEWER classical events")

if jazz_count_hyb < jazz_count_sem:
    print(f"SUCCESS: Hybrid search reduced jazz events by {jazz_count_sem - jazz_count_hyb}")
elif jazz_count_hyb == jazz_count_sem:
    print("NEUTRAL: No change in jazz event count")
else:
    print(f"REGRESSION: Hybrid search increased jazz events by {jazz_count_hyb - jazz_count_sem}")

print("\n" + "="*80)
