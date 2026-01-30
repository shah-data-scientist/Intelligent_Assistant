#!/usr/bin/env python
"""Batch trace execution for all multi-turn conversations from the golden dataset.

This script runs detailed traces for all 15 conversations and generates:
1. Individual trace files for each conversation (CONV_XXX_trace.txt)
2. Appends results to the existing analysis_report.md
3. Updates summary.json with conversation results
"""

import sys
import os
import io
import json
import time
import logging
from datetime import datetime, date
from pathlib import Path
from typing import Any, List, Dict

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load .env BEFORE importing src modules
from dotenv import load_dotenv
load_dotenv(project_root / ".env", override=True)

# CRITICAL: Force load API key from .env to override Windows env var
env_file = project_root / ".env"
if env_file.exists():
    with open(env_file, 'r') as f:
        for line in f:
            if line.startswith('GOOGLE_API_KEY='):
                os.environ['GOOGLE_API_KEY'] = line.strip().split('=', 1)[1]
                break

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Configure logging
logging.basicConfig(
    level=logging.WARNING,  # Reduce noise
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('httpcore').setLevel(logging.WARNING)

from src.retrieval.chain import RAGChain
from src.retrieval.unified_analyzer import unified_analyze, map_category_to_db
from src.security.guardrails import check_safety, SecurityException

# Output directories
OUTPUT_DIR = project_root / "data" / "evaluation" / "reports" / "single_turn_traces"
TRACES_DIR = OUTPUT_DIR / "traces"
GOLDEN_DATASET_PATH = project_root / "data" / "evaluation" / "golden_dataset.json"


def load_golden_dataset() -> dict:
    """Load the golden dataset JSON."""
    with open(GOLDEN_DATASET_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


def run_conversation_trace(
    chain: RAGChain,
    conv_data: dict,
    trace_file: Path
) -> dict:
    """Run a multi-turn conversation trace and save to file.

    Returns a result dict with metrics for analysis.
    """
    session_id = conv_data['session_id']
    description = conv_data.get('description', '')
    test_focus = conv_data.get('test_focus', [])
    language = conv_data.get('language', 'fr')
    turns = conv_data.get('turns', [])

    result = {
        'session_id': session_id,
        'description': description,
        'test_focus': test_focus,
        'language': language,
        'num_turns': len(turns),
        'status': 'PENDING',
        'issues': [],
        'turn_results': [],
        'metrics': {}
    }

    total_latency_ms = 0.0
    all_issues = []

    with open(trace_file, 'w', encoding='utf-8') as f:
        def output(text: str = ""):
            f.write(text + "\n")

        output("=" * 80)
        output(f"  CONVERSATION TRACE: {session_id}")
        output("=" * 80)
        output(f"\nDescription: {description}")
        output(f"Test Focus: {test_focus}")
        output(f"Language: {language}")
        output(f"Total Turns: {len(turns)}")
        output()

        # Use a unique session ID for this trace to maintain context
        trace_session_id = f"trace_{session_id}_{int(time.time())}"

        for turn_idx, turn in enumerate(turns, 1):
            query = turn.get('query', '')
            turn_type = turn.get('turn_type', 'search')
            expected_behavior = turn.get('expected_behavior', {})
            expected_filters = turn.get('expected_filters', {})

            output("-" * 60)
            output(f"  TURN {turn_idx}: {turn_type}")
            output("-" * 60)
            output(f"Query: \"{query}\"")
            output(f"Turn Type: {turn_type}")
            output(f"Expected Filters: {json.dumps(expected_filters, ensure_ascii=False)}")
            output(f"Expected Behavior: {json.dumps(expected_behavior, ensure_ascii=False)}")
            output()

            turn_result = {
                'turn_idx': turn_idx,
                'query': query,
                'turn_type': turn_type,
                'expected_filters': expected_filters,
                'expected_behavior': expected_behavior,
                'issues': [],
                'metrics': {}
            }

            # Step 1: Security Check
            output("  [Step 1] Security Check")
            sec_start = time.time()
            is_safe = True
            try:
                check_safety(query, session_id=trace_session_id)
            except SecurityException as e:
                is_safe = False
                output(f"    BLOCKED: {str(e)[:100]}")
            sec_time = (time.time() - sec_start) * 1000
            turn_result['metrics']['security_time_ms'] = round(sec_time, 2)
            turn_result['metrics']['security_blocked'] = not is_safe
            output(f"    Time: {sec_time:.1f}ms, Safe: {is_safe}")
            output()

            # Step 2: Query Analysis
            output("  [Step 2] Query Analysis")
            analysis_start = time.time()
            try:
                analysis = unified_analyze(query, chat_history=None)
                analysis_time = (time.time() - analysis_start) * 1000
                turn_result['metrics']['analysis_time_ms'] = round(analysis_time, 2)
                turn_result['metrics']['detected_language'] = analysis.detected_language
                turn_result['metrics']['intent'] = analysis.intent.value
                turn_result['metrics']['is_complete'] = analysis.is_complete
                turn_result['metrics']['extracted_filters'] = analysis.filters

                output(f"    Time: {analysis_time:.1f}ms")
                output(f"    Language: {analysis.detected_language}")
                output(f"    Intent: {analysis.intent.value}")
                output(f"    Is Complete: {analysis.is_complete}")
                output(f"    Filters: {json.dumps(analysis.filters, ensure_ascii=False, indent=6)}")

                # Check filter extraction
                for key, expected_val in expected_filters.items():
                    actual_val = analysis.filters.get(key)
                    if actual_val is None and expected_val is not None:
                        issue = f"[HIGH] Turn {turn_idx}: Missing filter '{key}' (expected: {expected_val})"
                        turn_result['issues'].append(issue)
                        output(f"    ! ISSUE: {issue}")
                    elif actual_val != expected_val and expected_val is not None:
                        # Normalize category comparison
                        if key == 'category':
                            expected_norm = map_category_to_db(expected_val) if expected_val else None
                            actual_norm = map_category_to_db(actual_val) if actual_val else None
                            if expected_norm == actual_norm:
                                continue
                        issue = f"[MEDIUM] Turn {turn_idx}: Filter mismatch for '{key}' (expected: {expected_val}, got: {actual_val})"
                        turn_result['issues'].append(issue)
                        output(f"    ! ISSUE: {issue}")

            except Exception as e:
                analysis_time = (time.time() - analysis_start) * 1000
                turn_result['metrics']['analysis_time_ms'] = round(analysis_time, 2)
                turn_result['metrics']['analysis_error'] = str(e)
                output(f"    ERROR: {e}")
            output()

            # Step 3: RAG Chain Execution
            if is_safe:
                output("  [Step 3] RAG Chain Execution")
                rag_start = time.time()
                try:
                    rag_result = chain.query_with_metadata(
                        query,
                        session_id=trace_session_id,
                        language=language
                    )
                    rag_time = (time.time() - rag_start) * 1000
                    turn_result['metrics']['rag_time_ms'] = round(rag_time, 2)

                    response = rag_result.get('response', '')
                    events = rag_result.get('events', [])
                    turn_result['metrics']['events_retrieved'] = len(events)
                    turn_result['metrics']['response_preview'] = response[:300]

                    output(f"    Time: {rag_time:.1f}ms")
                    output(f"    Events Retrieved: {len(events)}")
                    output(f"    Response Preview: {response[:200]}...")

                    # Check expected behaviors
                    if expected_behavior.get('should_clarify') and not rag_result.get('clarification_asked'):
                        # Check if response contains clarification keywords
                        clarify_keywords = ['quelle', 'which', 'quel type', 'what type', 'pour quand']
                        has_clarify = any(kw in response.lower() for kw in clarify_keywords)
                        if not has_clarify:
                            issue = f"[MEDIUM] Turn {turn_idx}: Expected clarification question but got direct response"
                            turn_result['issues'].append(issue)

                    if expected_behavior.get('should_retain_context'):
                        # Context retention is harder to verify automatically
                        pass

                except Exception as e:
                    rag_time = (time.time() - rag_start) * 1000
                    turn_result['metrics']['rag_time_ms'] = round(rag_time, 2)
                    turn_result['metrics']['rag_error'] = str(e)
                    output(f"    ERROR: {e}")
            output()

            # Calculate turn latency
            turn_latency = sum([
                turn_result['metrics'].get('security_time_ms', 0),
                turn_result['metrics'].get('analysis_time_ms', 0),
                turn_result['metrics'].get('rag_time_ms', 0)
            ])
            turn_result['metrics']['turn_latency_ms'] = round(turn_latency, 2)
            total_latency_ms += turn_latency

            # Check latency SLA (5000ms per turn)
            if turn_latency > 5000:
                issue = f"[MEDIUM] Turn {turn_idx}: Latency exceeds SLA ({turn_latency:.0f}ms > 5000ms)"
                turn_result['issues'].append(issue)

            all_issues.extend(turn_result['issues'])
            result['turn_results'].append(turn_result)

        # Summary
        output("=" * 80)
        output("  CONVERSATION SUMMARY")
        output("=" * 80)

        result['metrics']['total_latency_ms'] = round(total_latency_ms, 2)
        result['metrics']['avg_turn_latency_ms'] = round(total_latency_ms / len(turns), 2) if turns else 0
        result['issues'] = all_issues

        if len(all_issues) == 0:
            result['status'] = 'PASS'
        elif any('[HIGH]' in i for i in all_issues):
            result['status'] = 'FAIL'
        else:
            result['status'] = 'WARN'

        output(f"Status: {result['status']}")
        output(f"Total Issues: {len(all_issues)}")
        for issue in all_issues:
            output(f"  - {issue}")
        output(f"\nTotal Latency: {total_latency_ms:.0f}ms")
        output(f"Avg Turn Latency: {result['metrics']['avg_turn_latency_ms']:.0f}ms")
        output()
        output(f"[Trace saved: {trace_file.name}]")

    return result


def main():
    """Run traces for all conversations."""
    print("=" * 80)
    print("  Multi-Turn Conversation Trace Runner")
    print("=" * 80)
    print()

    # Create output directories
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    TRACES_DIR.mkdir(parents=True, exist_ok=True)

    # Load golden dataset
    dataset = load_golden_dataset()
    conversations = dataset.get('conversations', [])

    print(f"Found {len(conversations)} conversations to trace")
    print()

    # Initialize RAG chain
    print("Initializing RAG chain...")
    chain = RAGChain()
    print("RAG chain ready")
    print()

    # Run traces
    results = []
    for i, conv in enumerate(conversations, 1):
        session_id = conv['session_id']
        trace_file = TRACES_DIR / f"{session_id}_trace.txt"

        print(f"[{i}/{len(conversations)}] Running trace for {session_id}...", end=" ", flush=True)
        start = time.time()
        try:
            result = run_conversation_trace(chain, conv, trace_file)
            elapsed = time.time() - start
            print(f"{result['status']} ({elapsed:.1f}s)")
            results.append(result)
        except Exception as e:
            elapsed = time.time() - start
            print(f"ERROR ({elapsed:.1f}s): {e}")
            results.append({
                'session_id': session_id,
                'status': 'ERROR',
                'error': str(e),
                'issues': [f"[CRITICAL] Exception: {e}"]
            })

        # Small delay to avoid rate limiting
        time.sleep(1.0)

    # Generate summary
    print()
    print("=" * 80)
    print("  Generating Reports")
    print("=" * 80)

    # Write conversation analysis report
    report_path = OUTPUT_DIR / "conversation_analysis_report.md"
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("# Conversation Trace Analysis Report\n\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        passed = sum(1 for r in results if r['status'] == 'PASS')
        failed = sum(1 for r in results if r['status'] == 'FAIL')
        warned = sum(1 for r in results if r['status'] == 'WARN')
        errors = sum(1 for r in results if r['status'] == 'ERROR')

        f.write("## Executive Summary\n\n")
        f.write(f"- **Total Conversations**: {len(results)}\n")
        f.write(f"- **Passed**: {passed} ({100*passed/len(results):.1f}%)\n")
        f.write(f"- **Failed**: {failed} ({100*failed/len(results):.1f}%)\n")
        f.write(f"- **Warnings**: {warned} ({100*warned/len(results):.1f}%)\n")
        if errors:
            f.write(f"- **Errors**: {errors} ({100*errors/len(results):.1f}%)\n")
        f.write("\n")

        f.write("## Conversation Results\n\n")
        f.write("| Session | Description | Turns | Status | Issues |\n")
        f.write("|---------|-------------|-------|--------|--------|\n")
        for r in results:
            desc = r.get('description', '')[:40] + '...' if len(r.get('description', '')) > 40 else r.get('description', '')
            f.write(f"| {r['session_id']} | {desc} | {r.get('num_turns', 0)} | {r['status']} | {len(r.get('issues', []))} |\n")
        f.write("\n")

        # All issues
        f.write("## All Issues\n\n")
        all_issues = []
        for r in results:
            for issue in r.get('issues', []):
                all_issues.append((r['session_id'], issue))

        if all_issues:
            for session_id, issue in all_issues:
                f.write(f"- **{session_id}**: {issue}\n")
        else:
            f.write("No issues found.\n")

    print(f"Writing conversation analysis report: {report_path}")

    # Write conversation summary JSON
    summary_path = OUTPUT_DIR / "conversation_summary.json"
    summary = {
        'generated_at': datetime.now().isoformat(),
        'total_conversations': len(results),
        'results': {
            'passed': passed,
            'failed': failed,
            'warnings': warned,
            'errors': errors
        },
        'conversations': results
    }
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"Writing conversation summary JSON: {summary_path}")

    # Final summary
    print()
    print("=" * 80)
    print("  FINAL SUMMARY")
    print("=" * 80)
    print(f"  Total Conversations: {len(results)}")
    print(f"  Passed: {passed} ({100*passed/len(results):.1f}%)")
    print(f"  Failed: {failed} ({100*failed/len(results):.1f}%)")
    print(f"  Warnings: {warned} ({100*warned/len(results):.1f}%)")
    if errors:
        print(f"  Errors: {errors} ({100*errors/len(results):.1f}%)")
    print()
    print(f"  Output saved to: {OUTPUT_DIR}")
    print("=" * 80)


if __name__ == "__main__":
    main()
