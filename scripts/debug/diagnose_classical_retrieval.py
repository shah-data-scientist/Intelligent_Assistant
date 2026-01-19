"""Diagnose why classical concerts for children aren't being retrieved."""

import logging
import sys
from src.data.storage import EventStorage
from src.models.vector_store import EventVectorStore
from src.retrieval.retriever import EventRetriever
from src.retrieval.chain import RAGChain

# Set UTF-8 encoding for output
if sys.stdout.encoding != 'utf-8':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize storage and vector store
storage = EventStorage()
vector_store = EventVectorStore()
vector_store.load_index()

print("="*80)
print("STEP 1: Database Analysis - Do classical children's events exist?")
print("="*80)

# Search database for classical children's events
all_events = storage.get_all_events()

# Filter for potential classical children's events
# Focus on MUSIC-specific classical keywords to avoid theater/classic confusion
classical_keywords = [
    'musique classique', 'classical music',
    'orchestre', 'orchestra', 'symphony', 'symphonie', 'philharmonic', 'philharmonique',
    'concert classique', 'classical concert',
    'mozart', 'beethoven', 'bach', 'vivaldi', 'haydn', 'schubert',  # Composers
    'quatuor', 'quartet', 'concerto', 'sonate', 'sonata',  # Musical forms
    'opéra', 'opera'  # Opera counts as classical
]
children_keywords = ['enfant', 'children', 'jeune', 'youth', 'famille', 'family', 'tout public', 'jeune public']

classical_events = []
for event in all_events:
    text = f"{event.title} {event.description or ''} {event.scraped_content or ''}".lower()

    # Check for classical keywords
    has_classical = any(kw in text for kw in classical_keywords)
    has_children = any(kw in text for kw in children_keywords)

    if has_classical and has_children:
        classical_events.append(event)

print(f"\nFound {len(classical_events)} events with BOTH classical and children keywords:")
print("-"*80)

for i, event in enumerate(classical_events[:10], 1):  # Show first 10
    try:
        print(f"\n{i}. {event.title}")
        print(f"   Category: {event.category}")
        print(f"   City: {event.location.city if event.location else 'N/A'}")
        print(f"   Date: {event.start_date.strftime('%Y-%m-%d') if event.start_date else 'N/A'}")
        print(f"   Tags: {event.tags[:3] if event.tags else []}")  # Limit tags
        desc = (event.description or event.scraped_content or "")[:150].replace('\n', ' ')
        print(f"   Description: {desc}...")
    except Exception as e:
        print(f"\n{i}. [Error printing event: {e}]")

print("\n" + "="*80)
print("STEP 2: Vector Search Analysis - What does FAISS return?")
print("="*80)

# Test query
query = "Concerts classiques pour enfants de 6-12 ans le week-end dans le 75"
print(f"\nQuery: {query}")

# Refine query
chain = RAGChain()
refined_query = chain.refinement_chain.invoke({"question": query})
print(f"Refined query: {refined_query}")

# Extract filters
filters = chain.extraction_chain.invoke({"question": refined_query})
print(f"Extracted filters: {filters}")

# Clean filters
clean_filters = {k: v for k, v in filters.items() if v}
print(f"Clean filters: {clean_filters}")

# Search with FAISS
print("\nSearching FAISS with refined query and filters...")
results = vector_store.search(refined_query, k=10, metadata_filter=clean_filters)

print(f"\nFAISS returned {len(results)} events:")
print("-"*80)

for i, (event, score) in enumerate(results, 1):
    try:
        print(f"\n{i}. [Score: {score:.3f}] {event.title}")
        print(f"   Category: {event.category}")
        print(f"   City: {event.location.city if event.location else 'N/A'}")
        print(f"   Tags: {event.tags[:3] if event.tags else []}")
        desc = (event.description or event.scraped_content or "")[:150].replace('\n', ' ')
        print(f"   Description: {desc}...")

        # Check if it's actually classical
        text = f"{event.title} {event.description or ''} {event.scraped_content or ''}".lower()
        has_classical = any(kw in text for kw in classical_keywords)
        has_children = any(kw in text for kw in children_keywords)
        print(f"   Match: Classical={has_classical}, Children={has_children}")
    except Exception as e:
        print(f"\n{i}. [Error printing event: {e}]")

print("\n" + "="*80)
print("STEP 3: Semantic Search Analysis - Try without filters")
print("="*80)

# Try search without filters to see if filtering is the issue
print("\nSearching FAISS WITHOUT filters (pure semantic)...")
results_no_filter = vector_store.search(refined_query, k=10, metadata_filter=None)

print(f"\nFAISS returned {len(results_no_filter)} events:")
print("-"*80)

for i, (event, score) in enumerate(results_no_filter, 1):
    try:
        print(f"\n{i}. [Score: {score:.3f}] {event.title}")
        print(f"   Category: {event.category}")
        print(f"   City: {event.location.city if event.location else 'N/A'}")
        print(f"   Tags: {event.tags[:3] if event.tags else []}")

        # Check if it's actually classical
        text = f"{event.title} {event.description or ''} {event.scraped_content or ''}".lower()
        has_classical = any(kw in text for kw in classical_keywords)
        has_children = any(kw in text for kw in children_keywords)
        print(f"   Match: Classical={has_classical}, Children={has_children}")
    except Exception as e:
        print(f"\n{i}. [Error printing event: {e}]")

print("\n" + "="*80)
print("DIAGNOSIS SUMMARY")
print("="*80)
print(f"\nDatabase has {len(classical_events)} classical children's events")
print(f"FAISS with filters returned {len(results)} events")
print(f"FAISS without filters returned {len(results_no_filter)} events")

# Count matches
with_filter_matches = sum(1 for event, _ in results
                          if any(kw in f"{event.title} {event.description or ''} {event.scraped_content or ''}".lower()
                                for kw in classical_keywords))
without_filter_matches = sum(1 for event, _ in results_no_filter
                             if any(kw in f"{event.title} {event.description or ''} {event.scraped_content or ''}".lower()
                                   for kw in classical_keywords))

print(f"\nWith filters: {with_filter_matches}/{len(results)} are actually classical")
print(f"Without filters: {without_filter_matches}/{len(results_no_filter)} are actually classical")

print("\nPOSSIBLE ROOT CAUSES:")
if len(classical_events) == 0:
    print("❌ No classical children's events in database")
elif with_filter_matches == 0 and without_filter_matches > 0:
    print("❌ Filters are too restrictive (blocking classical events)")
elif with_filter_matches == 0 and without_filter_matches == 0:
    print("❌ Semantic embeddings don't capture 'classical' genre distinction")
    print("   → Need genre-aware retrieval or keyword boosting")
else:
    print("✅ Some classical events returned, but ranking might be suboptimal")
