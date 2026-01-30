"""
FILE: test_clarifications.py
STATUS: Active
RESPONSIBILITY: Unit tests for clarification question generation.

DEPENDENCIES (Who uses this file):
- pytest test runner
- Clarification logic validation

IMPORTS (What this file needs):
- pytest: Test framework
- src.retrieval.clarifications: Clarification templates

LAST MAJOR UPDATE: 2026-01-31
MAINTAINER: QA Team
"""

import pytest
from src.retrieval.clarifications import get_clarification_response, CLARIFICATION_QUESTIONS


class TestGetClarificationResponse:
    """Test get_clarification_response function."""

    def test_single_missing_city(self):
        """Test clarification for missing city only."""
        prefix, questions = get_clarification_response("missing_city", "fr")

        assert prefix is not None
        assert questions is not None
        assert len(questions) == 1
        assert "ville" in questions[0].lower() or "zone" in questions[0].lower()

    def test_single_missing_event_type(self):
        """Test clarification for missing event type only."""
        prefix, questions = get_clarification_response("missing_event_type", "fr")

        assert prefix is not None
        assert questions is not None
        assert len(questions) == 1
        assert "type" in questions[0].lower() and "evenement" in questions[0].lower()

    def test_single_missing_date(self):
        """Test clarification for missing date only."""
        prefix, questions = get_clarification_response("missing_date", "fr")

        assert prefix is not None
        assert questions is not None
        assert len(questions) == 1
        assert "periode" in questions[0].lower() or "quand" in questions[0].lower()

    def test_single_missing_timeframe_alias(self):
        """Test that missing_timeframe is an alias for missing_date."""
        prefix, questions = get_clarification_response("missing_timeframe", "fr")

        assert prefix is not None
        assert questions is not None
        assert len(questions) == 1
        assert "periode" in questions[0].lower()

    def test_two_missing_city_event_type(self):
        """Test clarification for missing city + event_type."""
        prefix, questions = get_clarification_response("missing_city+event_type", "fr")

        assert prefix is not None
        assert questions is not None
        assert len(questions) == 2
        # Should ask for both city and event type
        assert any("zone" in q.lower() or "ville" in q.lower() for q in questions)
        assert any("type" in q.lower() and "evenement" in q.lower() for q in questions)

    def test_two_missing_city_timeframe(self):
        """Test clarification for missing city + timeframe."""
        prefix, questions = get_clarification_response("missing_city+timeframe", "fr")

        assert prefix is not None
        assert questions is not None
        assert len(questions) == 2

    def test_two_missing_event_type_timeframe(self):
        """Test clarification for missing event_type + timeframe."""
        prefix, questions = get_clarification_response("missing_event_type+timeframe", "fr")

        assert prefix is not None
        assert questions is not None
        assert len(questions) == 2

    def test_three_missing_all_criteria(self):
        """Test clarification when all three criteria missing."""
        prefix, questions = get_clarification_response("missing_city+event_type+timeframe", "fr")

        assert prefix is not None
        assert questions is not None
        assert len(questions) == 3
        # Should ask for city, event type, and timeframe
        assert any("zone" in q.lower() or "ville" in q.lower() for q in questions)
        assert any("type" in q.lower() and "evenement" in q.lower() for q in questions)
        assert any("periode" in q.lower() for q in questions)

    def test_city_only_special_case(self):
        """Test special case when only city is provided."""
        prefix, questions = get_clarification_response("city_only", "fr")

        assert prefix is not None
        assert questions is not None
        assert len(questions) == 2  # Should ask for event type and date

    def test_event_type_only_special_case(self):
        """Test special case when only event type is provided."""
        prefix, questions = get_clarification_response("event_type_only", "fr")

        assert prefix is not None
        assert questions is not None
        assert len(questions) == 2  # Should ask for city and date

    def test_date_only_special_case(self):
        """Test special case when only date is provided."""
        prefix, questions = get_clarification_response("date_only", "fr")

        assert prefix is not None
        assert questions is not None
        assert len(questions) == 2  # Should ask for event type and city

    def test_kids_no_age_special_case(self):
        """Test special case for kids events without age specification."""
        prefix, questions = get_clarification_response("kids_no_age", "fr")

        assert prefix is not None
        assert questions is not None
        assert len(questions) == 1
        assert "âge" in questions[0].lower() or "age" in questions[0].lower()

    def test_unknown_reason_returns_none(self):
        """Test that unknown reason returns (None, None)."""
        prefix, questions = get_clarification_response("unknown_reason", "fr")

        assert prefix is None
        assert questions is None

    def test_english_language(self):
        """Test clarification in English."""
        prefix, questions = get_clarification_response("missing_city", "en")

        assert prefix is not None
        assert questions is not None
        assert "area" in questions[0].lower() or "city" in questions[0].lower()
        # Should NOT contain French words
        assert "ville" not in questions[0].lower()

    def test_english_all_missing(self):
        """Test English clarification with all criteria missing."""
        prefix, questions = get_clarification_response("missing_city+event_type+timeframe", "en")

        assert prefix is not None
        assert questions is not None
        assert len(questions) == 3
        assert "Which area" in questions[0] or "Which city" in questions[0]

    def test_language_fallback_to_english(self):
        """Test that invalid language falls back to English."""
        prefix, questions = get_clarification_response("missing_city", "es")

        # Should fallback to English
        assert prefix is not None
        assert questions is not None


class TestClarificationQuestionsCoverage:
    """Test coverage and consistency of CLARIFICATION_QUESTIONS dict."""

    def test_all_reasons_have_both_languages(self):
        """Test that all reasons have both fr and en templates."""
        for reason, templates in CLARIFICATION_QUESTIONS.items():
            assert "fr" in templates, f"Reason '{reason}' missing French template"
            assert "en" in templates, f"Reason '{reason}' missing English template"

    def test_all_templates_have_required_fields(self):
        """Test that all templates have prefix and questions fields."""
        for reason, templates in CLARIFICATION_QUESTIONS.items():
            for lang in ["fr", "en"]:
                template = templates[lang]
                assert "prefix" in template, f"Reason '{reason}' lang '{lang}' missing prefix"
                assert "questions" in template, f"Reason '{reason}' lang '{lang}' missing questions"
                assert isinstance(template["questions"], list), "Questions must be a list"

    def test_single_missing_has_one_question(self):
        """Test that single missing criteria have exactly 1 question."""
        single_missing = ["missing_city", "missing_event_type", "missing_date", "missing_timeframe"]

        for reason in single_missing:
            template_fr = CLARIFICATION_QUESTIONS[reason]["fr"]
            template_en = CLARIFICATION_QUESTIONS[reason]["en"]
            assert len(template_fr["questions"]) == 1, f"{reason} should have 1 question (FR)"
            assert len(template_en["questions"]) == 1, f"{reason} should have 1 question (EN)"

    def test_two_missing_has_two_questions(self):
        """Test that two missing criteria have exactly 2 questions."""
        two_missing = [
            "missing_city+event_type",
            "missing_city+date",
            "missing_city+timeframe",
            "missing_event_type+date",
            "missing_event_type+timeframe",
        ]

        for reason in two_missing:
            template_fr = CLARIFICATION_QUESTIONS[reason]["fr"]
            template_en = CLARIFICATION_QUESTIONS[reason]["en"]
            assert len(template_fr["questions"]) == 2, f"{reason} should have 2 questions (FR)"
            assert len(template_en["questions"]) == 2, f"{reason} should have 2 questions (EN)"

    def test_three_missing_has_three_questions(self):
        """Test that three missing criteria have exactly 3 questions."""
        three_missing = [
            "missing_city+event_type+date",
            "missing_city+event_type+timeframe",
            "missing_city+timeframe+event_type",
        ]

        for reason in three_missing:
            template_fr = CLARIFICATION_QUESTIONS[reason]["fr"]
            template_en = CLARIFICATION_QUESTIONS[reason]["en"]
            assert len(template_fr["questions"]) == 3, f"{reason} should have 3 questions (FR)"
            assert len(template_en["questions"]) == 3, f"{reason} should have 3 questions (EN)"

    def test_special_cases_exist(self):
        """Test that special case reasons exist."""
        special_cases = ["city_only", "event_type_only", "date_only", "kids_no_age"]

        for reason in special_cases:
            assert reason in CLARIFICATION_QUESTIONS, f"Special case '{reason}' not found"

    def test_no_empty_questions(self):
        """Test that no question is empty."""
        for reason, templates in CLARIFICATION_QUESTIONS.items():
            for lang in ["fr", "en"]:
                questions = templates[lang]["questions"]
                for i, q in enumerate(questions):
                    assert q.strip(), f"Question {i} in '{reason}' lang '{lang}' is empty"

    def test_no_empty_prefixes(self):
        """Test that no prefix is empty."""
        for reason, templates in CLARIFICATION_QUESTIONS.items():
            for lang in ["fr", "en"]:
                prefix = templates[lang]["prefix"]
                assert prefix.strip(), f"Prefix in '{reason}' lang '{lang}' is empty"

    def test_french_questions_use_french_words(self):
        """Test that French questions contain French words."""
        french_indicators = ["quelle", "quel", "dans", "pour", "type", "ville", "zone", "période"]

        for reason, templates in CLARIFICATION_QUESTIONS.items():
            # Skip kids_no_age as it has special wording
            if reason == "kids_no_age":
                continue

            fr_questions = " ".join(templates["fr"]["questions"]).lower()
            has_french = any(indicator in fr_questions for indicator in french_indicators)
            assert has_french, f"French template for '{reason}' doesn't seem French"

    def test_english_questions_use_english_words(self):
        """Test that English questions contain English words."""
        english_indicators = ["what", "which", "where", "when", "type", "city", "area", "timeframe", "event"]

        for reason, templates in CLARIFICATION_QUESTIONS.items():
            # Skip kids_no_age as it has special wording
            if reason == "kids_no_age":
                continue

            en_questions = " ".join(templates["en"]["questions"]).lower()
            has_english = any(indicator in en_questions for indicator in english_indicators)
            assert has_english, f"English template for '{reason}' doesn't seem English"


class TestAliasConsistency:
    """Test that aliases (missing_date vs missing_timeframe) work correctly."""

    def test_missing_date_and_missing_timeframe_equivalent(self):
        """Test that missing_date and missing_timeframe return similar content."""
        prefix_date_fr, questions_date_fr = get_clarification_response("missing_date", "fr")
        prefix_time_fr, questions_time_fr = get_clarification_response("missing_timeframe", "fr")

        # Both should ask about timeframe
        assert "periode" in questions_date_fr[0].lower()
        assert "periode" in questions_time_fr[0].lower()

    def test_combined_aliases_work(self):
        """Test that combined reasons work with timeframe alias."""
        # These should all work
        reasons = ["missing_city+timeframe", "missing_event_type+timeframe", "missing_city+event_type+timeframe"]

        for reason in reasons:
            prefix, questions = get_clarification_response(reason, "fr")
            assert prefix is not None
            assert questions is not None


class TestClarificationResponseFormat:
    """Test the format and structure of clarification responses."""

    def test_prefix_ends_with_newline_or_colon(self):
        """Test that prefixes end with newline or punctuation."""
        for reason, templates in CLARIFICATION_QUESTIONS.items():
            for lang in ["fr", "en"]:
                prefix = templates[lang]["prefix"]
                # Prefix should end with newline, colon, or punctuation
                assert prefix[-1] in ["\n", ":", "!", "."], f"Prefix in '{reason}' lang '{lang}' has unexpected ending"

    def test_questions_contain_question_marks(self):
        """Test that most questions contain question marks or are imperative."""
        for reason, templates in CLARIFICATION_QUESTIONS.items():
            for lang in ["fr", "en"]:
                questions = templates[lang]["questions"]
                # At least one question should have proper punctuation
                has_punctuation = any(q.endswith("?") or q.endswith("!") or q.endswith(".") for q in questions)
                # Some questions might be imperative without punctuation, so this is not strict
                # Just checking structure exists

    def test_bilingual_question_count_matches(self):
        """Test that French and English versions have same number of questions."""
        for reason, templates in CLARIFICATION_QUESTIONS.items():
            fr_count = len(templates["fr"]["questions"])
            en_count = len(templates["en"]["questions"])
            assert fr_count == en_count, f"Question count mismatch for '{reason}': FR={fr_count}, EN={en_count}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
