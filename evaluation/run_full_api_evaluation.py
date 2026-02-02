"""
FILE: run_full_api_evaluation.py
STATUS: Active
RESPONSIBILITY: Runs full golden dataset evaluation through production API with detailed metrics
LAST MAJOR UPDATE: 2026-02-01
MAINTAINER: Team
"""

import sys
import io
import json
import time
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional

# Setup
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from dotenv import load_dotenv
import os
import requests
load_dotenv(project_root / ".env", override=True)

# API Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8001")
API_PREFIX = "/api/v1"
API_KEY = os.getenv("APP_API_KEY", "dev-secret-key")

# Import evaluation components
from src.evaluation.datasets.golden_dataset import GoldenDataset
from src.evaluation.metrics.generation import LLMAsJudge


@dataclass
class QueryResult:
    """Result of a single query evaluation."""
    query_id: str
    query: str
    query_type: str
    language: str
    http_status: int
    latency_ms: float
    events_retrieved: int
    answer: str
    sources: List[Dict]
    error: Optional[str] = None
    faithfulness_score: float = 0.0
    relevancy_score: float = 0.0
    quality_score: float = 0.0
    judge_reasoning: str = ""
    expected_filters: Dict = None
    actual_filters_in_response: str = ""


def check_api_health():
    """Check if API is running."""
    try:
        response = requests.get(f"{API_BASE_URL}{API_PREFIX}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            return data.get("rag_system") == "initialized"
    except requests.exceptions.ConnectionError:
        return False
    return False


def call_api(question: str, session_id: str) -> tuple:
    """Call the chat API and return response + latency."""
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
        return response, latency, None
    except Exception as e:
        latency = (time.time() - start) * 1000
        return None, latency, str(e)


def evaluate_single_query(query, judge: LLMAsJudge, session_id: str) -> QueryResult:
    """Evaluate a single query through the API."""
    response, latency, error = call_api(query.query, session_id)

    result = QueryResult(
        query_id=query.id,
        query=query.query,
        query_type=query.query_type,
        language=query.language,
        http_status=response.status_code if response else 0,
        latency_ms=latency,
        events_retrieved=0,
        answer="",
        sources=[],
        error=error,
        expected_filters=query.expected_filters
    )

    if error or not response or response.status_code != 200:
        result.error = error or f"HTTP {response.status_code}: {response.text[:200]}"
        return result

    try:
        data = response.json()
        result.answer = data.get("answer", "")
        result.sources = data.get("sources", [])
        result.events_retrieved = len(result.sources)

        # Extract filters from response (look for "Filtres appliqués" line)
        for line in result.answer.split('\n'):
            if "Filtres appliqués" in line:
                result.actual_filters_in_response = line
                break

        # LLM Judge evaluation
        if result.answer and result.sources:
            source_texts = [
                f"Title: {s.get('title', 'N/A')}\nCity: {s.get('city', 'N/A')}\n"
                f"Date: {s.get('date', 'N/A')}\nCategory: {s.get('category', 'N/A')}"
                for s in result.sources[:5]
            ]

            # Faithfulness
            faith_result = judge.evaluate_faithfulness(query.query, result.answer, source_texts)
            result.faithfulness_score = faith_result.get("score", 0)

            # Rate limit pause between LLM judge calls
            time.sleep(3)

            # Relevancy
            rel_result = judge.evaluate_relevancy(query.query, result.answer)
            result.relevancy_score = rel_result.get("score", 0)

            # Combined quality
            result.quality_score = (result.faithfulness_score + result.relevancy_score) / 2
            result.judge_reasoning = faith_result.get("reasoning", "")[:200]

    except Exception as e:
        result.error = f"Parse error: {e}"

    return result


def run_evaluation(dataset: GoldenDataset, judge: LLMAsJudge) -> List[QueryResult]:
    """Run evaluation on all queries."""
    results = []
    total = len(dataset.queries)

    print(f"\nEvaluating {total} queries...")
    print("=" * 60)

    for i, query in enumerate(dataset.queries, 1):
        # Use session_id based on conversation if available
        session_id = query.session_id or f"eval_{query.id}"

        print(f"\n[{i}/{total}] {query.id}: {query.query[:50]}...")

        result = evaluate_single_query(query, judge, session_id)

        status = "✅" if result.quality_score >= 0.5 else "⚠️" if result.quality_score > 0 else "❌"
        print(f"  {status} Quality: {result.quality_score:.2f} | "
              f"Events: {result.events_retrieved} | Latency: {result.latency_ms:.0f}ms")

        if result.error:
            print(f"  ❌ Error: {result.error[:80]}")

        results.append(result)

        # Rate limiting pause (increased to avoid 429 errors)
        time.sleep(10)

    return results


def generate_report(results: List[QueryResult], dataset: GoldenDataset) -> Dict:
    """Generate comprehensive evaluation report."""

    # Query types to EXCLUDE from quality metrics (these intentionally return no events)
    # Greetings, off-topic, capability questions, and security blocks are correct behavior
    EXCLUDE_FROM_QUALITY = [
        "greeting",           # "Bonjour", "Hello" - no events expected
        "off_topic",          # "What's the weather?" - correctly rejected
        "capability",         # "What can you do?" - capability explanation
        "meta",               # Meta questions about the system
        "security_injection", # Prompt injection - correctly blocked (HTTP 400/403)
        "security_profanity", # Profanity - correctly blocked
        "out_of_scope_city",  # Cities outside IDF - correctly rejected
    ]

    # Basic stats
    total = len(results)
    successful = [r for r in results if not r.error and r.http_status == 200]
    failed = [r for r in results if r.error or r.http_status != 200]

    # Separate event-related queries from non-event queries
    event_queries = [r for r in successful if r.query_type not in EXCLUDE_FROM_QUALITY]
    excluded_queries = [r for r in results if r.query_type in EXCLUDE_FROM_QUALITY]

    # Quality metrics - ONLY for event-related queries
    quality_scores = [r.quality_score for r in event_queries if r.quality_score > 0]
    faith_scores = [r.faithfulness_score for r in event_queries if r.faithfulness_score > 0]
    rel_scores = [r.relevancy_score for r in event_queries if r.relevancy_score > 0]
    latencies = [r.latency_ms for r in successful]  # Latency includes all queries

    avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0
    avg_faith = sum(faith_scores) / len(faith_scores) if faith_scores else 0
    avg_rel = sum(rel_scores) / len(rel_scores) if rel_scores else 0
    avg_latency = sum(latencies) / len(latencies) if latencies else 0

    # Breakdown by query type
    by_type = {}
    for r in results:
        t = r.query_type
        if t not in by_type:
            by_type[t] = {"count": 0, "quality_sum": 0, "success": 0, "fail": 0}
        by_type[t]["count"] += 1
        by_type[t]["quality_sum"] += r.quality_score
        if r.error:
            by_type[t]["fail"] += 1
        else:
            by_type[t]["success"] += 1

    for t in by_type:
        by_type[t]["avg_quality"] = by_type[t]["quality_sum"] / by_type[t]["count"]

    # Find issues
    low_quality = [r for r in results if r.quality_score < 0.5 and not r.error]
    no_events = [r for r in results if r.events_retrieved == 0 and not r.error]
    high_latency = [r for r in results if r.latency_ms > 30000]

    report = {
        "timestamp": datetime.now().isoformat(),
        "dataset_version": dataset.version,
        "total_queries": total,
        "summary": {
            "successful_queries": len(successful),
            "failed_queries": len(failed),
            "success_rate": len(successful) / total if total > 0 else 0,
            # Quality metrics now exclude non-event queries
            "event_queries_evaluated": len(event_queries),
            "excluded_from_quality": len(excluded_queries),
            "avg_quality_score": avg_quality,
            "avg_faithfulness": avg_faith,
            "avg_relevancy": avg_rel,
            "avg_latency_ms": avg_latency,
            "p95_latency_ms": sorted(latencies)[int(len(latencies) * 0.95)] if latencies else 0,
            "quality_pass_rate": len([q for q in quality_scores if q >= 0.5]) / len(quality_scores) if quality_scores else 0,
        },
        "by_query_type": by_type,
        "issues": {
            "low_quality_queries": [{"id": r.query_id, "query": r.query, "score": r.quality_score} for r in low_quality[:10]],
            "no_events_queries": [{"id": r.query_id, "query": r.query} for r in no_events[:10]],
            "high_latency_queries": [{"id": r.query_id, "latency_ms": r.latency_ms} for r in high_latency[:10]],
            "failed_queries": [{"id": r.query_id, "error": r.error} for r in failed[:10]],
        },
        "detailed_results": [asdict(r) for r in results]
    }

    return report


def write_markdown_report(report: Dict, output_path: Path):
    """Write a human-readable markdown report."""
    s = report["summary"]

    md = f"""# API Evaluation Report

**Date:** {report['timestamp']}
**Dataset Version:** {report['dataset_version']}
**Total Queries:** {report['total_queries']}

---

## Executive Summary

**Note:** Quality metrics are calculated on **event-related queries only** ({s.get('event_queries_evaluated', 'N/A')} queries).
Non-event queries ({s.get('excluded_from_quality', 'N/A')} queries) like greetings, off-topic, and security tests are excluded.

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| Success Rate | {s['success_rate']*100:.1f}% | ≥95% | {'✅' if s['success_rate'] >= 0.95 else '❌'} |
| Avg Quality Score | {s['avg_quality_score']:.2f} | ≥0.7 | {'✅' if s['avg_quality_score'] >= 0.7 else '❌'} |
| Avg Faithfulness | {s['avg_faithfulness']:.2f} | ≥0.7 | {'✅' if s['avg_faithfulness'] >= 0.7 else '❌'} |
| Avg Relevancy | {s['avg_relevancy']:.2f} | ≥0.7 | {'✅' if s['avg_relevancy'] >= 0.7 else '❌'} |
| Avg Latency | {s['avg_latency_ms']:.0f}ms | <5000ms | {'✅' if s['avg_latency_ms'] < 5000 else '❌'} |
| P95 Latency | {s['p95_latency_ms']:.0f}ms | <10000ms | {'✅' if s['p95_latency_ms'] < 10000 else '❌'} |
| Quality Pass Rate | {s['quality_pass_rate']*100:.1f}% | ≥70% | {'✅' if s['quality_pass_rate'] >= 0.7 else '❌'} |

---

## Performance by Query Type

| Type | Count | Avg Quality | Success | Fail |
|------|-------|-------------|---------|------|
"""

    for t, data in report["by_query_type"].items():
        md += f"| {t} | {data['count']} | {data['avg_quality']:.2f} | {data['success']} | {data['fail']} |\n"

    md += f"""
---

## Issues Identified

### Low Quality Responses ({len(report['issues']['low_quality_queries'])} found)
"""
    for q in report['issues']['low_quality_queries'][:5]:
        md += f"- **{q['id']}**: \"{q['query'][:50]}...\" (score: {q['score']:.2f})\n"

    md += f"""
### No Events Retrieved ({len(report['issues']['no_events_queries'])} found)
"""
    for q in report['issues']['no_events_queries'][:5]:
        md += f"- **{q['id']}**: \"{q['query'][:50]}...\"\n"

    md += f"""
### High Latency (>30s) ({len(report['issues']['high_latency_queries'])} found)
"""
    for q in report['issues']['high_latency_queries'][:5]:
        md += f"- **{q['id']}**: {q['latency_ms']:.0f}ms\n"

    md += f"""
### Failed Queries ({len(report['issues']['failed_queries'])} found)
"""
    for q in report['issues']['failed_queries'][:5]:
        md += f"- **{q['id']}**: {q['error'][:80]}\n"

    md += """
---

## Root Cause Analysis

Based on the evaluation results, the following issues need attention:

"""

    # Add root cause analysis based on metrics
    if s['avg_faithfulness'] < 0.5:
        md += "### 1. Low Faithfulness (Hallucination Risk)\n"
        md += "- LLM is generating information not grounded in retrieved documents\n"
        md += "- **Action:** Review RAG prompt to emphasize source-only responses\n\n"

    if s['avg_relevancy'] < 0.5:
        md += "### 2. Low Relevancy\n"
        md += "- Responses don't adequately address user queries\n"
        md += "- **Action:** Improve query understanding and retrieval matching\n\n"

    if s['avg_latency_ms'] > 10000:
        md += "### 3. High Latency\n"
        md += "- API response times exceed acceptable thresholds\n"
        md += "- **Action:** Optimize LLM calls, add caching, reduce token usage\n\n"

    if len(report['issues']['no_events_queries']) > 5:
        md += "### 4. Empty Results Issue\n"
        md += "- Many queries return no events\n"
        md += "- **Action:** Review filter logic and fallback mechanisms\n\n"

    md += """
---

## Recommended Action Plan

1. **Immediate (P0):**
   - Fix any failing queries (HTTP errors, timeouts)
   - Review prompts for low faithfulness issues

2. **Short-term (P1):**
   - Optimize latency (caching, prompt reduction)
   - Improve retrieval relevancy

3. **Medium-term (P2):**
   - Expand test coverage for edge cases
   - Add automated regression testing

---

*Generated by run_full_api_evaluation.py*
"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(md)


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="Limit number of queries")
    args = parser.parse_args()

    print("=" * 70)
    print("  FULL API EVALUATION - Golden Dataset")
    print("=" * 70)

    # Check API health
    print("\nChecking API health...")
    if not check_api_health():
        print("❌ API is not running. Start it with:")
        print("   VIRTUAL_ENV=$(pwd)/.venv poetry run uvicorn src.api.main:app --port 8001")
        return 1

    print("✅ API is healthy")

    # Load golden dataset
    dataset_path = project_root / "evaluation" / "golden_dataset.json"
    print(f"\nLoading golden dataset from: {dataset_path}")
    dataset = GoldenDataset.load(dataset_path)

    if args.limit:
        dataset = dataset.get_subset(n=args.limit)
        print(f"✅ Loaded {dataset.total_queries} queries (limited to {args.limit})")
    else:
        print(f"✅ Loaded {dataset.total_queries} queries")

    # Initialize LLM judge (using Gemini - same API as main RAG system)
    print("\nInitializing Gemini LLM judge (uses existing GOOGLE_API_KEY)...")
    judge = LLMAsJudge(backend_type="gemini")
    print("✅ Judge ready")

    # Run evaluation
    results = run_evaluation(dataset, judge)

    # Generate report
    print("\n" + "=" * 70)
    print("Generating report...")

    report = generate_report(results, dataset)

    # Save JSON report
    json_path = project_root / "evaluation" / "reports" / f"api_evaluation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    json_path.parent.mkdir(exist_ok=True)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False, default=str)
    print(f"✅ JSON report: {json_path}")

    # Save Markdown report
    md_path = project_root / "evaluation" / "reports" / f"api_evaluation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    write_markdown_report(report, md_path)
    print(f"✅ Markdown report: {md_path}")

    # Print summary
    s = report["summary"]
    print("\n" + "=" * 70)
    print("EVALUATION SUMMARY")
    print("=" * 70)
    print(f"  Success Rate: {s['success_rate']*100:.1f}%")
    print(f"  Avg Quality: {s['avg_quality_score']:.2f}")
    print(f"  Avg Faithfulness: {s['avg_faithfulness']:.2f}")
    print(f"  Avg Relevancy: {s['avg_relevancy']:.2f}")
    print(f"  Avg Latency: {s['avg_latency_ms']:.0f}ms")
    print(f"  Quality Pass Rate: {s['quality_pass_rate']*100:.1f}%")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(main())
