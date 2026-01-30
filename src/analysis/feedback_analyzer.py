"""
FILE: feedback_analyzer.py
STATUS: Active
RESPONSIBILITY: User feedback analysis with pattern identification and actionable solution recommendations.

DEPENDENCIES (Who uses this file):
- src/api/endpoints.py: Uses FeedbackAnalyzer for /feedback/analysis endpoint
- tests/integration/test_feedback_integration.py: Integration tests for feedback analysis

IMPORTS (What this file needs):
- src.data.chat_storage: ChatStorage for feedback data access
- sqlalchemy: Database queries for feedback retrieval
- collections.Counter: Pattern frequency analysis

LAST MAJOR UPDATE: 2026-01-27 (Added pattern identification and proposed solutions)
MAINTAINER: Core Backend Team
"""

import logging
from collections import Counter
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select

from src.data.chat_storage import ChatStorage, ConversationRecord

logger = logging.getLogger(__name__)


class FeedbackAnalyzer:
    """Analyze user feedback to identify patterns and propose solutions."""

    def __init__(self, storage: ChatStorage) -> None:
        """Initialize analyzer with ChatStorage instance.

        Args:
            storage: ChatStorage instance for database access
        """
        self.storage = storage

    def analyze_feedback(self, days: int = 30, min_feedback_count: int = 1) -> dict[str, Any]:
        """Comprehensive feedback analysis with proposed solutions.

        Args:
            days: Number of days to analyze (default: 30)
            min_feedback_count: Minimum feedback count to include in analysis

        Returns:
            Dictionary with:
                - summary: Overall statistics
                - positive_feedback: List of positive feedback entries
                - negative_feedback: List of negative feedback entries with user queries
                - patterns: Identified patterns in feedback
                - proposed_solutions: Actionable recommendations
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        with self.storage.SessionLocal() as session:
            # Get all feedback within the time window
            query = (
                select(ConversationRecord)
                .where(
                    ConversationRecord.feedback_rating.isnot(None), ConversationRecord.feedback_timestamp >= cutoff_date
                )
                .order_by(ConversationRecord.feedback_timestamp.desc())
            )

            feedback_records = session.execute(query).scalars().all()

            if len(feedback_records) < min_feedback_count:
                return {
                    "summary": {
                        "total_feedback": 0,
                        "positive_count": 0,
                        "negative_count": 0,
                        "satisfaction_rate": 0.0,
                        "time_window_days": days,
                    },
                    "message": f"Insufficient feedback data (found {len(feedback_records)}, need {min_feedback_count})",
                }

            # Separate positive and negative feedback
            positive_feedback = []
            negative_feedback = []

            for record in feedback_records:
                # Get the corresponding user query (previous message in the same session)
                user_query_query = (
                    select(ConversationRecord)
                    .where(
                        ConversationRecord.session_id == record.session_id,
                        ConversationRecord.role == "user",
                        ConversationRecord.timestamp < record.timestamp,
                    )
                    .order_by(ConversationRecord.timestamp.desc())
                    .limit(1)
                )

                user_query_record = session.execute(user_query_query).scalar()
                user_query = user_query_record.content if user_query_record else "[Query not found]"

                feedback_entry = {
                    "message_id": record.id,
                    "session_id": record.session_id,
                    "user_query": user_query,
                    "assistant_response": record.content[:200] + "..." if len(record.content) > 200 else record.content,
                    "comment": record.feedback_comment,
                    "timestamp": record.feedback_timestamp.isoformat() if record.feedback_timestamp else None,
                }

                if record.feedback_rating == "positive":
                    positive_feedback.append(feedback_entry)
                else:
                    negative_feedback.append(feedback_entry)

            # Calculate statistics
            total_feedback = len(feedback_records)
            positive_count = len(positive_feedback)
            negative_count = len(negative_feedback)
            satisfaction_rate = (positive_count / total_feedback * 100) if total_feedback > 0 else 0.0

            # Identify patterns in negative feedback
            patterns = self._identify_patterns(negative_feedback)

            # Generate proposed solutions based on patterns
            proposed_solutions = self._generate_solutions(patterns, negative_feedback)

            return {
                "summary": {
                    "total_feedback": total_feedback,
                    "positive_count": positive_count,
                    "negative_count": negative_count,
                    "satisfaction_rate": round(satisfaction_rate, 2),
                    "time_window_days": days,
                },
                "positive_feedback": positive_feedback[:10],  # Limit to 10 most recent
                "negative_feedback": negative_feedback[:10],  # Limit to 10 most recent
                "patterns": patterns,
                "proposed_solutions": proposed_solutions,
            }

    def _identify_patterns(self, negative_feedback: list[dict]) -> dict[str, Any]:
        """Identify common patterns in negative feedback.

        Args:
            negative_feedback: List of negative feedback entries

        Returns:
            Dictionary with identified patterns
        """
        if not negative_feedback:
            return {"message": "No negative feedback to analyze"}

        # Extract comments (filter out None)
        comments = [entry["comment"] for entry in negative_feedback if entry["comment"]]

        # Common issue keywords
        issue_keywords = {
            "no_results": ["no results", "nothing found", "zero events", "aucun résultat", "aucun événement"],
            "wrong_results": ["wrong", "incorrect", "not relevant", "mauvais", "incorrect", "pas pertinent"],
            "missing_info": ["missing", "incomplete", "more details", "manque", "incomplet", "plus de détails"],
            "date_issue": ["wrong date", "date problem", "mauvaise date", "problème de date"],
            "location_issue": ["wrong city", "location problem", "mauvaise ville", "problème de lieu"],
        }

        pattern_counts = Counter()
        for comment in comments:
            comment_lower = comment.lower() if comment else ""
            for issue_type, keywords in issue_keywords.items():
                if any(keyword in comment_lower for keyword in keywords):
                    pattern_counts[issue_type] += 1

        return {
            "total_negative_with_comments": len(comments),
            "total_negative_without_comments": len(negative_feedback) - len(comments),
            "issue_breakdown": dict(pattern_counts),
            "most_common_issue": pattern_counts.most_common(1)[0][0] if pattern_counts else None,
        }

    def _generate_solutions(self, patterns: dict[str, Any], negative_feedback: list[dict]) -> list[dict[str, str]]:
        """Generate actionable solutions based on identified patterns.

        Args:
            patterns: Identified patterns from negative feedback
            negative_feedback: List of negative feedback entries

        Returns:
            List of proposed solutions with priority and description
        """
        solutions = []

        if not patterns or "issue_breakdown" not in patterns:
            return solutions

        issue_breakdown = patterns["issue_breakdown"]

        # Solution for "no_results" issue
        if issue_breakdown.get("no_results", 0) > 0:
            solutions.append(
                {
                    "priority": "HIGH",
                    "issue": "No Results Found",
                    "count": issue_breakdown["no_results"],
                    "proposed_solution": (
                        "1. Review filter extraction logic to ensure dates/locations are correctly parsed. "
                        "2. Implement query broadening suggestions when zero results are found. "
                        "3. Check if events database has sufficient coverage for queried time periods. "
                        "4. Consider adding 'nearby events' suggestions when exact matches fail."
                    ),
                    "actionable_steps": [
                        "Analyze queries with zero results to identify common filter patterns",
                        "Add fallback logic for date range expansion (e.g., ±1 week)",
                        "Implement geographic radius search when city-specific queries fail",
                        "Enhance clarification prompts for ambiguous queries",
                    ],
                }
            )

        # Solution for "wrong_results" issue
        if issue_breakdown.get("wrong_results", 0) > 0:
            solutions.append(
                {
                    "priority": "HIGH",
                    "issue": "Wrong or Irrelevant Results",
                    "count": issue_breakdown["wrong_results"],
                    "proposed_solution": (
                        "1. Review retrieval scoring (BM25 + FAISS hybrid weights). "
                        "2. Analyze if entity extraction is missing key filters (category, audience, etc.). "
                        "3. Consider adding reranking layer to improve relevance. "
                        "4. Validate that semantic search embeddings capture query intent."
                    ),
                    "actionable_steps": [
                        "Run evaluation on queries marked as 'wrong results' to identify retrieval gaps",
                        "Tune RRF (Reciprocal Rank Fusion) weights between BM25 and FAISS",
                        "Add negative examples to golden dataset for reranker training",
                        "Review if category classification is too broad (e.g., 'Musique' vs 'Jazz')",
                    ],
                }
            )

        # Solution for "missing_info" issue
        if issue_breakdown.get("missing_info", 0) > 0:
            solutions.append(
                {
                    "priority": "MEDIUM",
                    "issue": "Missing or Incomplete Information",
                    "count": issue_breakdown["missing_info"],
                    "proposed_solution": (
                        "1. Enrich event metadata (scraped_content, tags) using LLM extraction. "
                        "2. Add more detailed fields to response (ticket price, age range, accessibility). "
                        "3. Include URLs and contact information in generated responses. "
                        "4. Summarize event details more comprehensively in LLM generation."
                    ),
                    "actionable_steps": [
                        "Run LLM enrichment script to fill sparse fields (scraped_content, tags)",
                        "Update response template to include more event metadata",
                        "Add 'show more details' option to API responses",
                        "Validate that event URLs are functional and included in responses",
                    ],
                }
            )

        # Solution for "date_issue" issue
        if issue_breakdown.get("date_issue", 0) > 0:
            solutions.append(
                {
                    "priority": "HIGH",
                    "issue": "Date Parsing or Filtering Issues",
                    "count": issue_breakdown["date_issue"],
                    "proposed_solution": (
                        "1. Review date extraction logic for edge cases (relative dates, month names, etc.). "
                        "2. Validate that date filters are correctly applied to database queries. "
                        "3. Add better handling for 'this weekend', 'next month', etc. "
                        "4. Ensure bilingual date parsing works correctly (French month names)."
                    ),
                    "actionable_steps": [
                        "Test date extraction on queries with negative feedback",
                        "Add unit tests for relative date parsing ('ce week-end', 'la semaine prochaine')",
                        "Verify that database date filters use correct timezone (UTC vs local)",
                        "Add date validation before querying database",
                    ],
                }
            )

        # Solution for "location_issue" issue
        if issue_breakdown.get("location_issue", 0) > 0:
            solutions.append(
                {
                    "priority": "MEDIUM",
                    "issue": "Location Parsing or Filtering Issues",
                    "count": issue_breakdown["location_issue"],
                    "proposed_solution": (
                        "1. Review city normalization logic (Paris vs PARIS vs paris). "
                        "2. Add location alias support (e.g., 'capital' → Paris). "
                        "3. Implement fuzzy matching for misspelled city names. "
                        "4. Consider adding arrondissement support (e.g., 'Paris 11e')."
                    ),
                    "actionable_steps": [
                        "Analyze queries with location issues to identify common patterns",
                        "Add city alias mapping (e.g., 'la capitale' → 'Paris')",
                        "Implement Levenshtein distance for city name fuzzy matching",
                        "Add geographic hierarchy support (arrondissement → city → region)",
                    ],
                }
            )

        # General solution if negative feedback exists but no specific patterns
        if not solutions and len(negative_feedback) > 0:
            solutions.append(
                {
                    "priority": "MEDIUM",
                    "issue": "General Negative Feedback Without Specific Comments",
                    "count": len(negative_feedback),
                    "proposed_solution": (
                        "1. Encourage users to provide detailed feedback comments. "
                        "2. Add optional feedback form with specific issue categories. "
                        "3. Log full query context (filters applied, retrieval count, response latency) for debugging. "
                        "4. Review queries with negative feedback manually to identify common issues."
                    ),
                    "actionable_steps": [
                        "Update feedback UI to include issue category dropdown",
                        "Add detailed logging for queries that receive negative feedback",
                        "Schedule regular manual review of negative feedback queries",
                        "Create dashboard to visualize feedback trends over time",
                    ],
                }
            )

        # Sort solutions by priority (HIGH first)
        priority_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
        solutions.sort(key=lambda x: priority_order.get(x["priority"], 3))

        return solutions

    def get_negative_feedback_queries(self, days: int = 30, limit: int = 20) -> list[dict[str, Any]]:
        """Extract queries that received negative feedback for detailed analysis.

        Args:
            days: Number of days to look back
            limit: Maximum number of queries to return

        Returns:
            List of dicts with query, response, feedback comment, and timestamp
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        with self.storage.SessionLocal() as session:
            # Get negative feedback records
            query = (
                select(ConversationRecord)
                .where(
                    ConversationRecord.feedback_rating == "negative",
                    ConversationRecord.feedback_timestamp >= cutoff_date,
                )
                .order_by(ConversationRecord.feedback_timestamp.desc())
                .limit(limit)
            )

            negative_records = session.execute(query).scalars().all()

            results = []
            for record in negative_records:
                # Get the corresponding user query
                user_query_query = (
                    select(ConversationRecord)
                    .where(
                        ConversationRecord.session_id == record.session_id,
                        ConversationRecord.role == "user",
                        ConversationRecord.timestamp < record.timestamp,
                    )
                    .order_by(ConversationRecord.timestamp.desc())
                    .limit(1)
                )

                user_query_record = session.execute(user_query_query).scalar()

                results.append(
                    {
                        "message_id": record.id,
                        "session_id": record.session_id,
                        "user_query": user_query_record.content if user_query_record else "[Query not found]",
                        "assistant_response": record.content,
                        "feedback_comment": record.feedback_comment,
                        "feedback_timestamp": (
                            record.feedback_timestamp.isoformat() if record.feedback_timestamp else None
                        ),
                    }
                )

            return results

    def get_satisfaction_rate(self, days: int = 30) -> dict[str, Any]:
        """Calculate satisfaction rate over a time period.

        Args:
            days: Number of days to analyze

        Returns:
            Dictionary with satisfaction statistics
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        with self.storage.SessionLocal() as session:
            # Count positive feedback
            positive_query = select(ConversationRecord).where(
                ConversationRecord.feedback_rating == "positive", ConversationRecord.feedback_timestamp >= cutoff_date
            )
            positive_count = len(session.execute(positive_query).scalars().all())

            # Count negative feedback
            negative_query = select(ConversationRecord).where(
                ConversationRecord.feedback_rating == "negative", ConversationRecord.feedback_timestamp >= cutoff_date
            )
            negative_count = len(session.execute(negative_query).scalars().all())

            total_feedback = positive_count + negative_count
            satisfaction_rate = (positive_count / total_feedback * 100) if total_feedback > 0 else 0.0

            return {
                "time_window_days": days,
                "total_feedback": total_feedback,
                "positive_count": positive_count,
                "negative_count": negative_count,
                "satisfaction_rate": round(satisfaction_rate, 2),
            }
