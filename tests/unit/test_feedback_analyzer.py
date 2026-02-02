"""
FILE: test_feedback_analyzer.py
STATUS: Active
RESPONSIBILITY: Unit tests for FeedbackAnalyzer class.
LAST MAJOR UPDATE: 2026-01-31
MAINTAINER: QA Team
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timedelta

from src.analysis.feedback_analyzer import FeedbackAnalyzer


class TestFeedbackAnalyzerPatterns:
    """Test pattern identification in FeedbackAnalyzer."""

    def test_identify_patterns_no_feedback(self):
        """Test pattern identification with no negative feedback."""
        mock_storage = Mock()
        analyzer = FeedbackAnalyzer(storage=mock_storage)

        patterns = analyzer._identify_patterns([])
        assert patterns["message"] == "No negative feedback to analyze"

    def test_identify_patterns_no_results_issue(self):
        """Test pattern identification for no_results issue."""
        mock_storage = Mock()
        analyzer = FeedbackAnalyzer(storage=mock_storage)

        negative_feedback = [
            {"comment": "No results found for my query"},
            {"comment": "Zero events returned, but I know there should be some"},
            {"comment": None},  # No comment
        ]

        patterns = analyzer._identify_patterns(negative_feedback)

        assert patterns["total_negative_with_comments"] == 2
        assert patterns["total_negative_without_comments"] == 1
        assert patterns["issue_breakdown"]["no_results"] == 2

    def test_identify_patterns_wrong_results_issue(self):
        """Test pattern identification for wrong_results issue."""
        mock_storage = Mock()
        analyzer = FeedbackAnalyzer(storage=mock_storage)

        negative_feedback = [
            {"comment": "Results were not relevant to my query"},
            {"comment": "Wrong events shown"},
        ]

        patterns = analyzer._identify_patterns(negative_feedback)

        assert patterns["issue_breakdown"]["wrong_results"] == 2
        assert patterns["most_common_issue"] == "wrong_results"

    def test_identify_patterns_date_issue(self):
        """Test pattern identification for date issues."""
        mock_storage = Mock()
        analyzer = FeedbackAnalyzer(storage=mock_storage)

        negative_feedback = [
            {"comment": "Wrong date for the event"},
            {"comment": "Date problem - showed past events"},
        ]

        patterns = analyzer._identify_patterns(negative_feedback)

        assert patterns["issue_breakdown"]["date_issue"] == 2

    def test_identify_patterns_location_issue(self):
        """Test pattern identification for location issues."""
        mock_storage = Mock()
        analyzer = FeedbackAnalyzer(storage=mock_storage)

        negative_feedback = [
            {"comment": "Wrong city - I asked for Paris not Lyon"},
            {"comment": "Location problem with the results"},
        ]

        patterns = analyzer._identify_patterns(negative_feedback)

        assert patterns["issue_breakdown"]["location_issue"] == 2

    def test_identify_patterns_mixed_issues(self):
        """Test pattern identification with mixed issues."""
        mock_storage = Mock()
        analyzer = FeedbackAnalyzer(storage=mock_storage)

        negative_feedback = [
            {"comment": "No results found"},
            {"comment": "Wrong results returned"},
            {"comment": "Zero events but should have some"},  # matches no_results
            {"comment": "Missing information about prices"},
        ]

        patterns = analyzer._identify_patterns(negative_feedback)

        # "no_results" appears twice
        assert patterns["issue_breakdown"]["no_results"] == 2
        assert patterns["issue_breakdown"]["wrong_results"] == 1
        assert patterns["issue_breakdown"]["missing_info"] == 1


class TestFeedbackAnalyzerSolutions:
    """Test solution generation in FeedbackAnalyzer."""

    def test_generate_solutions_empty_patterns(self):
        """Test solution generation with empty patterns."""
        mock_storage = Mock()
        analyzer = FeedbackAnalyzer(storage=mock_storage)

        solutions = analyzer._generate_solutions({}, [])
        assert solutions == []

    def test_generate_solutions_no_results(self):
        """Test solution generation for no_results issue."""
        mock_storage = Mock()
        analyzer = FeedbackAnalyzer(storage=mock_storage)

        patterns = {
            "issue_breakdown": {"no_results": 5}
        }

        solutions = analyzer._generate_solutions(patterns, [])

        assert len(solutions) == 1
        assert solutions[0]["issue"] == "No Results Found"
        assert solutions[0]["priority"] == "HIGH"
        assert solutions[0]["count"] == 5
        assert "filter extraction" in solutions[0]["proposed_solution"]

    def test_generate_solutions_wrong_results(self):
        """Test solution generation for wrong_results issue."""
        mock_storage = Mock()
        analyzer = FeedbackAnalyzer(storage=mock_storage)

        patterns = {
            "issue_breakdown": {"wrong_results": 3}
        }

        solutions = analyzer._generate_solutions(patterns, [])

        assert len(solutions) == 1
        assert solutions[0]["issue"] == "Wrong or Irrelevant Results"
        assert solutions[0]["priority"] == "HIGH"

    def test_generate_solutions_multiple_issues(self):
        """Test solution generation for multiple issues."""
        mock_storage = Mock()
        analyzer = FeedbackAnalyzer(storage=mock_storage)

        patterns = {
            "issue_breakdown": {
                "no_results": 5,
                "wrong_results": 3,
                "missing_info": 2,
            }
        }

        solutions = analyzer._generate_solutions(patterns, [])

        # Should have 3 solutions
        assert len(solutions) == 3
        # HIGH priority solutions should be first
        assert solutions[0]["priority"] == "HIGH"
        assert solutions[1]["priority"] == "HIGH"
        assert solutions[2]["priority"] == "MEDIUM"

    def test_generate_solutions_no_specific_patterns(self):
        """Test solution generation when no specific patterns but has negative feedback."""
        mock_storage = Mock()
        analyzer = FeedbackAnalyzer(storage=mock_storage)

        patterns = {
            "issue_breakdown": {}
        }

        negative_feedback = [
            {"comment": None},
            {"comment": None},
        ]

        solutions = analyzer._generate_solutions(patterns, negative_feedback)

        assert len(solutions) == 1
        assert solutions[0]["issue"] == "General Negative Feedback Without Specific Comments"

    def test_solution_has_actionable_steps(self):
        """Test that solutions include actionable steps."""
        mock_storage = Mock()
        analyzer = FeedbackAnalyzer(storage=mock_storage)

        patterns = {
            "issue_breakdown": {"date_issue": 2}
        }

        solutions = analyzer._generate_solutions(patterns, [])

        assert len(solutions) == 1
        assert "actionable_steps" in solutions[0]
        assert len(solutions[0]["actionable_steps"]) > 0


class TestFeedbackAnalyzerInit:
    """Test FeedbackAnalyzer initialization."""

    def test_init_with_storage(self):
        """Test analyzer initialization with storage."""
        mock_storage = Mock()
        analyzer = FeedbackAnalyzer(storage=mock_storage)

        assert analyzer.storage == mock_storage


class TestFeedbackAnalyzerFrenchKeywords:
    """Test pattern identification with French keywords."""

    def test_identify_patterns_french_no_results(self):
        """Test French keywords for no_results issue."""
        mock_storage = Mock()
        analyzer = FeedbackAnalyzer(storage=mock_storage)

        negative_feedback = [
            {"comment": "Aucun résultat trouvé"},
            {"comment": "Aucun événement pour cette date"},
        ]

        patterns = analyzer._identify_patterns(negative_feedback)

        assert patterns["issue_breakdown"]["no_results"] == 2

    def test_identify_patterns_french_wrong_results(self):
        """Test French keywords for wrong_results issue."""
        mock_storage = Mock()
        analyzer = FeedbackAnalyzer(storage=mock_storage)

        negative_feedback = [
            {"comment": "Résultats pas pertinents"},
            {"comment": "Mauvaise information affichée"},
        ]

        patterns = analyzer._identify_patterns(negative_feedback)

        assert patterns["issue_breakdown"]["wrong_results"] == 2

    def test_identify_patterns_french_date_issue(self):
        """Test French keywords for date issues."""
        mock_storage = Mock()
        analyzer = FeedbackAnalyzer(storage=mock_storage)

        negative_feedback = [
            {"comment": "Mauvaise date pour l'événement"},
            {"comment": "Problème de date avec les résultats"},
        ]

        patterns = analyzer._identify_patterns(negative_feedback)

        assert patterns["issue_breakdown"]["date_issue"] == 2


class TestFeedbackAnalyzerLocationIssue:
    """Test pattern identification for location issues."""

    def test_generate_solutions_location_issue(self):
        """Test solution generation for location_issue."""
        mock_storage = Mock()
        analyzer = FeedbackAnalyzer(storage=mock_storage)

        patterns = {
            "issue_breakdown": {"location_issue": 3}
        }

        solutions = analyzer._generate_solutions(patterns, [])

        assert len(solutions) == 1
        assert solutions[0]["issue"] == "Location Parsing or Filtering Issues"
        assert solutions[0]["priority"] == "MEDIUM"
        assert solutions[0]["count"] == 3
        assert "city normalization" in solutions[0]["proposed_solution"]


class TestFeedbackAnalyzerEdgeCases:
    """Test edge cases in FeedbackAnalyzer."""

    def test_identify_patterns_empty_comments(self):
        """Test pattern identification with empty comments."""
        mock_storage = Mock()
        analyzer = FeedbackAnalyzer(storage=mock_storage)

        negative_feedback = [
            {"comment": ""},  # Empty string
            {"comment": None},  # None
        ]

        patterns = analyzer._identify_patterns(negative_feedback)

        assert patterns["total_negative_with_comments"] == 0
        assert patterns["total_negative_without_comments"] == 2

    def test_generate_solutions_date_issue(self):
        """Test solution generation for date_issue."""
        mock_storage = Mock()
        analyzer = FeedbackAnalyzer(storage=mock_storage)

        patterns = {
            "issue_breakdown": {"date_issue": 4}
        }

        solutions = analyzer._generate_solutions(patterns, [])

        assert len(solutions) == 1
        assert solutions[0]["issue"] == "Date Parsing or Filtering Issues"
        assert solutions[0]["priority"] == "HIGH"

    def test_generate_solutions_missing_info(self):
        """Test solution generation for missing_info issue."""
        mock_storage = Mock()
        analyzer = FeedbackAnalyzer(storage=mock_storage)

        patterns = {
            "issue_breakdown": {"missing_info": 2}
        }

        solutions = analyzer._generate_solutions(patterns, [])

        assert len(solutions) == 1
        assert solutions[0]["issue"] == "Missing or Incomplete Information"
        assert solutions[0]["priority"] == "MEDIUM"

    def test_generate_solutions_sorting_by_priority(self):
        """Test that solutions are sorted by priority (HIGH first)."""
        mock_storage = Mock()
        analyzer = FeedbackAnalyzer(storage=mock_storage)

        patterns = {
            "issue_breakdown": {
                "missing_info": 2,  # MEDIUM
                "no_results": 5,  # HIGH
                "location_issue": 1,  # MEDIUM
            }
        }

        solutions = analyzer._generate_solutions(patterns, [])

        # HIGH priority should come first
        assert solutions[0]["priority"] == "HIGH"
        # MEDIUM priority should follow
        assert all(s["priority"] == "MEDIUM" for s in solutions[1:])


class TestFeedbackAnalyzerMostCommonIssue:
    """Test most_common_issue identification."""

    def test_most_common_issue_identification(self):
        """Test that most common issue is correctly identified."""
        mock_storage = Mock()
        analyzer = FeedbackAnalyzer(storage=mock_storage)

        negative_feedback = [
            {"comment": "No results found"},
            {"comment": "Zero events returned"},
            {"comment": "Nothing found for this date"},
            {"comment": "Wrong results shown"},
        ]

        patterns = analyzer._identify_patterns(negative_feedback)

        # no_results appears 3 times, wrong_results 1 time
        assert patterns["most_common_issue"] == "no_results"


class TestFeedbackAnalyzerFrenchLocationIssue:
    """Test French keywords for location issues."""

    def test_identify_patterns_french_location_issue(self):
        """Test French keywords for location_issue."""
        mock_storage = Mock()
        analyzer = FeedbackAnalyzer(storage=mock_storage)

        negative_feedback = [
            {"comment": "Mauvaise ville dans les résultats"},
            {"comment": "Problème de lieu - j'ai demandé Paris"},
        ]

        patterns = analyzer._identify_patterns(negative_feedback)

        assert patterns["issue_breakdown"]["location_issue"] == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
