"""Integration tests for LLM-as-a-Judge generation metrics.

These tests use real LLM calls to validate faithfulness and relevancy scoring.
"""

import pytest
from src.evaluation.metrics.generation import LLMAsJudge


@pytest.mark.integration
@pytest.mark.evaluation
class TestFaithfulnessJudge:
    """Test faithfulness evaluation with synthetic examples."""

    @pytest.fixture
    def judge(self):
        """Create LLMAsJudge instance."""
        return LLMAsJudge()

    def test_faithfulness_perfect_grounding(self, judge):
        """Test that perfectly grounded answers score highly."""
        query = "What jazz concerts are available in Paris?"
        sources = [
            "Title: Jazz Night\nCity: Paris\nDate: 15/02/2026\nDescription: Jazz concert"
        ]
        answer = "There is a Jazz Night concert in Paris on 15/02/2026."

        result = judge.evaluate_faithfulness(query, answer, sources)

        assert "score" in result
        assert result["score"] >= 0.8, f"Expected high score for grounded answer, got {result['score']}"
        assert "reasoning" in result
        assert isinstance(result["violations"], list)
        assert len(result["violations"]) == 0, f"Expected no violations, found: {result['violations']}"

    def test_faithfulness_hallucination_detection(self, judge):
        """Test that hallucinated information is detected."""
        query = "What jazz concerts are available?"
        sources = [
            "Title: Jazz Night\nCity: Paris\nDate: 15/02/2026"
        ]
        # Hallucinated: "romantic", "perfect for couples", "€15"
        answer = "There is a romantic Jazz Night concert perfect for couples in Paris for €15."

        result = judge.evaluate_faithfulness(query, answer, sources)

        assert "score" in result
        assert result["score"] < 0.7, f"Expected low score for hallucinated answer, got {result['score']}"
        assert isinstance(result["violations"], list)
        # Should detect at least one violation
        assert len(result["violations"]) > 0, "Expected to detect hallucinations"

    def test_faithfulness_partial_grounding(self, judge):
        """Test answers that are partially grounded."""
        query = "What concerts are available?"
        sources = [
            "Title: Jazz Night\nCity: Paris\nDate: 15/02/2026",
            "Title: Rock Festival\nCity: Lyon\nDate: 20/02/2026"
        ]
        # Correctly mentions Jazz Night, but adds unsupported claim about tickets
        answer = "Jazz Night is in Paris on 15/02/2026. Tickets are selling fast."

        result = judge.evaluate_faithfulness(query, answer, sources)

        assert "score" in result
        # Should be moderate score (some grounding, some hallucination)
        assert 0.4 <= result["score"] <= 0.9

    def test_faithfulness_multiple_sources(self, judge):
        """Test faithfulness with multiple sources."""
        query = "What events are happening?"
        sources = [
            "Title: Jazz Night\nCity: Paris",
            "Title: Art Exhibition\nCity: Lyon",
            "Title: Theater Play\nCity: Marseille"
        ]
        answer = "There are three events: Jazz Night in Paris, Art Exhibition in Lyon, and Theater Play in Marseille."

        result = judge.evaluate_faithfulness(query, answer, sources)

        assert result["score"] >= 0.8, "Should score high for well-grounded multi-source answer"
        assert len(result["violations"]) == 0

    def test_faithfulness_empty_sources(self, judge):
        """Test handling of empty sources."""
        query = "What events?"
        sources = []
        answer = "There are no events available."

        result = judge.evaluate_faithfulness(query, answer, sources)

        assert "score" in result
        assert 0.0 <= result["score"] <= 1.0
        assert isinstance(result["violations"], list)


@pytest.mark.integration
@pytest.mark.evaluation
class TestRelevancyJudge:
    """Test relevancy evaluation with synthetic examples."""

    @pytest.fixture
    def judge(self):
        """Create LLMAsJudge instance."""
        return LLMAsJudge()

    def test_relevancy_direct_answer(self, judge):
        """Test that direct answers score highly."""
        query = "Show me jazz concerts in Paris"
        answer = "Here are jazz concerts in Paris: Jazz Night on 15/02/2026 at Olympia Hall."

        result = judge.evaluate_relevancy(query, answer)

        assert "score" in result
        assert result["score"] >= 0.7, f"Expected high score for relevant answer, got {result['score']}"
        assert "reasoning" in result
        assert isinstance(result["strengths"], list)
        assert isinstance(result["weaknesses"], list)

    def test_relevancy_off_topic_answer(self, judge):
        """Test that off-topic answers score poorly."""
        query = "What jazz concerts are available?"
        answer = "Paris is a beautiful city with many cultural attractions and museums."

        result = judge.evaluate_relevancy(query, answer)

        assert "score" in result
        assert result["score"] < 0.5, f"Expected low score for irrelevant answer, got {result['score']}"

    def test_relevancy_partial_answer(self, judge):
        """Test partially relevant answers."""
        query = "Tell me about jazz concerts in Paris in February"
        answer = "There are jazz concerts in Paris."  # Missing date information

        result = judge.evaluate_relevancy(query, answer)

        assert "score" in result
        # Should be moderate (addresses topic but missing details)
        assert 0.3 <= result["score"] <= 0.8

    def test_relevancy_clarification_needed(self, judge):
        """Test vague queries that need clarification."""
        query = "events"
        answer = "Could you please specify what type of events you're interested in? For example: concerts, exhibitions, theater, sports, etc."

        result = judge.evaluate_relevancy(query, answer)

        assert "score" in result
        # Asking for clarification is relevant to vague query
        assert result["score"] >= 0.6

    def test_relevancy_comprehensive_answer(self, judge):
        """Test comprehensive answers with details."""
        query = "What are the best jazz concerts this month?"
        answer = """Here are the top jazz concerts this month:

1. Jazz Night - Paris, 15/02/2026, featuring renowned artists
2. Blues & Jazz Festival - Lyon, 20/02/2026, three-day event
3. Smooth Jazz Evening - Marseille, 25/02/2026, intimate venue

Each event offers unique experiences and tickets are available online."""

        result = judge.evaluate_relevancy(query, answer)

        assert result["score"] >= 0.8, "Comprehensive answer should score highly"
        assert len(result["strengths"]) > 0, "Should identify strengths"


@pytest.mark.integration
@pytest.mark.evaluation
class TestLanguageConsistency:
    """Test language consistency detection."""

    @pytest.fixture
    def judge(self):
        """Create LLMAsJudge instance."""
        return LLMAsJudge()

    def test_language_french_consistent(self, judge):
        """Test French query with French answer."""
        query = "Quels sont les concerts de jazz à Paris?"
        answer = "Voici les concerts de jazz à Paris: Jazz Night le 15/02/2026."

        result = judge.evaluate_language_consistency(query, answer)

        assert result["query_language"] == "fr"
        assert result["answer_language"] == "fr"
        assert result["is_consistent"] is True
        assert result["score"] == 1.0

    def test_language_english_consistent(self, judge):
        """Test English query with English answer."""
        query = "What are the jazz concerts in Paris?"
        answer = "Here are the jazz concerts in Paris: Jazz Night on 15/02/2026."

        result = judge.evaluate_language_consistency(query, answer)

        assert result["query_language"] == "en"
        assert result["answer_language"] == "en"
        assert result["is_consistent"] is True
        assert result["score"] == 1.0

    def test_language_inconsistent(self, judge):
        """Test French query with English answer."""
        query = "Quels sont les concerts de jazz?"
        answer = "Here are the jazz concerts available."

        result = judge.evaluate_language_consistency(query, answer)

        assert result["is_consistent"] is False
        assert result["score"] == 0.0

    def test_language_mixed_query(self, judge):
        """Test handling of mixed-language queries."""
        query = "Show me les concerts de jazz"  # Mixed EN/FR
        answer = "Voici les concerts: Jazz Night"

        result = judge.evaluate_language_consistency(query, answer)

        # Should detect based on majority language markers
        assert result["query_language"] in ["fr", "en"]
        assert result["answer_language"] in ["fr", "en"]


@pytest.mark.integration
@pytest.mark.evaluation
class TestComprehensiveEvaluation:
    """Test comprehensive generation evaluation."""

    @pytest.fixture
    def judge(self):
        """Create LLMAsJudge instance."""
        return LLMAsJudge()

    def test_comprehensive_evaluation_all_metrics(self, judge):
        """Test that comprehensive evaluation returns all expected metrics."""
        query = "What jazz concerts are in Paris?"
        answer = "Jazz Night is in Paris on 15/02/2026 at Olympia Hall."
        sources = ["Title: Jazz Night\nCity: Paris\nDate: 15/02/2026\nVenue: Olympia Hall"]

        result = judge.evaluate_generation(query, answer, sources)

        # Check all expected keys are present
        assert "faithfulness_score" in result
        assert "relevancy_score" in result
        assert "language_consistent" in result
        assert "quality_score" in result
        assert "faithfulness_details" in result
        assert "relevancy_details" in result
        assert "language_details" in result

        # Check score ranges
        assert 0.0 <= result["faithfulness_score"] <= 1.0
        assert 0.0 <= result["relevancy_score"] <= 1.0
        assert 0.0 <= result["quality_score"] <= 1.0

        # Quality score should be average of faithfulness and relevancy
        expected_quality = (result["faithfulness_score"] + result["relevancy_score"]) / 2
        assert abs(result["quality_score"] - expected_quality) < 0.01

    def test_comprehensive_evaluation_high_quality(self, judge):
        """Test high-quality answer gets high scores."""
        query = "Show me jazz concerts in Paris"
        answer = "Here are jazz concerts in Paris: Jazz Night on 15/02/2026 at Olympia Hall."
        sources = ["Title: Jazz Night\nCity: Paris\nDate: 15/02/2026\nVenue: Olympia Hall"]

        result = judge.evaluate_generation(query, answer, sources)

        # High quality answer should score well
        assert result["quality_score"] >= 0.7, f"Expected high quality score, got {result['quality_score']}"

    def test_comprehensive_evaluation_low_quality(self, judge):
        """Test low-quality answer gets low scores."""
        query = "What concerts are available?"
        answer = "The weather is nice today."  # Completely irrelevant
        sources = ["Title: Jazz Night\nCity: Paris"]

        result = judge.evaluate_generation(query, answer, sources)

        # Low quality answer should score poorly
        assert result["relevancy_score"] < 0.5, "Irrelevant answer should have low relevancy"


@pytest.mark.evaluation
class TestJSONParsing:
    """Test JSON parsing robustness."""

    @pytest.fixture
    def judge(self):
        """Create LLMAsJudge instance."""
        return LLMAsJudge()

    def test_parse_clean_json(self, judge):
        """Test parsing clean JSON."""
        response = '{"score": 0.9, "reasoning": "Good", "violations": []}'
        result = judge._parse_json_response(response)

        assert result["score"] == 0.9
        assert result["reasoning"] == "Good"
        assert result["violations"] == []

    def test_parse_json_with_markdown(self, judge):
        """Test parsing JSON wrapped in markdown code blocks."""
        response = '```json\n{"score": 0.8, "reasoning": "OK"}\n```'
        result = judge._parse_json_response(response)

        assert result["score"] == 0.8
        assert result["reasoning"] == "OK"

    def test_parse_json_with_extra_backticks(self, judge):
        """Test parsing JSON with generic code blocks."""
        response = '```\n{"score": 0.7}\n```'
        result = judge._parse_json_response(response)

        assert result["score"] == 0.7

    def test_parse_json_with_whitespace(self, judge):
        """Test parsing JSON with extra whitespace."""
        response = '  \n  {"score": 0.6}  \n  '
        result = judge._parse_json_response(response)

        assert result["score"] == 0.6

    def test_parse_invalid_json(self, judge):
        """Test that invalid JSON raises ValueError."""
        response = "This is not JSON"

        with pytest.raises(ValueError, match="Invalid JSON"):
            judge._parse_json_response(response)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "evaluation"])
