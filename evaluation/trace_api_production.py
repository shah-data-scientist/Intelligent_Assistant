"""
FILE: trace_api_production.py
STATUS: Active
RESPONSIBILITY: Tests the PRODUCTION API endpoints with detailed trace output
LAST MAJOR UPDATE: 2026-02-01
MAINTAINER: Team

This script tests what happens in production by calling the actual FastAPI endpoints.
"""

import sys
import io
import time
import requests
from pathlib import Path

# Setup
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from dotenv import load_dotenv
import os

load_dotenv(project_root / ".env", override=True)

# API Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8001")
API_PREFIX = "/api/v1"
API_KEY = os.getenv("APP_API_KEY", "dev-secret-key")


def print_separator(title: str, char: str = "─", width: int = 80):
    """Print a formatted section separator."""
    print(f"\n{char * width}")
    print(f"  {title}")
    print(char * width)


def print_event_table(sources: list):
    """Print retrieved events in a table with scores."""
    if not sources:
        print("  No events retrieved.")
        return

    print(f"\n  {'─'*76}")
    print(f"  {'#':<3} {'Score':<7} {'Match Type':<16} {'Title':<35} {'City'}")
    print(f"  {'─'*76}")

    for i, src in enumerate(sources[:10], 1):
        score = src.get("score", 0)
        match_type = src.get("match_type", "Unknown")[:16]
        title = src.get("title", "Unknown")[:35]
        city = src.get("city", "Unknown")
        date = src.get("date", "Unknown")
        category = src.get("category", "Unknown")

        print(f"  {i:<3} {score:<7.3f} {match_type:<16} {title:<35} {city}")
        print(f"      └─ 📅 {date} | 🎭 {category}")


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


def call_chat_api(question: str, session_id: str = "trace_session"):
    """Call the /chat API endpoint."""
    headers = {"X-API-Key": API_KEY, "Content-Type": "application/json"}
    payload = {"question": question, "session_id": session_id}

    start_time = time.time()
    response = requests.post(f"{API_BASE_URL}{API_PREFIX}/chat", headers=headers, json=payload, timeout=120)
    latency_ms = (time.time() - start_time) * 1000

    return response, latency_ms


def trace_api_query(query: str, session_id: str = "trace_session"):
    """Trace a query through the production API."""

    print_separator(f"QUERY: {query}", "═")

    # ========================================
    # STEP 1: API Request
    # ========================================
    print_separator("STEP 1: API REQUEST")
    print(f"\n  Endpoint: POST {API_BASE_URL}/chat")
    print(f"  Session ID: {session_id}")
    print(f'  Question: "{query}"')

    # ========================================
    # STEP 2: API Response
    # ========================================
    print_separator("STEP 2: API RESPONSE")

    try:
        response, latency_ms = call_chat_api(query, session_id)

        print(f"\n  HTTP Status: {response.status_code}")
        print(f"  Latency: {latency_ms:.0f}ms")

        if response.status_code != 200:
            print(f"  ERROR: {response.text}")
            return None

        data = response.json()

    except Exception as e:
        print(f"  ERROR: {e}")
        return None

    # ========================================
    # STEP 3: Response Analysis
    # ========================================
    print_separator("STEP 3: RESPONSE ANALYSIS")

    sources = data.get("sources", [])
    structured_events = data.get("structured_events", [])

    print(f"\n  Message ID: {data.get('message_id', 'N/A')}")
    print(f"  Sources retrieved: {len(sources)}")
    print(f"  Structured events: {len(structured_events)}")
    print(f"  Needs clarification: {data.get('needs_clarification', False)}")

    if data.get("clarifying_questions"):
        print(f"  Clarifying questions: {data.get('clarifying_questions')}")

    # ========================================
    # STEP 4: Retrieved Events (with scores)
    # ========================================
    print_separator("STEP 4: RETRIEVED EVENTS (with scores)")
    print_event_table(sources)

    # ========================================
    # STEP 5: Generated Response
    # ========================================
    print_separator("STEP 5: GENERATED RESPONSE")

    answer = data.get("answer", "")
    print(f"\n  Response length: {len(answer)} characters")
    print("\n  FULL RESPONSE:")
    print(f"  {'─'*70}")
    for line in answer.split("\n"):
        print(f"  {line}")

    return data


def main():
    """Run production API trace."""
    print("\n" + "=" * 80)
    print("  PRODUCTION API TRACE - Testing Real Endpoints")
    print("=" * 80)

    # Check if API is running
    print("\nChecking API health...")
    if not check_api_health():
        print("\n[ERROR] API is not running or not ready.")
        print("Please start the API first with:")
        print("  VIRTUAL_ENV=$(pwd)/.venv poetry run uvicorn src.api.main:app --reload")
        print("\nOr run in a separate terminal.")
        return 1

    print("[OK] API is healthy and ready.\n")

    session_id = f"trace_{int(time.time())}"

    # ==========================================
    # TRACE 1: Initial query
    # ==========================================
    query1 = "Concerts de jazz à Paris en février"
    print("\n" + "#" * 80)
    print(f"# TRACE 1: {query1}")
    print("#" * 80)

    result1 = trace_api_query(query1, session_id)

    if not result1:
        print("\n[ERROR] First query failed. Aborting.")
        return 1

    # ==========================================
    # TRACE 2: Follow-up query (context merge)
    # ==========================================
    query2 = "Et les spectacles de théâtre ?"
    print("\n\n" + "#" * 80)
    print(f"# TRACE 2: {query2} (follow-up with context)")
    print("#" * 80)

    result2 = trace_api_query(query2, session_id)

    # ==========================================
    # SUMMARY
    # ==========================================
    print("\n\n" + "=" * 80)
    print("  TRACE SUMMARY")
    print("=" * 80)
    print(f"\n  Session ID: {session_id}")
    print("  Queries tested: 2")
    print(f"  Turn 1: '{query1}' -> {len(result1.get('sources', []))} events")
    if result2:
        print(f"  Turn 2: '{query2}' -> {len(result2.get('sources', []))} events")
    print("\n  [SUCCESS] Production API trace completed.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
