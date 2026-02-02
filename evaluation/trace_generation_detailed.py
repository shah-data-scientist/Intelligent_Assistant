"""
FILE: trace_generation_detailed.py
STATUS: Active
RESPONSIBILITY: Generates DETAILED traces including semantic search terms and event-level results with scores
LAST MAJOR UPDATE: 2026-02-01
MAINTAINER: Team
"""

import sys
import io
from pathlib import Path

# Setup - evaluation folder is one level deep
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from dotenv import load_dotenv

load_dotenv(project_root / ".env", override=True)

from src.retrieval.unified_analyzer import unified_analyze
from src.retrieval.chain import (
    should_apply_default_timeframe,
    apply_default_timeframe,
    detect_language_from_query,
    RAGChain,
)


def print_separator(title: str, char: str = "─", width: int = 80):
    """Print a formatted section separator."""
    print(f"\n{char * width}")
    print(f"  {title}")
    print(char * width)


def print_event_table(sources: list):
    """Print retrieved events in a table with scores and match types."""
    if not sources:
        print("  No events retrieved.")
        return

    print(f"\n  {'─'*76}")
    print(f"  {'#':<3} {'Score':<7} {'Match Type':<16} {'Dist':<6} {'Title':<30} {'City'}")
    print(f"  {'─'*76}")

    for i, src in enumerate(sources[:10], 1):
        score = src.get("score", 0)
        match_type = src.get("match_type", "Unknown")[:16]
        distance = src.get("distance_km", 0)
        title = src.get("title", "Unknown")[:30]
        city = src.get("city", "Unknown")
        date = src.get("date", "Unknown")
        category = src.get("category", "Unknown")
        venue = src.get("venue", "Unknown")[:25]

        dist_str = f"{distance:.1f}km" if distance > 0 else "0km"
        print(f"  {i:<3} {score:<7.3f} {match_type:<16} {dist_str:<6} {title:<30} {city}")
        print(f"      └─ 📅 {date} | 🎭 {category} | 📍 {venue}")


def trace_query_detailed(query: str, chain: RAGChain, session_id: str, chat_history=None):
    """Generate a detailed trace of query processing."""

    print_separator(f"QUERY: {query}", "═")

    # ========================================
    # STEP 1: Language Detection
    # ========================================
    print_separator("STEP 1: LANGUAGE DETECTION")
    language = detect_language_from_query(query)
    print(f"  Detected language: {language}")

    # ========================================
    # STEP 2: Unified LLM Analysis
    # ========================================
    print_separator("STEP 2: UNIFIED LLM ANALYSIS")

    # Use full city list from chain
    known_cities = list(chain.vector_store.city_locator.city_cache.keys())
    analysis = unified_analyze(query, chat_history=chat_history or [], known_cities=known_cities)

    print(f"\n  PRIMARY INTENT: {analysis.intent.value}")
    print(f"  INTENT CONFIDENCE: {analysis.intent_confidence:.2f}")

    print("\n  ENTITY EXTRACTION:")
    print(f"    city_raw: {analysis.city}")
    print(f"    city_normalized: {analysis.city_normalized}")
    print(f"    event_type: {analysis.event_type}")
    print(f"    timeframe: {analysis.timeframe}")

    print("\n  FILTERS EXTRACTED:")
    for key, val in analysis.filters.items():
        if val is not None and not key.startswith("_"):
            print(f"    {key}: {val}")

    print("\n  COMPLETENESS CHECK:")
    print(f"    is_complete: {analysis.is_complete}")
    print(f"    missing_criteria: {analysis.missing_criteria}")

    # ========================================
    # STEP 3: Semantic Search Query Construction
    # ========================================
    print_separator("STEP 3: SEMANTIC SEARCH QUERY")

    refined_query = analysis.filters.get("_refined_query") or query
    search_terms = analysis.filters.get("_search_terms", [query])

    print(f'\n  ORIGINAL QUERY: "{query}"')
    print("\n  REFINED QUERY (sent to vector embeddings):")
    print(f'    "{refined_query}"')

    print("\n  ACCUMULATED SEARCH TERMS:")
    for i, term in enumerate(search_terms, 1):
        print(f'    {i}. "{term}"')

    # ========================================
    # STEP 4: Filter Application
    # ========================================
    print_separator("STEP 4: FILTER APPLICATION")

    filters = analysis.filters.copy()
    should_apply = should_apply_default_timeframe(filters)

    print("\n  APPLIED FILTERS:")
    print(f"    city: {filters.get('city', '(any)')}")
    print(f"    category: {filters.get('category', '(any)')}")
    print(f"    month: {filters.get('month', '(any)')}")
    print(f"    day: {filters.get('day', '(any)')}")
    print(f"    year: {filters.get('year', 2026)}")
    print(f"    is_free: {filters.get('is_free', '(any)')}")

    if should_apply:
        filters = apply_default_timeframe(filters)
        print("\n  DEFAULT TIMEFRAME APPLIED (30 days):")
        print(f"    _timeframe_start: {filters.get('_timeframe_start')}")
        print(f"    _timeframe_end: {filters.get('_timeframe_end')}")

    # ========================================
    # STEP 5: Full RAG Execution
    # ========================================
    print_separator("STEP 5: RAG CHAIN EXECUTION")

    result = chain.query_with_metadata(query, session_id=session_id)

    sources = result.get("sources", [])
    retrieval_stats = result.get("retrieval_stats", {})

    print(f"\n  QUERY TYPE: {result.get('query_type', 'event_search')}")
    print(f"  NEEDS CLARIFICATION: {result.get('needs_clarification', False)}")

    print("\n  RETRIEVAL STATISTICS:")
    print(f"    Total retrieved: {len(sources)}")
    print(f"    Exact matches: {retrieval_stats.get('exact_match_count', 0)}")
    print(f"    Nearby matches: {retrieval_stats.get('nearby_count', 0)}")
    print(f"    Total in database: {retrieval_stats.get('total_in_database', 'N/A')}")

    # ========================================
    # STEP 6: Retrieved Events (with scores)
    # ========================================
    print_separator("STEP 6: RETRIEVED EVENTS (with scores)")

    print_event_table(sources)

    # ========================================
    # STEP 7: Generated Response
    # ========================================
    print_separator("STEP 7: GENERATED RESPONSE")

    answer = result.get("answer", "")
    print(f"\n  RESPONSE LENGTH: {len(answer)} characters")
    print("\n  FULL RESPONSE:")
    print(f"  {'─'*70}")
    for line in answer.split("\n"):
        print(f"  {line}")

    # ========================================
    # STEP 8: Session State
    # ========================================
    print_separator("STEP 8: SESSION STATE")

    stored = chain._session_filters.get(session_id, {})
    filters_only = {k: v for k, v in stored.items() if not k.startswith("_")}
    accumulated_terms = stored.get("_search_terms", [])

    print("\n  STORED FILTERS:")
    for key, val in filters_only.items():
        print(f"    {key}: {val}")

    print("\n  ACCUMULATED SEARCH TERMS:")
    for i, term in enumerate(accumulated_terms, 1):
        print(f'    {i}. "{term}"')

    return result, analysis


def main():
    """Run detailed trace for sample queries."""
    print("\n" + "=" * 80)
    print("  DETAILED QUERY TRACE - Semantic Search & Event Scores")
    print("=" * 80)

    # Initialize chain
    print("\nInitializing RAG chain...")
    chain = RAGChain()
    session_id = "detailed_trace_001"
    print("RAG chain ready.\n")

    # ==========================================
    # TRACE 1: Initial query
    # ==========================================
    query1 = "Concerts de jazz à Paris en février"
    print("\n" + "#" * 80)
    print(f"# TRACE 1: {query1}")
    print("#" * 80)

    result1, analysis1 = trace_query_detailed(query1, chain, session_id)

    # ==========================================
    # TRACE 2: Follow-up query (context merge)
    # ==========================================
    from langchain_core.messages import HumanMessage, AIMessage

    query2 = "Et les spectacles de théâtre ?"
    print("\n\n" + "#" * 80)
    print(f"# TRACE 2: {query2} (follow-up with context)")
    print("#" * 80)

    chat_history = [HumanMessage(content=query1), AIMessage(content=result1["answer"][:200] + "...")]

    result2, analysis2 = trace_query_detailed(query2, chain, session_id, chat_history=chat_history)

    # ==========================================
    # FINAL SUMMARY
    # ==========================================
    print("\n\n" + "=" * 80)
    print("  TRACE SUMMARY: Context Carryover Verification")
    print("=" * 80)
    print(f"\n  Turn 1: '{query1}'")
    print(f"  Turn 2: '{query2}'")

    stored = chain._session_filters.get(session_id, {})
    filters_only = {k: v for k, v in stored.items() if not k.startswith("_")}
    print("\n  FINAL SESSION STATE:")
    print(f"    Filters: {filters_only}")
    print(f"    Search terms: {stored.get('_search_terms', [])}")


if __name__ == "__main__":
    main()
