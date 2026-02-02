"""Run golden dataset queries and capture actual chatbot responses for review.

This script:
1. Loads the golden dataset
2. Runs each query through the RAG chain
3. Captures the actual chatbot response
4. Saves everything to a review-friendly YAML format

Usage:
    python scripts/run_queries_for_review.py
    python scripts/run_queries_for_review.py --limit 10  # Only first 10 queries
"""

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.retrieval.chain import RAGChain
from src.data.storage import EventStorage
from datetime import date

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def query_database_directly(query_data: dict, storage: EventStorage) -> dict[str, Any]:
    """Query database directly based on expected filters to validate ground truth.

    Args:
        query_data: Query data from golden dataset (with expected_filters)
        storage: EventStorage instance

    Returns:
        Dict with matching events from database
    """
    try:
        expected_filters = query_data.get("expected_filters", {})

        # Build filters from expected values
        city = expected_filters.get("city")
        category = expected_filters.get("category")

        # Handle date filters
        month = expected_filters.get("month")
        year = expected_filters.get("year", 2026)
        date_min = None
        date_max = None

        if month:
            date_min = date(year, month, 1)
            if month == 12:
                date_max = date(year + 1, 1, 1)
            else:
                date_max = date(year, month + 1, 1)

        # Query database
        all_events = storage.get_all_events()

        # Apply filters manually
        matching_events = []
        for event in all_events:
            # City filter
            if city and event.location and event.location.city:
                if event.location.city.lower() != city.lower():
                    continue

            # Category filter
            if category and event.category:
                if event.category.lower() != category.lower():
                    continue

            # Date filter
            if date_min and date_max and event.start_date:
                event_date = event.start_date.date() if hasattr(event.start_date, "date") else event.start_date
                if not (date_min <= event_date < date_max):
                    continue

            matching_events.append(
                {
                    "event_id": event.event_id,
                    "title": event.title,
                    "city": event.location.city if event.location else "Unknown",
                    "category": event.category or "Unknown",
                    "date": str(event.start_date) if event.start_date else "Unknown",
                }
            )

        return {
            "success": True,
            "filters_used": {"city": city, "category": category, "month": month, "year": year},
            "total_matching": len(matching_events),
            "events": matching_events[:10],  # Limit to first 10
            "error": None,
        }
    except Exception as e:
        logger.error(f"Database query failed: {e}", exc_info=True)
        return {"success": False, "filters_used": {}, "total_matching": 0, "events": [], "error": str(e)}


def run_query_and_capture(chain: RAGChain, query: str, language: str = "fr") -> dict[str, Any]:
    """Run a query through the RAG chain and capture the full response.

    Args:
        chain: Initialized RAGChain instance
        query: Query string to execute
        language: Language code (fr or en)

    Returns:
        Dict with answer, sources, and metadata
    """
    try:
        # Use unique session_id to bypass cache (for fresh results)
        import uuid

        unique_session_id = f"review_{uuid.uuid4().hex[:8]}"
        result = chain.query_with_metadata(query, session_id=unique_session_id, language=language)

        # Format sources for readability
        formatted_sources = []
        for src in result.get("sources", []):
            formatted_sources.append(
                {
                    "event_id": src.get("event_id"),
                    "title": src.get("title"),
                    "city": src.get("city"),
                    "category": src.get("category"),
                    "score": src.get("score"),
                    "match_type": src.get("match_type"),
                }
            )

        return {
            "success": True,
            "answer": result.get("answer", ""),
            "sources": formatted_sources,
            "retrieval_stats": result.get("retrieval_stats", {}),
            "error": None,
        }
    except Exception as e:
        logger.error(f"Error running query '{query}': {e}")
        return {"success": False, "answer": None, "sources": [], "retrieval_stats": {}, "error": str(e)}


def generate_review_yaml(
    dataset: dict, responses: dict[str, dict], db_results: dict[str, dict], output_path: str
) -> None:
    """Generate a review-friendly YAML file with queries, expected results, actual responses, and database validation.

    Args:
        dataset: Original golden dataset
        responses: Dict mapping query IDs to chatbot responses
        db_results: Dict mapping query IDs to database query results
        output_path: Path to save the review YAML
    """
    yaml_lines = []

    # Header
    yaml_lines.append("# Golden Dataset Review File")
    yaml_lines.append("# Generated: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    yaml_lines.append("#")
    yaml_lines.append("# How to use this file:")
    yaml_lines.append("#   1. Review EXPECTED GROUND TRUTH (what should be returned)")
    yaml_lines.append("#   2. Review ACTUAL CHATBOT RESPONSE (what was returned)")
    yaml_lines.append("#   3. Review DATABASE VALIDATION (what exists in database)")
    yaml_lines.append("#   4. Compare all three to identify issues:")
    yaml_lines.append("#      - If DB has events but chatbot didn't return them → retrieval issue")
    yaml_lines.append("#      - If chatbot returned events not in ground truth → relevance issue")
    yaml_lines.append("#      - If DB doesn't have expected events → data quality issue")
    yaml_lines.append("#   5. Add your REVIEW NOTES with feedback")
    yaml_lines.append("#   6. Mark queries as APPROVED or NEEDS_IMPROVEMENT")
    yaml_lines.append("#")
    yaml_lines.append("")

    queries = dataset.get("queries", [])

    for i, query_data in enumerate(queries):
        query_id = query_data["id"]
        response = responses.get(query_id, {})
        db_result = db_results.get(query_id, {})

        # Query header
        yaml_lines.append(f"# ========== QUERY {i+1}/{len(queries)}: {query_id} ==========")
        yaml_lines.append("")

        yaml_lines.append(f"- id: {query_id}")
        yaml_lines.append(f"  query: \"{query_data['query']}\"")
        yaml_lines.append(f"  language: {query_data.get('language', 'fr')}")
        yaml_lines.append(f"  complexity: {query_data.get('complexity', 'unknown')}")
        yaml_lines.append("")

        # SECTION 1: Expected Ground Truth
        yaml_lines.append("  # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        yaml_lines.append("  # 📋 EXPECTED GROUND TRUTH (what SHOULD be returned)")
        yaml_lines.append("  # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        yaml_lines.append("  expected_ground_truth:")

        for gt in query_data.get("relevance_ground_truth", []):
            yaml_lines.append(f"    - event_id: \"{gt['event_id']}\"")
            yaml_lines.append(f"      relevance_score: {gt['relevance_score']}")
            yaml_lines.append(f"      reason: \"{gt.get('reason', 'No reason provided')}\"")
            yaml_lines.append("")

        if not query_data.get("relevance_ground_truth"):
            yaml_lines.append("    []  # No ground truth defined")
            yaml_lines.append("")

        # SECTION 2: Actual Chatbot Response
        yaml_lines.append("  # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        yaml_lines.append("  # 🤖 ACTUAL CHATBOT RESPONSE (what WAS returned)")
        yaml_lines.append("  # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        yaml_lines.append("  actual_response:")

        if response.get("success"):
            yaml_lines.append("    status: SUCCESS")
            yaml_lines.append("    answer: |")
            # Indent multi-line answer
            answer_lines = response["answer"].split("\n")
            for line in answer_lines[:10]:  # Limit to first 10 lines
                yaml_lines.append(f"      {line}")
            if len(answer_lines) > 10:
                yaml_lines.append(f"      ... ({len(answer_lines) - 10} more lines)")
            yaml_lines.append("")

            yaml_lines.append("    sources_returned:")
            for src in response.get("sources", [])[:5]:  # Show top 5 sources
                score = src.get("score")
                if score is None:
                    score = 0.0

                yaml_lines.append(f"      - event_id: \"{src['event_id']}\"")
                yaml_lines.append(f"        title: \"{src['title']}\"")
                yaml_lines.append(f"        city: {src.get('city', 'N/A')}")
                yaml_lines.append(f"        score: {score:.3f}")
                yaml_lines.append(f"        match_type: {src.get('match_type', 'Unknown')}")
                yaml_lines.append("")

            stats = response.get("retrieval_stats", {})
            yaml_lines.append("    retrieval_stats:")
            yaml_lines.append(f"      exact_matches: {stats.get('exact_count', 0)}")
            yaml_lines.append(f"      total_returned: {stats.get('total_count', 0)}")
            yaml_lines.append("")
        else:
            yaml_lines.append("    status: ERROR")
            yaml_lines.append(f"    error: \"{response.get('error', 'Unknown error')}\"")
            yaml_lines.append("")

        # SECTION 3: Database Validation (Direct Query)
        yaml_lines.append("  # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        yaml_lines.append("  # 🔍 DATABASE VALIDATION (direct database query)")
        yaml_lines.append("  # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        yaml_lines.append("  database_query:")

        if db_result.get("success"):
            yaml_lines.append("    status: SUCCESS")
            filters_used = db_result.get("filters_used", {})
            yaml_lines.append("    filters_applied:")
            yaml_lines.append(f"      city: {filters_used.get('city', 'None')}")
            yaml_lines.append(f"      category: {filters_used.get('category', 'None')}")
            yaml_lines.append(f"      month: {filters_used.get('month', 'None')}")
            yaml_lines.append(f"      year: {filters_used.get('year', 'None')}")
            yaml_lines.append("")

            yaml_lines.append(f"    total_matching_events: {db_result.get('total_matching', 0)}")
            yaml_lines.append("")

            yaml_lines.append("    matching_events_sample:")
            events = db_result.get("events", [])
            if events:
                for evt in events:
                    yaml_lines.append(f"      - event_id: \"{evt['event_id']}\"")
                    yaml_lines.append(f"        title: \"{evt['title']}\"")
                    yaml_lines.append(f"        city: {evt.get('city', 'N/A')}")
                    yaml_lines.append(f"        category: {evt.get('category', 'N/A')}")
                    yaml_lines.append(f"        date: {evt.get('date', 'N/A')}")
                    yaml_lines.append("")
            else:
                yaml_lines.append("      []  # No matching events in database")
                yaml_lines.append("")

            yaml_lines.append("    # INTERPRETATION:")
            yaml_lines.append("    interpretation: |")
            yaml_lines.append(
                f"      Database contains {db_result.get('total_matching', 0)} events matching the filters."
            )
            yaml_lines.append("      Compare this to:")
            yaml_lines.append(
                f"      - Ground truth expected: {len(query_data.get('relevance_ground_truth', []))} events"
            )
            yaml_lines.append(f"      - Chatbot returned: {len(response.get('sources', []))} sources")
            yaml_lines.append("")
        else:
            yaml_lines.append("    status: ERROR")
            yaml_lines.append(f"    error: \"{db_result.get('error', 'Unknown error')}\"")
            yaml_lines.append("")

        # SECTION 4: Review & Feedback
        yaml_lines.append("  # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        yaml_lines.append("  # ✍️ YOUR REVIEW (add your feedback here)")
        yaml_lines.append("  # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        yaml_lines.append("  review:")
        yaml_lines.append("    status: PENDING  # Change to: APPROVED or NEEDS_IMPROVEMENT")
        yaml_lines.append("")
        yaml_lines.append("    # Compare actual vs expected:")
        yaml_lines.append("    comparison_notes: |")
        yaml_lines.append("      # Did the chatbot return the right events?")
        yaml_lines.append("      # Was the answer accurate and helpful?")
        yaml_lines.append("      # Any hallucinations or errors?")
        yaml_lines.append("")

        yaml_lines.append("    # Issues found:")
        yaml_lines.append("    issues:")
        yaml_lines.append("      - # List any problems here")
        yaml_lines.append("")

        yaml_lines.append("    # Improvements needed:")
        yaml_lines.append("    improvements:")
        yaml_lines.append("      - # Suggest improvements here")
        yaml_lines.append("")

        yaml_lines.append("  # " + "─" * 70)
        yaml_lines.append("")

    # Write file
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(yaml_lines))

    logger.info(f"Review YAML written to: {output_path}")


def main():
    """Main execution."""
    parser = argparse.ArgumentParser(description="Run queries and generate review file")
    parser.add_argument("--input", default="data/evaluation/golden_dataset.json", help="Input golden dataset JSON")
    parser.add_argument(
        "--output", default="data/evaluation/golden_dataset_review.yaml", help="Output review YAML path"
    )
    parser.add_argument("--limit", type=int, default=None, help="Limit number of queries to run (for testing)")
    args = parser.parse_args()

    try:
        # Load golden dataset
        logger.info(f"Loading golden dataset from {args.input}")
        with open(args.input, "r", encoding="utf-8") as f:
            dataset = json.load(f)

        queries = dataset.get("queries", [])
        if args.limit:
            queries = queries[: args.limit]
            logger.info(f"Limited to first {args.limit} queries")

        # Initialize RAG chain and EventStorage
        logger.info("Initializing RAG chain...")
        chain = RAGChain()
        logger.info("Initializing EventStorage for database validation...")
        storage = EventStorage()

        # Run each query through chatbot AND database
        responses = {}
        db_results = {}
        for i, query_data in enumerate(queries):
            query_id = query_data["id"]
            query_text = query_data["query"]
            language = query_data.get("language", "fr")

            logger.info(f"Running query {i+1}/{len(queries)}: {query_id}")
            logger.info(f"  Query: {query_text}")

            # Run through chatbot
            response = run_query_and_capture(chain, query_text, language)
            responses[query_id] = response

            if response["success"]:
                logger.info(f"  ✓ Chatbot Success - {len(response['sources'])} sources returned")
            else:
                logger.error(f"  ✗ Chatbot Error: {response['error']}")

            # Run direct database query
            db_result = query_database_directly(query_data, storage)
            db_results[query_id] = db_result

            if db_result["success"]:
                logger.info(f"  ✓ Database Query - {db_result['total_matching']} matching events found")
            else:
                logger.error(f"  ✗ Database Error: {db_result['error']}")

        # Generate review YAML
        logger.info("\nGenerating review YAML...")
        generate_review_yaml(dataset, responses, db_results, args.output)

        # Print summary
        print("\n" + "=" * 70)
        print("REVIEW FILE GENERATED")
        print("=" * 70)
        print(f"Input:  {args.input}")
        print(f"Output: {args.output}")
        print(f"Queries processed: {len(responses)}")
        print(f"Successful: {sum(1 for r in responses.values() if r['success'])}")
        print(f"Errors: {sum(1 for r in responses.values() if not r['success'])}")
        print("\nNext steps:")
        print(f"  1. Open {args.output}")
        print("  2. Review each query's ACTUAL vs EXPECTED results")
        print("  3. Add your feedback in the REVIEW sections")
        print("  4. Mark queries as APPROVED or NEEDS_IMPROVEMENT")
        print("=" * 70 + "\n")

        return 0

    except Exception as e:
        logger.error(f"Failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
