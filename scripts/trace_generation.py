"""Trace the full generation pipeline step by step."""
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, ".")

from src.retrieval.unified_analyzer import unified_analyze
from src.retrieval.chain import (
    compose_response_prefix,
    should_apply_default_timeframe,
    apply_default_timeframe,
    build_refinement_suffix,
    detect_language_from_query
)

def trace_query(query: str, chat_history=None):
    """Trace all steps of query processing."""

    print(f"\n{'='*80}")
    print(f"QUERY: {query}")
    print('='*80)

    # ========================================
    # STEP 1: Language Detection
    # ========================================
    print(f"\n{'─'*40}")
    print("STEP 1: LANGUAGE DETECTION")
    print('─'*40)

    language = detect_language_from_query(query)
    print(f"  Detected language: {language}")

    # ========================================
    # STEP 2: Unified LLM Analysis (Multi-dimensional)
    # ========================================
    print(f"\n{'─'*40}")
    print("STEP 2: UNIFIED LLM ANALYSIS")
    print('─'*40)

    # Known cities for normalization (sample)
    known_cities = [
        "paris", "versailles", "poissy", "montreuil", "nanterre",
        "boulogne-billancourt", "saint-denis", "le plessis-robinson",
        "fontainebleau", "meaux", "pontoise", "creteil", "bobigny"
    ]

    analysis = unified_analyze(query, chat_history=chat_history or [], known_cities=known_cities)

    print(f"\n  PRIMARY INTENT: {analysis.intent.value}")
    print(f"  INTENT CONFIDENCE: {analysis.intent_confidence:.2f}")

    print(f"\n  DIMENSIONS DETECTED:")
    for name, dim in analysis.dimensions.items():
        status = "YES" if dim.detected else "no"
        print(f"    - {name}: {status}")
        if dim.detected:
            if dim.value:
                print(f"        value: {dim.value}")
            if dim.original:
                print(f"        original: {dim.original}")
            if dim.action:
                print(f"        action: {dim.action}")

    print(f"\n  ENTITY EXTRACTION:")
    print(f"    city_raw: {analysis.city}")
    print(f"    city_normalized: {analysis.city_normalized}")
    print(f"    event_type: {analysis.event_type}")
    print(f"    timeframe: {analysis.timeframe}")

    print(f"\n  FILTERS EXTRACTED:")
    for key, val in analysis.filters.items():
        if val is not None:
            print(f"    {key}: {val}")

    print(f"\n  COMPLETENESS CHECK:")
    print(f"    is_complete: {analysis.is_complete}")
    print(f"    missing_criteria: {analysis.missing_criteria}")

    # ========================================
    # STEP 3: Response Prefix Composition
    # ========================================
    print(f"\n{'─'*40}")
    print("STEP 3: RESPONSE PREFIX COMPOSITION")
    print('─'*40)

    prefix = compose_response_prefix(analysis, language)
    if prefix:
        print(f"  Prefix: \"{prefix}\"")
    else:
        print(f"  Prefix: (none)")

    print(f"\n  Components:")
    print(f"    - has_greeting: {analysis.has_greeting}")
    print(f"    - has_typo_correction: {analysis.has_typo_correction}")
    if analysis.has_typo_correction:
        print(f"        correction: {analysis.typo_correction}")

    # ========================================
    # STEP 4: Default Timeframe Check
    # ========================================
    print(f"\n{'─'*40}")
    print("STEP 4: DEFAULT TIMEFRAME CHECK")
    print('─'*40)

    filters = analysis.filters.copy()
    should_apply = should_apply_default_timeframe(filters)
    print(f"  Should apply default (30 days)? {should_apply}")
    print(f"    - has month filter: {filters.get('month') is not None}")
    print(f"    - has day filter: {filters.get('day') is not None}")
    print(f"    - has year filter: {filters.get('year') is not None}")

    if should_apply:
        filters = apply_default_timeframe(filters)
        print(f"\n  DEFAULT TIMEFRAME APPLIED:")
        print(f"    _timeframe_start: {filters.get('_timeframe_start')}")
        print(f"    _timeframe_end: {filters.get('_timeframe_end')}")

    # ========================================
    # STEP 5: Decision Point
    # ========================================
    print(f"\n{'─'*40}")
    print("STEP 5: DECISION POINT")
    print('─'*40)

    if analysis.intent.value != "event_search":
        print(f"  EARLY RETURN: Non-event intent ({analysis.intent.value})")
        print(f"  → Return pre-defined response for this intent")
    elif analysis.city and not analysis.city_normalized:
        print(f"  EARLY RETURN: Out-of-scope city ({analysis.city})")
        print(f"  → Return out-of-scope city message")
    elif not analysis.is_complete and analysis.missing_criteria:
        print(f"  EARLY RETURN: Incomplete query")
        print(f"  → Ask clarification for: {analysis.missing_criteria}")
    else:
        print(f"  CONTINUE TO RAG: Query is complete")
        print(f"  → Search with filters: {filters}")

    # ========================================
    # STEP 6: Refinement Suffix
    # ========================================
    print(f"\n{'─'*40}")
    print("STEP 6: REFINEMENT SUFFIX (if RAG continues)")
    print('─'*40)

    # Simulate has_results (would come from actual search)
    has_results = True  # Assume results found
    suffix = build_refinement_suffix(filters, has_results=has_results, language=language)
    print(f"  Suffix preview (if results found):")
    print(f"  {suffix[:200]}..." if len(suffix) > 200 else f"  {suffix}")

    # ========================================
    # STEP 7: Final Response Structure
    # ========================================
    print(f"\n{'─'*40}")
    print("STEP 7: FINAL RESPONSE STRUCTURE")
    print('─'*40)

    print(f"  Response = [PREFIX] + [RAG_ANSWER] + [SUFFIX]")
    print(f"\n  Where:")
    print(f"    PREFIX = \"{prefix or '(none)'}\"")
    print(f"    RAG_ANSWER = (generated by LLM based on retrieved events)")
    print(f"    SUFFIX = (refinement suggestions)")

    return analysis


if __name__ == "__main__":
    # Golden Dataset conv_001: Jazz concert refinement
    from langchain_core.messages import HumanMessage, AIMessage
    from src.retrieval.chain import build_filter_echo, RAGChain

    print("\n" + "="*80)
    print("GOLDEN DATASET: conv_001 - Multi-turn Jazz Concert Query")
    print("="*80)

    # Initialize chain for full end-to-end test
    chain = RAGChain()
    session_id = "golden_conv_001"

    # ==========================================
    # TURN 1: "Concerts de jazz à Paris"
    # ==========================================
    query1 = "Concerts de jazz à Paris"
    print(f"\n{'#'*80}")
    print(f"# TURN 1: {query1}")
    print('#'*80)

    analysis1 = trace_query(query1)

    # Run actual RAG
    print(f"\n{'─'*40}")
    print("STEP 8: FULL RAG EXECUTION")
    print('─'*40)
    result1 = chain.query_with_metadata(query1, session_id=session_id)
    print(f"  Events found: {len(result1.get('structured_events', []))}")
    print(f"\n  FULL RESPONSE:")
    print(f"  {'-'*60}")
    print(result1['answer'])

    # Show stored session state
    print(f"\n{'─'*40}")
    print("SESSION STATE AFTER TURN 1")
    print('─'*40)
    stored = chain._session_filters.get(session_id, {})
    filters_only = {k: v for k, v in stored.items() if not k.startswith('_')}
    print(f"  Filters: {filters_only}")
    print(f"  Search terms: {stored.get('_search_terms', [])}")

    # ==========================================
    # TURN 2: "En février plutôt" (refinement)
    # ==========================================
    query2 = "En février plutôt"
    print(f"\n\n{'#'*80}")
    print(f"# TURN 2: {query2}")
    print(f"# (Follow-up: should keep jazz/Paris, add February)")
    print('#'*80)

    # Trace with chat history
    chat_history = [
        HumanMessage(content=query1),
        AIMessage(content=result1['answer'][:200] + "...")
    ]

    print(f"\n{'─'*40}")
    print("CHAT HISTORY PASSED TO LLM")
    print('─'*40)
    for msg in chat_history:
        role = "USER" if isinstance(msg, HumanMessage) else "ASSISTANT"
        print(f"  [{role}]: {msg.content[:80]}...")

    analysis2 = trace_query(query2, chat_history=chat_history)

    # Run actual RAG
    print(f"\n{'─'*40}")
    print("STEP 8: FULL RAG EXECUTION (with context merge)")
    print('─'*40)
    result2 = chain.query_with_metadata(query2, session_id=session_id)
    print(f"  Events found: {len(result2.get('structured_events', []))}")
    print(f"\n  FULL RESPONSE:")
    print(f"  {'-'*60}")
    print(result2['answer'])

    # Show final session state
    print(f"\n{'─'*40}")
    print("SESSION STATE AFTER TURN 2")
    print('─'*40)
    stored = chain._session_filters.get(session_id, {})
    filters_only = {k: v for k, v in stored.items() if not k.startswith('_')}
    print(f"  Filters: {filters_only}")
    print(f"  Search terms: {stored.get('_search_terms', [])}")

    # ==========================================
    # FINAL SUMMARY
    # ==========================================
    print(f"\n\n{'='*80}")
    print("FINAL SUMMARY: Context Carryover Verification")
    print('='*80)
    print(f"  Turn 1 query: '{query1}'")
    print(f"  Turn 2 query: '{query2}'")
    print(f"\n  Expected behavior:")
    print(f"    - City: Paris (preserved from Turn 1)")
    print(f"    - Category: jazz/concert (preserved from Turn 1)")
    print(f"    - Month: 2 (February - added in Turn 2)")
    print(f"\n  Actual final filters: {filters_only}")
