"""Analyze user feedback from chat history to identify success patterns and failure modes.

This script extracts feedback from chat_history.db and generates insights for
improving the golden dataset with real user queries.

Usage:
    python scripts/analyze_feedback.py
    python scripts/analyze_feedback.py --output data/evaluation/feedback_analysis.json
"""

import argparse
import json
import logging
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.data.chat_storage import ChatStorage

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def _to_isoformat(timestamp) -> str | None:
    """Convert timestamp to ISO format string, handling both datetime and string types."""
    if timestamp is None:
        return None
    if isinstance(timestamp, str):
        return timestamp  # Already a string
    return timestamp.isoformat()  # datetime object


def extract_feedback_queries(storage: ChatStorage) -> dict[str, list[dict]]:
    """Extract queries with positive and negative feedback.

    Returns:
        Dict with 'positive' and 'negative' lists of feedback records
    """
    with storage.SessionLocal() as session:
        # Query for positive feedback
        positive_query = """
        SELECT
            c.id as conversation_id,
            c.session_id,
            c.content as query,
            c.timestamp as query_timestamp,
            f.comment,
            f.timestamp as feedback_timestamp
        FROM conversations c
        JOIN feedbacks f ON c.id = f.message_id
        WHERE f.is_positive = 1 AND c.role = 'user'
        ORDER BY f.timestamp DESC
        """

        # Query for negative feedback
        negative_query = """
        SELECT
            c.id as conversation_id,
            c.session_id,
            c.content as query,
            c.timestamp as query_timestamp,
            f.comment,
            f.timestamp as feedback_timestamp
        FROM conversations c
        JOIN feedbacks f ON c.id = f.message_id
        WHERE f.is_positive = 0 AND c.role = 'user'
        ORDER BY f.timestamp DESC
        """

        # Execute queries
        from sqlalchemy import text

        positive_results = session.execute(text(positive_query)).fetchall()
        negative_results = session.execute(text(negative_query)).fetchall()

        # Convert to dicts
        positive_feedback = [
            {
                "conversation_id": row[0],
                "session_id": row[1],
                "query": row[2],
                "query_timestamp": _to_isoformat(row[3]),
                "comment": row[4],
                "feedback_timestamp": _to_isoformat(row[5]),
            }
            for row in positive_results
        ]

        negative_feedback = [
            {
                "conversation_id": row[0],
                "session_id": row[1],
                "query": row[2],
                "query_timestamp": _to_isoformat(row[3]),
                "comment": row[4],
                "feedback_timestamp": _to_isoformat(row[5]),
            }
            for row in negative_results
        ]

        logger.info(
            f"Extracted {len(positive_feedback)} positive and {len(negative_feedback)} negative feedback records"
        )

        return {"positive": positive_feedback, "negative": negative_feedback}


def extract_conversational_patterns(storage: ChatStorage) -> list[dict]:
    """Extract multi-turn conversational patterns.

    Returns:
        List of conversational sessions with multiple turns
    """
    with storage.SessionLocal() as session:
        # Find sessions with multiple turns
        multi_turn_query = """
        SELECT
            session_id,
            COUNT(*) as turn_count,
            MIN(timestamp) as first_turn,
            MAX(timestamp) as last_turn
        FROM conversations
        GROUP BY session_id
        HAVING turn_count > 2
        ORDER BY turn_count DESC
        LIMIT 50
        """

        from sqlalchemy import text

        multi_turn_results = session.execute(text(multi_turn_query)).fetchall()

        conversational_sessions = []

        for row in multi_turn_results:
            session_id = row[0]
            turn_count = row[1]

            # Get all messages for this session
            messages_query = """
            SELECT role, content, timestamp
            FROM conversations
            WHERE session_id = :session_id
            ORDER BY timestamp ASC
            """

            messages = session.execute(text(messages_query), {"session_id": session_id}).fetchall()

            conversational_sessions.append(
                {
                    "session_id": session_id,
                    "turn_count": turn_count,
                    "first_turn": _to_isoformat(row[2]),
                    "last_turn": _to_isoformat(row[3]),
                    "conversation": [
                        {"role": msg[0], "content": msg[1], "timestamp": _to_isoformat(msg[2])} for msg in messages
                    ],
                }
            )

        logger.info(f"Extracted {len(conversational_sessions)} multi-turn conversations")

        return conversational_sessions


def identify_success_patterns(positive_feedback: list[dict]) -> dict[str, Any]:
    """Identify patterns in positively-rated queries.

    Args:
        positive_feedback: List of positive feedback records

    Returns:
        Dict with success pattern analysis
    """
    if not positive_feedback:
        return {"total_count": 0, "common_keywords": {}, "sample_queries": [], "insights": []}

    # Extract keywords from queries (simple word tokenization)
    all_keywords = []
    for record in positive_feedback:
        query = record["query"].lower()
        # Simple keyword extraction (remove common stopwords)
        words = query.split()
        stopwords = {"le", "la", "les", "de", "du", "à", "au", "et", "en", "pour", "the", "a", "an", "in", "on", "at"}
        keywords = [w for w in words if w not in stopwords and len(w) > 3]
        all_keywords.extend(keywords)

    # Count common keywords
    keyword_counter = Counter(all_keywords)
    common_keywords = dict(keyword_counter.most_common(20))

    # Sample queries (up to 10)
    sample_queries = [
        {"query": record["query"], "comment": record["comment"], "timestamp": record["feedback_timestamp"]}
        for record in positive_feedback[:10]
    ]

    # Generate insights
    insights = []
    if len(positive_feedback) > 0:
        insights.append(f"Total positive feedback: {len(positive_feedback)}")
        if common_keywords:
            top_keyword = list(common_keywords.keys())[0]
            insights.append(f"Most common keyword in successful queries: '{top_keyword}'")

    return {
        "total_count": len(positive_feedback),
        "common_keywords": common_keywords,
        "sample_queries": sample_queries,
        "insights": insights,
    }


def identify_failure_modes(negative_feedback: list[dict]) -> dict[str, Any]:
    """Identify patterns in negatively-rated queries.

    Args:
        negative_feedback: List of negative feedback records

    Returns:
        Dict with failure mode analysis
    """
    if not negative_feedback:
        return {"total_count": 0, "common_issues": {}, "sample_failures": [], "insights": []}

    # Extract issues from comments (if available)
    issues = []
    for record in negative_feedback:
        if record["comment"]:
            issues.append(record["comment"].lower())

    # Count common issue patterns
    issue_counter = Counter(issues)
    common_issues = dict(issue_counter.most_common(10))

    # Sample failures (up to 10)
    sample_failures = [
        {"query": record["query"], "comment": record["comment"], "timestamp": record["feedback_timestamp"]}
        for record in negative_feedback[:10]
    ]

    # Generate insights
    insights = []
    if len(negative_feedback) > 0:
        insights.append(f"Total negative feedback: {len(negative_feedback)}")
        if common_issues:
            top_issue = list(common_issues.keys())[0]
            insights.append(f"Most common issue: '{top_issue}'")

    return {
        "total_count": len(negative_feedback),
        "common_issues": common_issues,
        "sample_failures": sample_failures,
        "insights": insights,
    }


def analyze_conversational_patterns(sessions: list[dict]) -> dict[str, Any]:
    """Analyze multi-turn conversational patterns.

    Args:
        sessions: List of conversational session records

    Returns:
        Dict with conversational pattern analysis
    """
    if not sessions:
        return {"total_sessions": 0, "avg_turns": 0, "max_turns": 0, "sample_conversations": [], "insights": []}

    # Calculate statistics
    turn_counts = [s["turn_count"] for s in sessions]
    avg_turns = sum(turn_counts) / len(turn_counts)
    max_turns = max(turn_counts)

    # Sample conversations (up to 5)
    sample_conversations = [
        {
            "session_id": s["session_id"],
            "turn_count": s["turn_count"],
            "conversation": s["conversation"][:6],  # First 6 messages
        }
        for s in sessions[:5]
    ]

    # Generate insights
    insights = [
        f"Total multi-turn sessions: {len(sessions)}",
        f"Average turns per session: {avg_turns:.1f}",
        f"Longest conversation: {max_turns} turns",
    ]

    return {
        "total_sessions": len(sessions),
        "avg_turns": round(avg_turns, 1),
        "max_turns": max_turns,
        "sample_conversations": sample_conversations,
        "insights": insights,
    }


def generate_feedback_report(storage: ChatStorage) -> dict[str, Any]:
    """Generate comprehensive feedback analysis report.

    Args:
        storage: ChatStorage instance

    Returns:
        Complete feedback analysis report
    """
    logger.info("Analyzing user feedback from chat history...")

    # Extract feedback
    feedback = extract_feedback_queries(storage)

    # Extract conversational patterns
    conversational_sessions = extract_conversational_patterns(storage)

    # Analyze patterns
    success_patterns = identify_success_patterns(feedback["positive"])
    failure_modes = identify_failure_modes(feedback["negative"])
    conversational_analysis = analyze_conversational_patterns(conversational_sessions)

    # Build report
    report = {
        "analysis_metadata": {"timestamp": datetime.utcnow().isoformat(), "analysis_version": "1.0"},
        "summary": {
            "total_positive_feedback": success_patterns["total_count"],
            "total_negative_feedback": failure_modes["total_count"],
            "total_conversational_sessions": conversational_analysis["total_sessions"],
            "avg_conversation_turns": conversational_analysis["avg_turns"],
        },
        "success_patterns": success_patterns,
        "failure_modes": failure_modes,
        "conversational_patterns": conversational_analysis,
        "recommendations": generate_recommendations(success_patterns, failure_modes, conversational_analysis),
    }

    return report


def generate_recommendations(success_patterns: dict, failure_modes: dict, conversational: dict) -> list[str]:
    """Generate actionable recommendations based on feedback analysis.

    Returns:
        List of recommendation strings
    """
    recommendations = []

    # Success-based recommendations
    if success_patterns["total_count"] > 5:
        recommendations.append(
            f"Add {min(10, success_patterns['total_count'])} successful queries to golden dataset "
            "to establish positive baseline patterns"
        )

    # Failure-based recommendations
    if failure_modes["total_count"] > 5:
        recommendations.append(
            f"Add {min(10, failure_modes['total_count'])} failed queries to golden dataset "
            "to prevent regression on known failure modes"
        )

    # Conversational recommendations
    if conversational["total_sessions"] > 3:
        recommendations.append(
            f"Add {min(5, conversational['total_sessions'])} multi-turn conversational chains "
            "to test follow-up query handling"
        )

    # Keyword-based recommendations
    if success_patterns.get("common_keywords"):
        top_keywords = list(success_patterns["common_keywords"].keys())[:3]
        recommendations.append(f"Create test queries focusing on popular keywords: {', '.join(top_keywords)}")

    return recommendations


def print_summary(report: dict[str, Any]) -> None:
    """Print human-readable summary to console."""
    print("\n" + "=" * 70)
    print("FEEDBACK ANALYSIS REPORT")
    print("=" * 70)
    print(f"\nAnalysis Timestamp: {report['analysis_metadata']['timestamp']}")

    print("\n" + "SUMMARY STATISTICS:")
    print("-" * 70)
    summary = report["summary"]
    print(f"  Positive Feedback:  {summary['total_positive_feedback']} queries")
    print(f"  Negative Feedback:  {summary['total_negative_feedback']} queries")
    print(f"  Multi-turn Sessions: {summary['total_conversational_sessions']} conversations")
    print(f"  Avg Turns/Session:  {summary['avg_conversation_turns']:.1f}")

    print("\n" + "SUCCESS PATTERNS:")
    print("-" * 70)
    success = report["success_patterns"]
    if success["common_keywords"]:
        print("  Top Keywords in Successful Queries:")
        for keyword, count in list(success["common_keywords"].items())[:10]:
            print(f"    - {keyword:20s}: {count:>3} occurrences")
    else:
        print("  No success patterns identified (no positive feedback yet)")

    print("\n" + "FAILURE MODES:")
    print("-" * 70)
    failure = report["failure_modes"]
    if failure["common_issues"]:
        print("  Common Issues:")
        for issue, count in list(failure["common_issues"].items())[:5]:
            print(f"    - {issue}")
    else:
        print("  No failure modes identified (no negative feedback yet)")

    print("\n" + "CONVERSATIONAL PATTERNS:")
    print("-" * 70)
    conv = report["conversational_patterns"]
    if conv["total_sessions"] > 0:
        print(f"  Total Sessions: {conv['total_sessions']}")
        print(f"  Average Turns:  {conv['avg_turns']:.1f}")
        print(f"  Longest Chain:  {conv['max_turns']} turns")
    else:
        print("  No multi-turn conversations detected")

    print("\n" + "RECOMMENDATIONS:")
    print("-" * 70)
    for i, rec in enumerate(report["recommendations"], 1):
        print(f"  {i}. {rec}")

    print("\n" + "=" * 70)
    print(f"Analysis complete. {len(report['recommendations'])} recommendations generated.")
    print("=" * 70 + "\n")


def main():
    """Main feedback analysis execution."""
    parser = argparse.ArgumentParser(description="Analyze user feedback from chat history")
    parser.add_argument(
        "--output", default="data/evaluation/feedback_analysis.json", help="Output path for JSON report"
    )
    args = parser.parse_args()

    try:
        # Initialize chat storage
        logger.info("Loading chat history from database...")
        storage = ChatStorage()

        # Generate report
        report = generate_feedback_report(storage)

        # Print summary to console
        print_summary(report)

        # Save JSON report
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        logger.info(f"Full report saved to: {output_path}")

        # Close storage
        storage.close()

        return 0

    except Exception as e:
        logger.error(f"Feedback analysis failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
