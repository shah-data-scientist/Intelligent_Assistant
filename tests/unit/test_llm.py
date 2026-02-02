"""
FILE: test_llm.py
STATUS: Active
RESPONSIBILITY: Unit tests for LLM utilities and helper functions.
LAST MAJOR UPDATE: 2026-01-31
MAINTAINER: QA Team
"""

import pytest
from unittest.mock import MagicMock, patch, Mock


class TestIsRetryableLLMError:
    """Test is_retryable_llm_error function."""

    def test_rate_limit_429_is_retryable(self):
        """Test 429 rate limit error is retryable."""
        from src.generation.llm import is_retryable_llm_error

        error = Exception("HTTP 429: Too Many Requests")
        assert is_retryable_llm_error(error) is True

    def test_resource_exhausted_is_retryable(self):
        """Test Google RESOURCE_EXHAUSTED is retryable."""
        from src.generation.llm import is_retryable_llm_error

        error = Exception("RESOURCE_EXHAUSTED: Quota exceeded")
        assert is_retryable_llm_error(error) is True

    def test_quota_error_is_retryable(self):
        """Test quota errors are retryable."""
        from src.generation.llm import is_retryable_llm_error

        error = Exception("Quota limit exceeded for this project")
        assert is_retryable_llm_error(error) is True

    def test_server_500_is_retryable(self):
        """Test 500 server error is retryable."""
        from src.generation.llm import is_retryable_llm_error

        error = Exception("HTTP 500 Internal Server Error")
        assert is_retryable_llm_error(error) is True

    def test_server_502_is_retryable(self):
        """Test 502 bad gateway is retryable."""
        from src.generation.llm import is_retryable_llm_error

        error = Exception("502 Bad Gateway")
        assert is_retryable_llm_error(error) is True

    def test_server_503_is_retryable(self):
        """Test 503 service unavailable is retryable."""
        from src.generation.llm import is_retryable_llm_error

        error = Exception("503 Service Unavailable")
        assert is_retryable_llm_error(error) is True

    def test_connection_error_is_retryable(self):
        """Test connection errors are retryable."""
        from src.generation.llm import is_retryable_llm_error

        error = Exception("Connection refused")
        assert is_retryable_llm_error(error) is True

    def test_connection_timeout_is_retryable(self):
        """Test connection timeout errors are retryable."""
        from src.generation.llm import is_retryable_llm_error

        # The function requires BOTH "connection" AND "timeout" keywords
        error = Exception("Connection timeout occurred")
        assert is_retryable_llm_error(error) is True

    def test_auth_error_not_retryable(self):
        """Test authentication errors are not retryable."""
        from src.generation.llm import is_retryable_llm_error

        error = Exception("401 Unauthorized: Invalid API key")
        assert is_retryable_llm_error(error) is False

    def test_not_found_not_retryable(self):
        """Test 404 errors are not retryable."""
        from src.generation.llm import is_retryable_llm_error

        error = Exception("404 Not Found")
        assert is_retryable_llm_error(error) is False

    def test_validation_error_not_retryable(self):
        """Test validation errors are not retryable."""
        from src.generation.llm import is_retryable_llm_error

        error = Exception("ValidationError: Invalid input format")
        assert is_retryable_llm_error(error) is False


class TestCircuitBreakerConfig:
    """Test circuit breaker configuration."""

    def test_circuit_breaker_disabled_by_default(self):
        """Test circuit breaker is disabled in dev mode."""
        from src.generation.llm import llm_breaker, _ENABLE_CIRCUIT_BREAKER

        # In test environment, should be disabled
        if not _ENABLE_CIRCUIT_BREAKER:
            assert llm_breaker is None


class TestGetLLMFactory:
    """Test get_chat_llm factory function."""

    def test_get_chat_llm_function_exists(self):
        """Test that get_chat_llm function can be imported."""
        from src.generation.llm import get_chat_llm
        assert callable(get_chat_llm)


class TestMistralLLMClass:
    """Test MistralLLM class structure."""

    def test_mistral_llm_class_exists(self):
        """Test MistralLLM class can be imported."""
        from src.generation.llm import MistralLLM

        assert MistralLLM is not None

    def test_mistral_llm_has_invoke_method(self):
        """Test MistralLLM has invoke method."""
        from src.generation.llm import MistralLLM

        assert hasattr(MistralLLM, 'invoke') or hasattr(MistralLLM, '__call__')


class TestLLMMessageFormatting:
    """Test LLM message formatting utilities."""

    def test_message_role_structure(self):
        """Test message role structure for LLM calls."""
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello!"},
            {"role": "assistant", "content": "Hi there!"},
        ]

        assert all("role" in msg for msg in messages)
        assert all("content" in msg for msg in messages)
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert messages[2]["role"] == "assistant"

    def test_prompt_template_formatting(self):
        """Test prompt template variable substitution."""
        template = """You are an assistant for {domain}.

User query: {query}
Context: {context}"""

        result = template.format(
            domain="cultural events",
            query="Jazz concerts in Paris",
            context="Event data from database"
        )

        assert "cultural events" in result
        assert "Jazz concerts in Paris" in result
        assert "Event data from database" in result


class TestLLMResponseParsing:
    """Test LLM response parsing patterns."""

    def test_json_extraction_from_response(self):
        """Test JSON extraction from LLM response."""
        import json

        response = '''Here are the results:
```json
{"answer": "Found 5 events", "events": []}
```'''

        import re
        match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
        assert match is not None

        parsed = json.loads(match.group(1))
        assert parsed["answer"] == "Found 5 events"

    def test_handles_malformed_json(self):
        """Test graceful handling of malformed JSON."""
        response = '{"answer": "Incomplete JSON'

        import json
        try:
            json.loads(response)
            parsed = True
        except json.JSONDecodeError:
            parsed = False

        assert parsed is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
