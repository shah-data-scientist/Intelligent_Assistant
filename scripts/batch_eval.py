"""Batch evaluation - runs 5 queries at a time with metrics."""

import os
import sys
import io
import json

# Fix Windows console encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

import requests
import time
from pathlib import Path

API_BASE_URL = "http://localhost:8000"
API_PREFIX = "/api/v1"
API_KEY = "dev-secret-key"  # pragma: allowlist secret

# Load golden dataset
dataset_path = Path(__file__).parent.parent / "evaluation" / "golden_dataset.json"
with open(dataset_path, "r", encoding="utf-8") as f:
    dataset = json.load(f)


def call_api(question: str, session_id: str) -> dict:
    headers = {"X-API-Key": API_KEY, "Content-Type": "application/json"}
    payload = {"question": question, "session_id": session_id}

    start = time.time()
    try:
        response = requests.post(f"{API_BASE_URL}{API_PREFIX}/chat", headers=headers, json=payload, timeout=120)
        latency = (time.time() - start) * 1000
        return {
            "status": response.status_code,
            "latency_ms": latency,
            "data": response.json() if response.status_code == 200 else {"error": response.text},
            "error": None,
        }
    except Exception as e:
        return {"status": 0, "latency_ms": 0, "data": None, "error": str(e)}


def flatten_queries():
    """Flatten conversations and single queries into a list."""
    queries = []

    # From conversations
    for conv in dataset.get("conversations", []):
        session_id = conv["session_id"]
        for turn in conv.get("turns", []):
            queries.append(
                {
                    "id": turn["turn_id"],
                    "query": turn["query"],
                    "session_id": session_id,
                    "turn_type": turn.get("turn_type", "unknown"),
                    "expected_filters": turn.get("expected_filters", {}),
                    "language": conv.get("language", "fr"),
                    "context_dependency": turn.get("context_dependency", None),
                }
            )

    # From single queries
    for sq in dataset.get("single_queries", []):
        queries.append(
            {
                "id": sq["id"],
                "query": sq["query"],
                "session_id": f"single_{sq['id']}",
                "turn_type": "single",
                "expected_filters": sq.get("expected_filters", {}),
                "language": sq.get("language", "fr"),
                "context_dependency": None,
            }
        )

    return queries


def run_batch(queries, batch_num, start_idx):
    """Run a batch of queries and return results."""
    print(f"\n{'='*70}")
    print(f"BATCH {batch_num}: Queries {start_idx+1}-{start_idx+len(queries)}")
    print(f"{'='*70}")

    results = []
    issues = []
    total_latency = 0

    for i, q in enumerate(queries):
        print(f"\n[{start_idx+i+1}] {q['id']} ({q['turn_type']})")
        print(f"    Query: {q['query'][:60]}...")

        result = call_api(q["query"], q["session_id"])
        total_latency += result["latency_ms"]

        if result["error"]:
            print(f"    ERROR: {result['error']}")
            issues.append({"id": q["id"], "type": "connection_error", "detail": result["error"]})
            results.append({"success": False, "latency": 0, "events": 0})
            continue

        if result["status"] != 200:
            error_msg = result["data"].get("error", str(result["data"]))[:100]
            print(f"    FAILED: HTTP {result['status']} - {error_msg}")
            issues.append({"id": q["id"], "type": f"http_{result['status']}", "detail": error_msg})
            results.append({"success": False, "latency": result["latency_ms"], "events": 0})
            continue

        data = result["data"]
        events = len(data.get("sources", []))
        answer = data.get("answer", "")

        print(f"    Status: 200 | Latency: {result['latency_ms']:.0f}ms | Events: {events}")

        # Check for issues
        success = True

        # 1. Check for out_of_scope errors
        if "out_of_scope" in answer.lower() or "outside" in answer.lower():
            expected_city = q["expected_filters"].get("city")
            print(f"    ISSUE: Out of scope (expected city: {expected_city})")
            issues.append({"id": q["id"], "type": "out_of_scope", "detail": f"City '{expected_city}' not recognized"})
            success = False

        # 2. Check if expected city is in results
        elif q["expected_filters"].get("city"):
            expected_city = q["expected_filters"]["city"]
            sources = data.get("sources", [])
            cities = set(s.get("city") for s in sources)
            if expected_city not in cities and events > 0:
                print(f"    ISSUE: Expected city '{expected_city}' not in results: {cities}")
                issues.append(
                    {"id": q["id"], "type": "wrong_city", "detail": f"Expected '{expected_city}', got {cities}"}
                )
                # Not a failure if we got results from nearby cities
                success = events > 0

        # 3. Check latency
        if result["latency_ms"] > 5000:
            print(f"    ISSUE: High latency ({result['latency_ms']:.0f}ms > 5000ms)")
            issues.append({"id": q["id"], "type": "high_latency", "detail": f"{result['latency_ms']:.0f}ms"})

        # 4. Check for no results (potential issue)
        # Note: follow_up queries (coreference) correctly return 0 events but provide details in answer
        is_follow_up = q["turn_type"] == "follow_up"
        has_event_details = any(
            kw in answer.lower()
            for kw in ["openagenda.com", "plus d'info", "more info", "prix", "price", "date", "lieu", "location"]
        )

        if events == 0 and "clarif" not in answer.lower():
            if is_follow_up and has_event_details:
                # Coreference query with event details - this is success
                print("    OK: Follow-up query resolved (event details in answer)")
            else:
                print("    ISSUE: No events returned")
                issues.append(
                    {"id": q["id"], "type": "no_results", "detail": "Query returned 0 events without clarification"}
                )
                success = False

        results.append({"success": success, "latency": result["latency_ms"], "events": events})

    return results, issues, total_latency


def print_batch_metrics(results, issues, total_latency, batch_num):
    """Print metrics for a batch."""
    print(f"\n{'-'*70}")
    print(f"BATCH {batch_num} METRICS:")
    print(f"{'-'*70}")

    success_count = sum(1 for r in results if r["success"])
    total = len(results)
    avg_latency = total_latency / total if total > 0 else 0
    avg_events = sum(r["events"] for r in results) / total if total > 0 else 0

    print(f"  Success Rate: {success_count}/{total} ({100*success_count/total:.0f}%)")
    print(f"  Avg Latency:  {avg_latency:.0f}ms")
    print(f"  Avg Events:   {avg_events:.1f}")

    if issues:
        print(f"\n  ISSUES FOUND ({len(issues)}):")
        # Group by type
        by_type = {}
        for issue in issues:
            t = issue["type"]
            if t not in by_type:
                by_type[t] = []
            by_type[t].append(issue)

        for issue_type, items in by_type.items():
            print(f"    - {issue_type}: {len(items)} occurrences")
            for item in items[:3]:  # Show max 3 examples
                print(f"        {item['id']}: {item['detail'][:50]}")
    else:
        print("\n  No issues found!")

    return success_count, total


# Main execution
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--batch", type=int, default=1, help="Which batch to run (1, 2, 3, ...)")
    parser.add_argument("--batch-size", type=int, default=5, help="Queries per batch")
    args = parser.parse_args()

    all_queries = flatten_queries()
    print(f"Total queries in dataset: {len(all_queries)}")

    batch_size = args.batch_size
    batch_num = args.batch
    start_idx = (batch_num - 1) * batch_size
    end_idx = min(start_idx + batch_size, len(all_queries))

    if start_idx >= len(all_queries):
        print(f"Batch {batch_num} is out of range. Max batch: {(len(all_queries)-1)//batch_size + 1}")
        sys.exit(1)

    batch_queries = all_queries[start_idx:end_idx]
    results, issues, total_latency = run_batch(batch_queries, batch_num, start_idx)
    success, total = print_batch_metrics(results, issues, total_latency, batch_num)

    print(f"\n{'='*70}")
    print(f"Next batch: python scripts/batch_eval.py --batch {batch_num + 1}")
    print(f"{'='*70}")
