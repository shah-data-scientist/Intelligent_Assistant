#!/usr/bin/env python
"""Batch trace execution for all single-turn queries from the golden dataset.

This script runs detailed traces for all 55 single-turn queries and generates:
1. Individual trace files for each query
2. analysis_report.md with findings
3. summary.json with machine-readable results
"""

import sys
import os
import io
import json
import time
import logging
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load .env BEFORE importing src modules
from dotenv import load_dotenv

load_dotenv(project_root / ".env", override=True)

# CRITICAL: Force load API key from .env to override Windows env var
env_file = project_root / ".env"
if env_file.exists():
    with open(env_file, "r") as f:
        for line in f:
            if line.startswith("GOOGLE_API_KEY="):
                os.environ["GOOGLE_API_KEY"] = line.strip().split("=", 1)[1]
                break

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# Configure logging
logging.basicConfig(
    level=logging.WARNING, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"  # Reduce noise
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

from src.retrieval.chain import RAGChain
from src.retrieval.unified_analyzer import unified_analyze
from src.security.guardrails import check_safety, SecurityException

# Output directories
OUTPUT_DIR = project_root / "data" / "evaluation" / "reports" / "single_turn_traces"
TRACES_DIR = OUTPUT_DIR / "traces"
GOLDEN_DATASET_PATH = project_root / "data" / "evaluation" / "golden_dataset.json"


def load_golden_dataset() -> dict:
    """Load the golden dataset JSON."""
    with open(GOLDEN_DATASET_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def run_single_trace(chain: RAGChain, query_data: dict, trace_file: Path) -> dict:
    """Run a single trace and save to file.

    Returns a result dict with metrics for analysis.
    """
    query_id = query_data["id"]
    query = query_data["query"]
    expected_language = query_data.get("language", "en")
    expected_filters = query_data.get("expected_filters", {})
    expected_behavior = query_data.get("expected_behavior", {})
    gen_expectations = query_data.get("generation_expectations", {})
    query_type = query_data.get("query_type", "unknown")

    result = {
        "query_id": query_id,
        "query": query,
        "query_type": query_type,
        "expected_language": expected_language,
        "expected_filters": expected_filters,
        "expected_behavior": expected_behavior,
        "status": "PENDING",
        "issues": [],
        "metrics": {},
    }

    with open(trace_file, "w", encoding="utf-8") as f:

        def output(text: str = ""):
            f.write(text + "\n")

        output("=" * 80)
        output(f"  TRACE: {query_id}")
        output("=" * 80)
        output(f'\nQuery: "{query}"')
        output(f"Query Type: {query_type}")
        output(f"Expected Language: {expected_language}")
        output(f"Expected Filters: {json.dumps(expected_filters, indent=2)}")
        output(f"Expected Behavior: {json.dumps(expected_behavior, indent=2)}")
        output("")

        # Known cities for normalization
        known_cities = [
            "paris",
            "versailles",
            "montreuil",
            "nanterre",
            "saint-denis",
            "bobigny",
            "creteil",
            "bondy",
            "fontainebleau",
            "vincennes",
        ]

        # ========================================
        # STEP 1: Security Check
        # ========================================
        output("-" * 60)
        output("  STEP 1: Security Check")
        output("-" * 60)

        start_time = time.time()
        is_safe = True
        security_message = None

        try:
            check_safety(query)  # Raises SecurityException if unsafe
            security_time = (time.time() - start_time) * 1000
            result["metrics"]["security_time_ms"] = security_time
            output(f"  Security Check Time: {security_time:.0f} ms")
            output("  Is Safe: True")

        except SecurityException as e:
            security_time = (time.time() - start_time) * 1000
            result["metrics"]["security_time_ms"] = security_time
            is_safe = False
            security_message = str(e)
            output(f"  Security Check Time: {security_time:.0f} ms")
            output("  Is Safe: False")
            output(f"  Security Message: {security_message}")

        except Exception as e:
            output(f"  Security Check Error: {str(e)}")
            result["issues"].append({"severity": "HIGH", "issue": f"Security check error: {str(e)}"})

        # Check security expectations
        expected_blocked = expected_behavior.get("expected_response_type") == "security_block"
        actual_blocked = not is_safe

        if expected_blocked and not actual_blocked:
            result["issues"].append(
                {
                    "severity": "CRITICAL",
                    "issue": "Security bypass - expected block but query passed",
                    "details": f"Query type: {query_type}",
                }
            )
        elif not expected_blocked and actual_blocked:
            result["issues"].append(
                {
                    "severity": "CRITICAL",
                    "issue": "False positive - legitimate query blocked",
                    "details": f"Security message: {security_message}",
                }
            )

        result["metrics"]["security_blocked"] = actual_blocked
        result["metrics"]["expected_blocked"] = expected_blocked

        # ========================================
        # STEP 2: Unified Query Analysis
        # ========================================
        output("")
        output("-" * 60)
        output("  STEP 2: Unified Query Analysis")
        output("-" * 60)

        start_time = time.time()
        try:
            analysis = unified_analyze(query, chat_history=[], known_cities=known_cities)
            analysis_time = (time.time() - start_time) * 1000
            result["metrics"]["analysis_time_ms"] = analysis_time

            output(f"  Analysis Time: {analysis_time:.0f} ms")
            output(f"  Detected Language: {analysis.detected_language}")
            output(f"  Intent: {analysis.intent.value}")
            output(f"  Intent Confidence: {analysis.intent_confidence:.2f}")
            output(f'  Refined Query: "{analysis.refined_query}"')
            output("  Extracted Filters:")
            for k, v in analysis.filters.items():
                if v is not None:
                    output(f"    - {k}: {v}")

            # Completeness Check (critical for understanding clarification behavior)
            output("")
            output("  Completeness Check:")
            output(f"    - Is Complete: {analysis.is_complete}")
            if analysis.missing_criteria:
                output(f"    - Missing Criteria: {analysis.missing_criteria}")
            else:
                output("    - Missing Criteria: None")

            # Scope dimension details
            scope_dim = analysis.dimensions.get("scope")
            if scope_dim and scope_dim.detected:
                output(f'    - Scope: "{scope_dim.value}" (action: {scope_dim.action})')
                if scope_dim.value == "all":
                    output("    - Broad Intent Bypass: YES (user explicitly asked for 'all')")

            # Should ask clarification?
            should_clarify = not analysis.is_complete
            expected_clarify = expected_behavior.get("should_ask_clarification", False)
            output(f"    - Should Ask Clarification: {should_clarify}")
            output(f"    - Expected Clarification: {expected_clarify}")

            if should_clarify != expected_clarify:
                result["issues"].append(
                    {
                        "severity": "HIGH",
                        "issue": "Clarification behavior mismatch",
                        "expected": expected_clarify,
                        "actual": should_clarify,
                    }
                )

            # Store completeness metrics
            result["metrics"]["is_complete"] = analysis.is_complete
            result["metrics"]["missing_criteria"] = analysis.missing_criteria
            result["metrics"]["should_clarify"] = should_clarify

            # Store actual values
            result["metrics"]["detected_language"] = analysis.detected_language
            result["metrics"]["intent"] = analysis.intent.value
            result["metrics"]["extracted_filters"] = {k: v for k, v in analysis.filters.items() if v is not None}

            # Check language detection
            if analysis.detected_language != expected_language:
                result["issues"].append(
                    {
                        "severity": "MEDIUM",
                        "issue": "Language detection mismatch",
                        "expected": expected_language,
                        "actual": analysis.detected_language,
                    }
                )

            # Check filter extraction (case-insensitive comparison)
            for filter_key, expected_value in expected_filters.items():
                actual_value = analysis.filters.get(filter_key)

                # Normalize for comparison
                if isinstance(expected_value, str) and isinstance(actual_value, str):
                    match = expected_value.lower() == actual_value.lower()
                elif expected_value is None and actual_value is None:
                    match = True
                else:
                    match = expected_value == actual_value

                if not match:
                    result["issues"].append(
                        {
                            "severity": "HIGH",
                            "issue": f"Filter extraction mismatch: {filter_key}",
                            "expected": expected_value,
                            "actual": actual_value,
                        }
                    )

        except Exception as e:
            output(f"  Analysis Error: {str(e)}")
            result["issues"].append({"severity": "HIGH", "issue": f"Analysis error: {str(e)}"})
            analysis = None

        # ========================================
        # STEP 3: RAG Pipeline (if safe and not blocked)
        # ========================================
        should_run_rag = is_safe and (expected_behavior.get("expected_llm_calls", 2) > 0)

        if should_run_rag:
            output("")
            output("-" * 60)
            output("  STEP 3: RAG Pipeline Execution")
            output("-" * 60)

            start_time = time.time()
            try:
                session_id = f"trace_{query_id}"
                rag_result = chain.query_with_metadata(query, session_id=session_id)
                rag_time = (time.time() - start_time) * 1000
                result["metrics"]["rag_time_ms"] = rag_time
                result["metrics"]["total_latency_ms"] = rag_time + result["metrics"].get("analysis_time_ms", 0)

                output(f"  RAG Pipeline Time: {rag_time:.0f} ms")
                output(f"  Events Retrieved: {len(rag_result.get('sources', []))}")
                output(f"  Events in Response: {len(rag_result.get('structured_events', []))}")

                result["metrics"]["events_retrieved"] = len(rag_result.get("sources", []))
                result["metrics"]["events_in_response"] = len(rag_result.get("structured_events", []))

                # Show response preview
                answer = rag_result.get("answer", "")
                output("\n  Response Preview (first 500 chars):")
                output(f"  {answer[:500]}...")

                # Check latency SLA (2 seconds)
                if rag_time > 2000:
                    result["issues"].append(
                        {
                            "severity": "MEDIUM",
                            "issue": "Latency exceeds SLA",
                            "threshold_ms": 2000,
                            "actual_ms": rag_time,
                        }
                    )

            except Exception as e:
                output(f"  RAG Error: {str(e)}")
                result["issues"].append({"severity": "HIGH", "issue": f"RAG pipeline error: {str(e)}"})
        else:
            output("")
            output("-" * 60)
            output("  STEP 3: RAG Pipeline SKIPPED")
            output("-" * 60)
            if not is_safe:
                output("  Reason: Query blocked by security check")
            else:
                output("  Reason: Expected 0 LLM calls (special query path)")

        # ========================================
        # SUMMARY
        # ========================================
        output("")
        output("=" * 80)
        output("  TRACE SUMMARY")
        output("=" * 80)

        # Determine final status
        critical_issues = [i for i in result["issues"] if i.get("severity") == "CRITICAL"]
        high_issues = [i for i in result["issues"] if i.get("severity") == "HIGH"]
        medium_issues = [i for i in result["issues"] if i.get("severity") == "MEDIUM"]

        if critical_issues:
            result["status"] = "FAILED"
        elif high_issues:
            result["status"] = "FAILED"
        elif medium_issues:
            result["status"] = "WARNING"
        else:
            result["status"] = "PASSED"

        output(f"  Status: {result['status']}")
        output(f"  Issues Found: {len(result['issues'])}")
        for issue in result["issues"]:
            output(f"    [{issue.get('severity')}] {issue.get('issue')}")

        output("\n  Metrics:")
        for metric, value in result["metrics"].items():
            if isinstance(value, float):
                output(f"    - {metric}: {value:.2f}")
            else:
                output(f"    - {metric}: {value}")

        output(f"\n[Trace saved: {trace_file.name}]")

    return result


def generate_analysis_report(results: list[dict], report_path: Path):
    """Generate the markdown analysis report."""

    # Calculate statistics
    total = len(results)
    passed = len([r for r in results if r["status"] == "PASSED"])
    failed = len([r for r in results if r["status"] == "FAILED"])
    warnings = len([r for r in results if r["status"] == "WARNING"])

    # Group by category
    categories = {
        "SQ": {"name": "Standard Queries", "results": []},
        "SEC": {"name": "Security Tests", "results": []},
        "FP": {"name": "False Positive Tests", "results": []},
        "BQ": {"name": "Boundary Cases", "results": []},
        "RT": {"name": "Retrieval Tests", "results": []},
        "BL": {"name": "Bilingual Tests", "results": []},
    }

    for r in results:
        prefix = r["query_id"][:2] if r["query_id"][:2] in categories else r["query_id"][:3]
        if prefix in categories:
            categories[prefix]["results"].append(r)

    # Collect all issues by severity
    critical_issues = []
    high_issues = []
    medium_issues = []

    for r in results:
        for issue in r.get("issues", []):
            issue_with_context = {**issue, "query_id": r["query_id"], "query": r["query"]}
            if issue.get("severity") == "CRITICAL":
                critical_issues.append(issue_with_context)
            elif issue.get("severity") == "HIGH":
                high_issues.append(issue_with_context)
            elif issue.get("severity") == "MEDIUM":
                medium_issues.append(issue_with_context)

    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# Single-Turn Trace Analysis Report\n\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        f.write("## Executive Summary\n\n")
        f.write(f"- **Total Queries**: {total}\n")
        f.write(f"- **Passed**: {passed} ({passed/total*100:.1f}%)\n")
        f.write(f"- **Failed**: {failed} ({failed/total*100:.1f}%)\n")
        f.write(f"- **Warnings**: {warnings} ({warnings/total*100:.1f}%)\n\n")

        # Category breakdown tables
        f.write("## Category Breakdown\n\n")

        for prefix, cat_data in categories.items():
            if not cat_data["results"]:
                continue

            cat_results = cat_data["results"]
            cat_passed = len([r for r in cat_results if r["status"] == "PASSED"])
            cat_failed = len([r for r in cat_results if r["status"] == "FAILED"])

            f.write(f"### {cat_data['name']} ({prefix}001-{prefix}{len(cat_results):03d})\n\n")
            f.write(f"**Pass Rate**: {cat_passed}/{len(cat_results)} ({cat_passed/len(cat_results)*100:.1f}%)\n\n")

            f.write("| ID | Query | Status | Issues |\n")
            f.write("|-----|-------|--------|--------|\n")

            for r in cat_results:
                query_preview = r["query"][:40] + "..." if len(r["query"]) > 40 else r["query"]
                issue_count = len(r.get("issues", []))
                status_icon = "PASS" if r["status"] == "PASSED" else ("WARN" if r["status"] == "WARNING" else "FAIL")
                f.write(f"| {r['query_id']} | {query_preview} | {status_icon} | {issue_count} |\n")

            f.write("\n")

        # Discrepancies section
        f.write("## Discrepancies Found\n\n")

        if critical_issues:
            f.write("### Critical Issues\n\n")
            for issue in critical_issues:
                f.write(f"- **{issue['query_id']}**: {issue['issue']}\n")
                f.write(f"  - Query: \"{issue['query']}\"\n")
                if "expected" in issue:
                    f.write(f"  - Expected: {issue['expected']}\n")
                if "actual" in issue:
                    f.write(f"  - Actual: {issue['actual']}\n")
                f.write("\n")
        else:
            f.write("### Critical Issues\n\nNone found.\n\n")

        if high_issues:
            f.write("### High Priority Issues\n\n")
            for issue in high_issues:
                f.write(f"- **{issue['query_id']}**: {issue['issue']}\n")
                if "expected" in issue:
                    f.write(f"  - Expected: {issue['expected']}, Actual: {issue.get('actual', 'N/A')}\n")
            f.write("\n")
        else:
            f.write("### High Priority Issues\n\nNone found.\n\n")

        if medium_issues:
            f.write("### Medium Priority Issues\n\n")
            for issue in medium_issues:
                f.write(f"- **{issue['query_id']}**: {issue['issue']}\n")
            f.write("\n")
        else:
            f.write("### Medium Priority Issues\n\nNone found.\n\n")

        # Recommendations
        f.write("## Recommendations\n\n")

        if critical_issues:
            f.write("1. **Fix Security Issues**: Critical security bypasses or false positives detected.\n")
        if high_issues:
            f.write("2. **Improve Filter Extraction**: Some expected filters are not being extracted correctly.\n")
        if medium_issues:
            f.write("3. **Optimize Performance**: Some queries exceed latency SLA or have language detection issues.\n")
        if not (critical_issues or high_issues or medium_issues):
            f.write("All tests passed! Consider adding more edge cases to the golden dataset.\n")

        f.write("\n---\n")
        f.write("Report generated by `run_single_turn_traces.py`\n")


def generate_summary_json(results: list[dict], summary_path: Path):
    """Generate the machine-readable summary JSON."""

    total = len(results)
    passed = len([r for r in results if r["status"] == "PASSED"])
    failed = len([r for r in results if r["status"] == "FAILED"])
    warnings = len([r for r in results if r["status"] == "WARNING"])

    # Group by category
    by_category = {}
    for r in results:
        prefix = r["query_id"][:2] if r["query_id"][:2] in ["SQ", "FP", "BQ", "RT", "BL"] else r["query_id"][:3]
        if prefix not in by_category:
            by_category[prefix] = {"total": 0, "passed": 0, "failed": 0, "warnings": 0}
        by_category[prefix]["total"] += 1
        if r["status"] == "PASSED":
            by_category[prefix]["passed"] += 1
        elif r["status"] == "FAILED":
            by_category[prefix]["failed"] += 1
        else:
            by_category[prefix]["warnings"] += 1

    # Collect discrepancies
    discrepancies = []
    for r in results:
        for issue in r.get("issues", []):
            discrepancies.append(
                {
                    "query_id": r["query_id"],
                    "severity": issue.get("severity"),
                    "issue": issue.get("issue"),
                    "expected": issue.get("expected"),
                    "actual": issue.get("actual"),
                }
            )

    summary = {
        "generated_at": datetime.now().isoformat(),
        "total_queries": total,
        "results": {"passed": passed, "failed": failed, "warnings": warnings},
        "pass_rate": passed / total if total > 0 else 0,
        "by_category": by_category,
        "discrepancies": discrepancies,
        "detailed_results": results,
    }

    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)


# Rate limiting configuration
DELAY_BETWEEN_QUERIES = 8  # 8 seconds between queries (~7.5 RPM, under 15 RPM limit)
MAX_RETRIES_ON_RATE_LIMIT = 5  # More retries allowed
RATE_LIMIT_BACKOFF_BASE = 65  # Wait 65+ seconds on rate limit (Google resets at 60s)


def test_api_health() -> tuple[bool, str]:
    """Test if the Google API is working before running traces.

    Returns (success, message) tuple.
    """
    print("Testing Google API health...")
    try:
        from src.config import settings

        # Check if API key is loaded
        if not settings.google_api_key or len(settings.google_api_key) < 10:
            return False, f"API key not loaded properly (length: {len(settings.google_api_key)})"

        # Test a simple analysis
        result = unified_analyze("Hello")

        # Check if it got a real response (not default fallback)
        if result.intent_confidence >= 0.5:
            return True, "API is working correctly"
        else:
            return False, "API returned low confidence (possible fallback due to error)"

    except Exception as e:
        error_msg = str(e)
        if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
            return False, f"Rate limit hit: {error_msg[:100]}"
        elif "403" in error_msg or "PERMISSION_DENIED" in error_msg:
            return False, f"API key invalid: {error_msg[:100]}"
        else:
            return False, f"API error: {error_msg[:100]}"


def check_for_api_errors(result: dict) -> tuple[bool, str]:
    """Check if a trace result indicates an API error.

    Returns (has_error, error_type) tuple.
    """
    for issue in result.get("issues", []):
        # Check both issue text and any details
        issue_text = str(issue.get("issue", "")).lower()
        issue_details = str(issue.get("details", "")).lower()
        combined = issue_text + " " + issue_details

        if "429" in combined or "rate" in combined or "exhausted" in combined or "resource_exhausted" in combined:
            return True, "RATE_LIMIT"
        if "403" in combined or "permission" in combined:
            return True, "API_KEY_INVALID"
    return False, None


def main():
    """Main execution function."""
    print("=" * 80)
    print("  Single-Turn Trace Analysis")
    print("=" * 80)

    # ========================================
    # PRE-FLIGHT CHECK: Test API health
    # ========================================
    print("\n" + "-" * 60)
    print("  PRE-FLIGHT CHECK")
    print("-" * 60)

    api_ok, api_message = test_api_health()
    if not api_ok:
        print("\n  [ABORT] API health check FAILED!")
        print(f"  Error: {api_message}")
        print("\n  Please fix the API issue before running traces.")
        print("  - Check your .env file has GOOGLE_API_KEY set")
        print("  - Check no Windows env var is overriding it")
        print("  - Wait a minute if rate limited")
        print("=" * 80)
        return

    print(f"  [OK] {api_message}")
    print(f"  Delay between queries: {DELAY_BETWEEN_QUERIES}s")
    print("-" * 60)

    print(f"\nLoading golden dataset from: {GOLDEN_DATASET_PATH}")

    # Load dataset
    dataset = load_golden_dataset()
    single_queries = dataset.get("single_queries", [])

    print(f"Found {len(single_queries)} single-turn queries\n")

    # Ensure output directories exist
    TRACES_DIR.mkdir(parents=True, exist_ok=True)

    # Initialize chain once
    print("Initializing RAGChain...")
    start_init = time.time()
    chain = RAGChain()
    init_time = time.time() - start_init
    print(f"Chain initialized in {init_time:.1f}s\n")

    # Run traces with monitoring
    results = []
    consecutive_api_errors = 0

    for i, query_data in enumerate(single_queries, 1):
        query_id = query_data["id"]
        print(f"[{i}/{len(single_queries)}] Running trace for {query_id}...", end=" ", flush=True)

        trace_file = TRACES_DIR / f"{query_id}_trace.txt"

        start = time.time()
        result = run_single_trace(chain, query_data, trace_file)
        elapsed = time.time() - start

        results.append(result)

        status_icon = "PASS" if result["status"] == "PASSED" else ("WARN" if result["status"] == "WARNING" else "FAIL")
        print(f"{status_icon} ({elapsed:.1f}s)")

        # ========================================
        # CHECK FOR API ERRORS
        # ========================================
        has_api_error, error_type = check_for_api_errors(result)

        if has_api_error:
            consecutive_api_errors += 1
            print(f"  [WARNING] API error detected: {error_type}")

            if error_type == "RATE_LIMIT":
                if consecutive_api_errors >= MAX_RETRIES_ON_RATE_LIMIT:
                    print(f"\n  [ABORT] Too many rate limit errors ({consecutive_api_errors})")
                    print("  Stopping to avoid wasting time. Please wait and retry later.")
                    break
                else:
                    wait_time = RATE_LIMIT_BACKOFF_BASE * (2 ** (consecutive_api_errors - 1))
                    print(f"  [WAIT] Rate limited. Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)

            elif error_type == "API_KEY_INVALID":
                print("\n  [ABORT] API key is invalid!")
                print("  Please check your GOOGLE_API_KEY environment variable.")
                break
        else:
            consecutive_api_errors = 0  # Reset counter on success

        # ========================================
        # DELAY BETWEEN QUERIES (avoid rate limits)
        # ========================================
        if i < len(single_queries):  # Don't delay after last query
            time.sleep(DELAY_BETWEEN_QUERIES)

    # Generate reports
    print("\n" + "=" * 80)
    print("  Generating Reports")
    print("=" * 80)

    report_path = OUTPUT_DIR / "analysis_report.md"
    summary_path = OUTPUT_DIR / "summary.json"

    print(f"Writing analysis report: {report_path}")
    generate_analysis_report(results, report_path)

    print(f"Writing summary JSON: {summary_path}")
    generate_summary_json(results, summary_path)

    # Print final summary
    total = len(results)
    passed = len([r for r in results if r["status"] == "PASSED"])
    failed = len([r for r in results if r["status"] == "FAILED"])
    warnings = len([r for r in results if r["status"] == "WARNING"])

    print("\n" + "=" * 80)
    print("  FINAL SUMMARY")
    print("=" * 80)
    print(f"  Total Queries: {total}")
    print(f"  Passed: {passed} ({passed/total*100:.1f}%)")
    print(f"  Failed: {failed} ({failed/total*100:.1f}%)")
    print(f"  Warnings: {warnings} ({warnings/total*100:.1f}%)")
    print(f"\n  Output saved to: {OUTPUT_DIR}")
    print("=" * 80)


if __name__ == "__main__":
    main()
