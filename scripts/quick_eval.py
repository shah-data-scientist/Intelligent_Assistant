"""Quick evaluation of a few test queries."""
import os
import sys
import io

# Fix Windows console encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

import requests
import time

API_BASE_URL = "http://localhost:8000"
API_PREFIX = "/api/v1"
API_KEY = "dev-secret-key"

TEST_QUERIES = [
    {"query": "Concerts de jazz à Paris", "expected_city": "Paris", "expected_category": "Musique"},
    {"query": "Expositions à Versailles", "expected_city": "Versailles", "expected_category": "Art / Exposition"},
    {"query": "Théâtre ce weekend à Paris", "expected_city": "Paris", "expected_category": "Théâtre / Spectacle"},
    {"query": "Jazz concerts in Paris this weekend", "expected_city": "Paris", "expected_category": "Musique"},
    {"query": "What's happening in Poissy?", "expected_city": "Poissy", "expected_category": None},
]

def call_api(question: str, session_id: str) -> dict:
    headers = {"X-API-Key": API_KEY, "Content-Type": "application/json"}
    payload = {"question": question, "session_id": session_id}

    start = time.time()
    try:
        response = requests.post(
            f"{API_BASE_URL}{API_PREFIX}/chat",
            headers=headers,
            json=payload,
            timeout=120
        )
        latency = (time.time() - start) * 1000
        return {
            "status": response.status_code,
            "latency_ms": latency,
            "data": response.json() if response.status_code == 200 else response.text,
            "error": None
        }
    except Exception as e:
        return {"status": 0, "latency_ms": 0, "data": None, "error": str(e)}

print("=" * 70)
print("QUICK EVALUATION - Testing Core Functionality")
print("=" * 70)

passed = 0
failed = 0

for i, test in enumerate(TEST_QUERIES, 1):
    print(f"\n[Test {i}/{len(TEST_QUERIES)}] {test['query'][:50]}...")
    result = call_api(test['query'], f"test-session-{i}")

    if result['error']:
        print(f"  ERROR: {result['error']}")
        failed += 1
        continue

    if result['status'] != 200:
        print(f"  FAILED: HTTP {result['status']}")
        print(f"  Response: {str(result['data'])[:200]}")
        failed += 1
        continue

    data = result['data']
    events_count = len(data.get('sources', []))
    answer_preview = data.get('answer', '')[:100].replace('\n', ' ')

    print(f"  Status: {result['status']} | Latency: {result['latency_ms']:.0f}ms | Events: {events_count}")
    print(f"  Answer: {answer_preview}...")

    # Check if we got events with expected city
    sources = data.get('sources', [])
    if sources:
        cities = set(s.get('city') for s in sources)
        print(f"  Cities in results: {cities}")
        if test['expected_city'] and test['expected_city'] in cities:
            print(f"  [PASS] Expected city '{test['expected_city']}' found")
            passed += 1
        elif test['expected_city']:
            print(f"  [FAIL] Expected city '{test['expected_city']}' NOT in results")
            failed += 1
        else:
            print(f"  [PASS] Got results (no specific city expected)")
            passed += 1
    else:
        if "out_of_scope" in data.get('answer', '').lower() or "outside" in data.get('answer', '').lower():
            print(f"  [FAIL] Out of scope response - city not recognized")
            failed += 1
        else:
            print(f"  [FAIL] No events returned")
            failed += 1

print("\n" + "=" * 70)
print(f"RESULTS: {passed}/{len(TEST_QUERIES)} passed, {failed}/{len(TEST_QUERIES)} failed")
print("=" * 70)
