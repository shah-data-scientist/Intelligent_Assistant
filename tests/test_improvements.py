"""Test keyword preservation and caching improvements."""

import logging
import time
import uuid
from src.retrieval.chain import RAGChain

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

print("="*80)
print("TESTING IMPROVEMENTS: Keyword Preservation + Caching")
print("="*80)

# Initialize chain with caching enabled
chain = RAGChain(enable_cache=True, cache_ttl_minutes=60)

# Test 1: Keyword preservation in refinement
print("\n1. TESTING KEYWORD PRESERVATION")
print("-"*80)

test_query = "Concerts classiques pour enfants de 6-12 ans le week-end dans le 75"
print(f"Query: {test_query}")

refined = chain.refinement_chain.invoke({"question": test_query})
print(f"Refined: {refined}")

# Check keyword preservation
if "classique" in refined.lower():
    print("  ✓ Genre 'classique' PRESERVED")
else:
    print("  ✗ Genre 'classique' LOST")

if "enfants" in refined.lower():
    print("  ✓ Age 'enfants' PRESERVED")
else:
    print("  ✗ Age 'enfants' LOST")

# Test 2: Caching performance
print("\n2. TESTING QUERY CACHING")
print("-"*80)

session_id = f"test_{uuid.uuid4().hex[:8]}"
test_query_cache = "Concerts de jazz à Paris en février"

print(f"Query: {test_query_cache}")
print(f"Session: {session_id}")

# First query (cache MISS)
print("\nFirst execution (cache MISS expected)...")
start = time.time()
result1 = chain.query_with_metadata(test_query_cache, session_id=session_id)
latency1 = (time.time() - start) * 1000
print(f"  Latency: {latency1:.0f}ms")
print(f"  Answer length: {len(result1['answer'])} chars")

# Second query (cache HIT)
print("\nSecond execution (cache HIT expected)...")
start = time.time()
result2 = chain.query_with_metadata(test_query_cache, session_id=session_id)
latency2 = (time.time() - start) * 1000
print(f"  Latency: {latency2:.0f}ms")
print(f"  Answer length: {len(result2['answer'])} chars")

# Verify caching worked
speedup = latency1 / latency2 if latency2 > 0 else 0
print(f"\nSpeedup: {speedup:.1f}x")
if latency2 < 100:  # Cache hit should be < 100ms
    print("  ✓ Caching WORKING (near-instant response)")
else:
    print("  ✗ Caching may not be working (slow response)")

# Verify answers are identical
if result1['answer'] == result2['answer']:
    print("  ✓ Cached answer IDENTICAL to original")
else:
    print("  ✗ Cached answer DIFFERENT from original")

# Cache stats
if chain.cache:
    stats = chain.cache.get_stats()
    print(f"\nCache stats: {stats['size']} entries, {stats['total_hits']} hits")

print("\n" + "="*80)
print("TEST COMPLETE")
print("="*80)
