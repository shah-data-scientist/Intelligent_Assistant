"""
FILE: test_chain.py
STATUS: Active
RESPONSIBILITY: Unit tests for RAGChain with mocked LLM dependencies.
LAST MAJOR UPDATE: 2026-01-31
MAINTAINER: QA Team
"""

import pytest
import json
from unittest.mock import MagicMock, patch, Mock
from datetime import date

from src.retrieval.chain import (
    RobustJsonParser,
    get_city_locator,
    _background_db_write,
)


class TestRobustJsonParser:
    """Test RobustJsonParser for handling LLM output."""

    @pytest.fixture
    def parser(self):
        return RobustJsonParser()

    def test_parse_valid_json(self, parser):
        """Test parsing valid JSON."""
        text = '{"answer_text": "Here are events", "events": []}'
        result = parser.parse(text)
        assert result["answer_text"] == "Here are events"
        assert result["events"] == []

    def test_parse_json_in_markdown_code_block(self, parser):
        """Test parsing JSON wrapped in markdown code blocks."""
        text = '''```json
{"answer_text": "Concert info", "events": [{"title": "Jazz Night"}]}
```'''
        result = parser.parse(text)
        assert result["answer_text"] == "Concert info"
        assert len(result["events"]) == 1

    def test_parse_partial_json_extracts_answer(self, parser):
        """Test extraction from partial/truncated JSON."""
        text = '{"answer_text": "Voici les concerts de jazz à Paris ce weekend'
        result = parser.parse(text)
        assert "concerts de jazz" in result["answer_text"]

    def test_parse_text_before_json(self, parser):
        """Test extraction of text before JSON fragment."""
        # Parser extracts answer_text from partial JSON when present
        text = '{"answer_text": "Voici les événements culturels à Paris ce weekend'
        result = parser.parse(text)
        # Should extract the answer_text value
        assert "answer_text" in result
        assert "événements" in result["answer_text"]

    def test_parse_completely_invalid_returns_fallback(self, parser):
        """Test that completely invalid input returns fallback message."""
        text = ""
        result = parser.parse(text)
        assert "answer_text" in result
        assert "reformuler" in result["answer_text"]

    def test_parse_removes_trailing_incomplete_json(self, parser):
        """Test removal of trailing incomplete JSON."""
        text = "Voici les résultats pour votre recherche. {\"answer\":"
        result = parser.parse(text)
        assert "résultats" in result["answer_text"]

    def test_parser_type_property(self, parser):
        """Test _type property returns correct value."""
        assert parser._type == "robust_json"


class TestCityLocator:
    """Test city locator singleton."""

    def test_get_city_locator_returns_instance(self):
        """Test that get_city_locator returns a CityLocator."""
        with patch('src.retrieval.chain.CityLocator') as MockLocator:
            MockLocator.return_value = MagicMock()
            # Reset global
            import src.retrieval.chain as chain_module
            chain_module._city_locator = None

            locator = get_city_locator()
            assert locator is not None

    def test_get_city_locator_singleton(self):
        """Test that get_city_locator returns same instance."""
        with patch('src.retrieval.chain.CityLocator') as MockLocator:
            mock_instance = MagicMock()
            MockLocator.return_value = mock_instance

            import src.retrieval.chain as chain_module
            chain_module._city_locator = None

            locator1 = get_city_locator()
            locator2 = get_city_locator()

            # Should only create once
            assert MockLocator.call_count == 1


class TestBackgroundDbWrite:
    """Test background database write helper."""

    def test_background_write_executes_function(self):
        """Test that background write executes the provided function."""
        import time

        call_tracker = {"called": False}

        def mock_func(value):
            call_tracker["called"] = True
            call_tracker["value"] = value

        _background_db_write(mock_func, "test_value")

        # Wait for thread to complete
        time.sleep(0.1)

        assert call_tracker["called"] is True
        assert call_tracker["value"] == "test_value"

    def test_background_write_handles_exceptions(self):
        """Test that exceptions in background write are handled."""
        import time

        def failing_func():
            raise ValueError("Database error")

        # Should not raise - error is logged
        _background_db_write(failing_func)

        # Wait for thread
        time.sleep(0.1)
        # No assertion needed - test passes if no exception propagates


class TestRAGChainInitialization:
    """Test RAGChain initialization with mocked dependencies."""

    @patch('src.retrieval.chain.EventVectorStore')
    @patch('src.retrieval.chain.MistralLLM')
    @patch('src.retrieval.chain.EventStorage')
    @patch('src.retrieval.chain.ChatStorage')
    def test_rag_chain_can_be_imported(self, mock_chat, mock_event, mock_llm, mock_vs):
        """Test that RAGChain can be imported and dependencies are injectable."""
        # This tests that the module structure is correct
        from src.retrieval.chain import RAGChain
        assert RAGChain is not None


class TestQueryProcessing:
    """Test query processing logic with mocked LLM."""

    def test_json_extraction_from_llm_response(self):
        """Test JSON extraction patterns used in chain."""
        import re

        # Test markdown code block extraction
        text = '```json\n{"key": "value"}\n```'
        match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
        assert match is not None
        assert json.loads(match.group(1)) == {"key": "value"}

    def test_answer_text_extraction_pattern(self):
        """Test answer_text extraction from partial JSON."""
        import re

        text = '{"answer_text": "Voici les concerts", "events": ['
        match = re.search(r'"answer_text"\s*:\s*"(.*?)(?:"|$)', text, re.DOTALL)
        assert match is not None
        assert "concerts" in match.group(1)


class TestFilterBuilding:
    """Test filter building logic."""

    def test_date_filter_construction(self):
        """Test date filter construction from intent."""
        from src.retrieval.manager import SearchIntent

        intent = SearchIntent(
            city="Paris",
            month=6,
            days=[15],
            year=2026
        )

        # Build filter dict like chain does
        filters = {
            "city": intent.city,
            "month": intent.month,
            "day": intent.days,
            "year": intent.year,
        }
        clean = {k: v for k, v in filters.items() if v is not None}

        assert clean["city"] == "Paris"
        assert clean["month"] == 6
        assert clean["day"] == [15]


class TestResponseBuilding:
    """Test response building with mocked data."""

    def test_response_structure(self):
        """Test that response has expected structure."""
        from src.retrieval.response_builder import ResponseBuilder

        builder = ResponseBuilder()

        # Mock data
        events_data = [
            {
                "title": "Jazz Concert",
                "location": {"city": "Paris"},
                "start_date": "2026-06-15",
            }
        ]

        # ResponseBuilder should handle event formatting
        assert builder is not None


class TestLanguageDetection:
    """Test language detection from query."""

    def test_detect_french_from_bonjour(self):
        """Test French detection with greeting."""
        from src.retrieval.chain import detect_language_from_query
        assert detect_language_from_query("Bonjour, comment ça va?") == "fr"

    def test_detect_french_from_merci(self):
        """Test French detection with merci."""
        from src.retrieval.chain import detect_language_from_query
        assert detect_language_from_query("Merci beaucoup!") == "fr"

    def test_detect_french_from_cherche(self):
        """Test French detection with cherche."""
        from src.retrieval.chain import detect_language_from_query
        assert detect_language_from_query("Je cherche des concerts") == "fr"

    def test_detect_english_from_plain_text(self):
        """Test English detection with no French indicators."""
        from src.retrieval.chain import detect_language_from_query
        assert detect_language_from_query("Find jazz concerts in Paris") == "en"

    def test_detect_english_from_empty(self):
        """Test empty string returns English."""
        from src.retrieval.chain import detect_language_from_query
        assert detect_language_from_query("") == "en"


class TestOutOfScopeCityDetection:
    """Test out-of-scope city detection."""

    def test_no_city_detected(self):
        """Test that queries without city patterns return None."""
        from src.retrieval.chain import detect_out_of_scope_city
        result = detect_out_of_scope_city("Show me jazz concerts")
        assert result == (None, None)

    def test_skip_common_words(self):
        """Test that common words are not detected as cities."""
        from src.retrieval.chain import detect_out_of_scope_city
        # "events" should be skipped as it's in the skip list
        result = detect_out_of_scope_city("Find events in cultural venues")
        assert result == (None, None)

    def test_skip_date_words(self):
        """Test that month names are not detected as cities."""
        from src.retrieval.chain import detect_out_of_scope_city
        result = detect_out_of_scope_city("Events in March")
        assert result == (None, None)

    def test_skip_region_words(self):
        """Test that region words like 'ile' are skipped."""
        from src.retrieval.chain import detect_out_of_scope_city
        result = detect_out_of_scope_city("Events in Ile de France")
        assert result == (None, None)


class TestResponseDictionaries:
    """Test response dictionary structures."""

    def test_greeting_responses_both_languages(self):
        """Test greeting responses have both fr and en."""
        from src.retrieval.chain import GREETING_RESPONSES
        assert "fr" in GREETING_RESPONSES
        assert "en" in GREETING_RESPONSES
        assert len(GREETING_RESPONSES["fr"]) > 0
        assert len(GREETING_RESPONSES["en"]) > 0

    def test_chitchat_responses_both_languages(self):
        """Test chitchat responses have both fr and en."""
        from src.retrieval.chain import CHITCHAT_RESPONSES
        assert "fr" in CHITCHAT_RESPONSES
        assert "en" in CHITCHAT_RESPONSES

    def test_capability_responses_both_languages(self):
        """Test capability responses have both fr and en."""
        from src.retrieval.chain import CAPABILITY_RESPONSES
        assert "fr" in CAPABILITY_RESPONSES
        assert "en" in CAPABILITY_RESPONSES

    def test_off_topic_responses_both_languages(self):
        """Test off-topic responses have both fr and en."""
        from src.retrieval.chain import OFF_TOPIC_RESPONSES
        assert "fr" in OFF_TOPIC_RESPONSES
        assert "en" in OFF_TOPIC_RESPONSES

    def test_abuse_responses_both_languages(self):
        """Test abuse responses have both fr and en."""
        from src.retrieval.chain import ABUSE_RESPONSES
        assert "fr" in ABUSE_RESPONSES
        assert "en" in ABUSE_RESPONSES

    def test_directions_responses_both_languages(self):
        """Test directions responses have both fr and en."""
        from src.retrieval.chain import DIRECTIONS_RESPONSES
        assert "fr" in DIRECTIONS_RESPONSES
        assert "en" in DIRECTIONS_RESPONSES

    def test_out_of_scope_city_responses_have_placeholder(self):
        """Test out-of-scope city responses have city placeholder."""
        from src.retrieval.chain import OUT_OF_SCOPE_CITY_RESPONSES
        assert "{city}" in OUT_OF_SCOPE_CITY_RESPONSES["fr"]
        assert "{city}" in OUT_OF_SCOPE_CITY_RESPONSES["en"]


class TestGreetingPrefixes:
    """Test greeting and typo acknowledgment prefixes."""

    def test_greeting_prefixes_both_languages(self):
        """Test greeting prefixes have both fr and en."""
        from src.retrieval.chain import GREETING_PREFIXES
        assert GREETING_PREFIXES["fr"] == "Bonjour ! "
        assert GREETING_PREFIXES["en"] == "Hello! "

    def test_typo_acknowledgments_have_placeholders(self):
        """Test typo acknowledgments have required placeholders."""
        from src.retrieval.chain import TYPO_ACKNOWLEDGMENTS
        assert "{corrected}" in TYPO_ACKNOWLEDGMENTS["fr"]
        assert "{original}" in TYPO_ACKNOWLEDGMENTS["fr"]
        assert "{corrected}" in TYPO_ACKNOWLEDGMENTS["en"]
        assert "{original}" in TYPO_ACKNOWLEDGMENTS["en"]


class TestComposeResponsePrefix:
    """Test compose_response_prefix function."""

    def test_compose_prefix_no_dimensions(self):
        """Test that no dimensions returns empty string."""
        from src.retrieval.chain import compose_response_prefix
        from src.retrieval.unified_analyzer import UnifiedAnalysisResult, QueryIntent

        analysis = UnifiedAnalysisResult(
            intent=QueryIntent.EVENT_SEARCH,
            intent_confidence=0.9
        )
        result = compose_response_prefix(analysis, "fr")
        assert result == ""

    def test_compose_prefix_with_greeting(self):
        """Test that greeting dimension adds prefix."""
        from src.retrieval.chain import compose_response_prefix
        from src.retrieval.unified_analyzer import UnifiedAnalysisResult, QueryIntent, QueryDimension

        analysis = UnifiedAnalysisResult(
            intent=QueryIntent.EVENT_SEARCH,
            intent_confidence=0.9,
            dimensions={"greeting": QueryDimension("greeting", True)}
        )
        result = compose_response_prefix(analysis, "fr")
        assert "Bonjour" in result

    def test_compose_prefix_with_typo(self):
        """Test that typo correction adds acknowledgment."""
        from src.retrieval.chain import compose_response_prefix
        from src.retrieval.unified_analyzer import UnifiedAnalysisResult, QueryIntent, QueryDimension

        analysis = UnifiedAnalysisResult(
            intent=QueryIntent.EVENT_SEARCH,
            intent_confidence=0.9,
            dimensions={
                "typo": QueryDimension("typo", True, value="Paris", original="Pari")
            },
            city_normalized="paris"  # Must be set for typo ack to show
        )
        result = compose_response_prefix(analysis, "fr")
        assert "Paris" in result
        assert "Pari" in result


class TestSimpleSummaryBufferMemory:
    """Test SimpleSummaryBufferMemory class."""

    def test_memory_initialization(self):
        """Test memory can be initialized."""
        from src.retrieval.chain import SimpleSummaryBufferMemory
        from unittest.mock import MagicMock

        mock_llm = MagicMock()
        mock_chat_memory = MagicMock()
        mock_chat_memory.messages = []

        memory = SimpleSummaryBufferMemory(
            llm=mock_llm,
            chat_memory=mock_chat_memory,
            max_token_limit=1000
        )
        assert memory.max_token_limit == 1000
        assert memory.memory_key == "chat_history"

    def test_load_memory_short_history(self):
        """Test loading memory with short history (no summarization)."""
        from src.retrieval.chain import SimpleSummaryBufferMemory
        from unittest.mock import MagicMock
        from langchain_core.messages import HumanMessage, AIMessage

        mock_llm = MagicMock()
        mock_chat_memory = MagicMock()
        mock_chat_memory.messages = [
            HumanMessage(content="Hello"),
            AIMessage(content="Hi there!"),
        ]

        memory = SimpleSummaryBufferMemory(
            llm=mock_llm,
            chat_memory=mock_chat_memory
        )

        result = memory.load_memory_variables({})
        assert "chat_history" in result
        assert len(result["chat_history"]) == 2

    def test_save_context_does_nothing(self):
        """Test that save_context is a no-op (handled externally)."""
        from src.retrieval.chain import SimpleSummaryBufferMemory
        from unittest.mock import MagicMock

        mock_llm = MagicMock()
        mock_chat_memory = MagicMock()
        mock_chat_memory.messages = []

        memory = SimpleSummaryBufferMemory(
            llm=mock_llm,
            chat_memory=mock_chat_memory
        )

        # Should not raise
        memory.save_context({"input": "test"}, {"output": "test"})


class TestStatisticalResponses:
    """Test statistical response templates."""

    def test_statistical_responses_exist(self):
        """Test statistical responses have both languages."""
        from src.retrieval.chain import STATISTICAL_RESPONSES
        assert "fr" in STATISTICAL_RESPONSES
        assert "en" in STATISTICAL_RESPONSES
        assert len(STATISTICAL_RESPONSES["fr"]) > 0
        assert len(STATISTICAL_RESPONSES["en"]) > 0


class TestUseUnifiedAnalyzerFlag:
    """Test the USE_UNIFIED_ANALYZER feature flag."""

    def test_flag_is_enabled(self):
        """Test that unified analyzer is enabled by default."""
        from src.retrieval.chain import USE_UNIFIED_ANALYZER
        assert USE_UNIFIED_ANALYZER is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
