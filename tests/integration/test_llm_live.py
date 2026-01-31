"""
FILE: test_llm_live.py
STATUS: Active
RESPONSIBILITY: Tests live Google Gemini LLM API integration, including response validation and error handling
LAST MAJOR UPDATE: 2026-01-31
MAINTAINER: QA Team

IMPORTANT: These tests make REAL API calls and incur costs.
They are skipped by default unless explicitly enabled via:
  RUN_LIVE_API_TESTS=1 pytest tests/integration/test_llm_live.py

Cost estimates per test run:
- Gemini LLM: ~$0.001 per test (flash model)
- Mistral Embeddings: ~$0.0001 per test
- Full test suite: ~$0.01-0.02 total
"""

import pytest
import os
from unittest.mock import patch

# Skip all tests in this file unless RUN_LIVE_API_TESTS=1 is set
pytestmark = pytest.mark.skipif(
    not os.environ.get("RUN_LIVE_API_TESTS"),
    reason="Live API tests disabled. Set RUN_LIVE_API_TESTS=1 to enable."
)


class TestGeminiLLMLive:
    """Integration tests for Google Gemini LLM (real API calls)."""

    def test_gemini_basic_response(self):
        """Test that Gemini returns a valid response for a simple prompt."""
        from src.generation.llm import get_chat_llm
        from src.config import settings

        # Skip if no API key configured
        if not settings.google_api_key:
            pytest.skip("GOOGLE_API_KEY not configured")

        llm = get_chat_llm()
        response = llm.invoke("Say 'Hello World' in exactly two words.")

        assert response is not None
        assert hasattr(response, 'content')
        assert len(response.content) > 0

    def test_gemini_french_response(self):
        """Test that Gemini can respond in French."""
        from src.generation.llm import get_chat_llm
        from src.config import settings

        if not settings.google_api_key:
            pytest.skip("GOOGLE_API_KEY not configured")

        llm = get_chat_llm()
        response = llm.invoke("Réponds 'Bonjour le monde' en français.")

        assert response is not None
        assert "bonjour" in response.content.lower() or "monde" in response.content.lower()

    def test_gemini_json_output(self):
        """Test that Gemini can produce structured JSON output."""
        from src.generation.llm import get_chat_llm
        from src.config import settings
        import json

        if not settings.google_api_key:
            pytest.skip("GOOGLE_API_KEY not configured")

        llm = get_chat_llm()
        prompt = """Return a JSON object with exactly this structure:
{"event": "Concert", "city": "Paris"}
Only output the JSON, nothing else."""

        response = llm.invoke(prompt)

        # Try to parse as JSON
        content = response.content.strip()
        # Handle markdown code blocks
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()

        parsed = json.loads(content)
        assert "event" in parsed or "city" in parsed

    def test_gemini_rate_limit_handling(self):
        """Test that rate limit errors are properly identified."""
        from src.generation.llm import is_retryable_llm_error

        # Simulate rate limit error
        error = Exception("429 Resource Exhausted: Quota exceeded")
        assert is_retryable_llm_error(error) is True

    def test_mistral_llm_wrapper_with_gemini(self):
        """Test MistralLLM wrapper class uses Gemini backend."""
        from src.generation.llm import MistralLLM
        from src.config import settings

        if not settings.google_api_key:
            pytest.skip("GOOGLE_API_KEY not configured")

        # MistralLLM is the wrapper class (named for backward compatibility)
        # It should use Gemini when llm_backend="google"
        llm = MistralLLM()

        response = llm.invoke("Reply with just the word 'OK'")

        assert response is not None
        # Response could be AIMessage or string depending on backend
        content = response.content if hasattr(response, 'content') else str(response)
        assert len(content) > 0


class TestMistralEmbeddingsLive:
    """Integration tests for Mistral Embeddings (real API calls)."""

    def test_mistral_embed_single_text(self):
        """Test embedding a single text produces correct dimensions."""
        from src.models.embeddings import EventEmbedder
        from src.config import settings

        if not settings.mistral_api_key:
            pytest.skip("MISTRAL_API_KEY not configured")

        embedder = EventEmbedder()
        text = "Concert de jazz à Paris"

        embedding = embedder.embed_query(text)

        # Mistral embed model produces 1024-dimensional vectors
        assert embedding is not None
        assert len(embedding) == 1024
        assert all(isinstance(x, float) for x in embedding)

    def test_mistral_embed_batch(self):
        """Test embedding multiple texts in a batch."""
        from src.models.embeddings import EventEmbedder
        from src.config import settings

        if not settings.mistral_api_key:
            pytest.skip("MISTRAL_API_KEY not configured")

        embedder = EventEmbedder()
        texts = [
            "Concert de jazz à Paris",
            "Exposition d'art moderne",
            "Festival de musique électronique"
        ]

        # Use internal embeddings object for batch processing
        embeddings = embedder.embeddings.embed_documents(texts)

        assert len(embeddings) == 3
        assert all(len(emb) == 1024 for emb in embeddings)

    def test_mistral_embed_unicode(self):
        """Test embedding text with unicode characters."""
        from src.models.embeddings import EventEmbedder
        from src.config import settings

        if not settings.mistral_api_key:
            pytest.skip("MISTRAL_API_KEY not configured")

        embedder = EventEmbedder()
        # French accents and special characters
        text = "Événement culturel à Île-de-France: théâtre, opéra, café-concert"

        embedding = embedder.embed_query(text)

        assert embedding is not None
        assert len(embedding) == 1024

    def test_mistral_embed_empty_handling(self):
        """Test that empty text is handled gracefully."""
        from src.models.embeddings import EventEmbedder
        from src.config import settings

        if not settings.mistral_api_key:
            pytest.skip("MISTRAL_API_KEY not configured")

        embedder = EventEmbedder()

        # Empty string should either return zeros or raise a clear error
        try:
            embedding = embedder.embed_query("")
            # If it succeeds, should still be correct dimension
            assert len(embedding) == 1024
        except Exception as e:
            # Acceptable to raise error for empty input
            assert "empty" in str(e).lower() or "invalid" in str(e).lower()

    def test_embedding_similarity(self):
        """Test that semantically similar texts have high cosine similarity."""
        from src.models.embeddings import EventEmbedder
        from src.config import settings
        import numpy as np

        if not settings.mistral_api_key:
            pytest.skip("MISTRAL_API_KEY not configured")

        embedder = EventEmbedder()

        # Similar texts
        text1 = "Concert de jazz à Paris"
        text2 = "Spectacle de jazz parisien"

        # Different text
        text3 = "Cours de cuisine italienne"

        emb1 = np.array(embedder.embed_query(text1))
        emb2 = np.array(embedder.embed_query(text2))
        emb3 = np.array(embedder.embed_query(text3))

        # Cosine similarity
        def cosine_sim(a, b):
            return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

        sim_similar = cosine_sim(emb1, emb2)
        sim_different = cosine_sim(emb1, emb3)

        # Similar texts should have higher similarity
        assert sim_similar > sim_different
        # Similar texts should be quite close
        assert sim_similar > 0.7


class TestUnifiedAnalyzerLive:
    """Integration tests for the unified query analyzer (uses Gemini)."""

    def test_analyze_simple_query(self):
        """Test analyzing a simple event search query."""
        from src.retrieval.unified_analyzer import unified_analyze, QueryIntent
        from src.config import settings

        if not settings.google_api_key:
            pytest.skip("GOOGLE_API_KEY not configured")

        result = unified_analyze(
            query="Concerts de jazz à Paris ce weekend",
            chat_history=[],
            known_cities=["paris", "lyon", "versailles"]
        )

        assert result is not None
        assert result.intent == QueryIntent.EVENT_SEARCH
        assert result.city_normalized == "paris"

    def test_analyze_greeting(self):
        """Test that greeting is correctly detected."""
        from src.retrieval.unified_analyzer import unified_analyze, QueryIntent
        from src.config import settings

        if not settings.google_api_key:
            pytest.skip("GOOGLE_API_KEY not configured")

        result = unified_analyze(
            query="Bonjour!",
            chat_history=[],
            known_cities=["paris"]
        )

        assert result is not None
        assert result.intent == QueryIntent.GREETING

    def test_analyze_off_topic(self):
        """Test that off-topic queries are correctly detected."""
        from src.retrieval.unified_analyzer import unified_analyze, QueryIntent
        from src.config import settings

        if not settings.google_api_key:
            pytest.skip("GOOGLE_API_KEY not configured")

        result = unified_analyze(
            query="Quelle est la capitale de l'Australie?",
            chat_history=[],
            known_cities=["paris"]
        )

        assert result is not None
        assert result.intent == QueryIntent.OFF_TOPIC

    def test_analyze_typo_correction(self):
        """Test that city typos are detected and corrected."""
        from src.retrieval.unified_analyzer import unified_analyze
        from src.config import settings

        if not settings.google_api_key:
            pytest.skip("GOOGLE_API_KEY not configured")

        result = unified_analyze(
            query="Concerts à Pari",  # Typo: Pari instead of Paris
            chat_history=[],
            known_cities=["paris", "lyon", "versailles"]
        )

        assert result is not None
        # Should detect and correct the typo, or normalize the city
        # The city_normalized field should contain "paris"
        if result.city_normalized:
            assert "paris" in result.city_normalized.lower()
        elif result.has_typo_correction:
            original, corrected = result.typo_correction
            assert "paris" in corrected.lower()


class TestRAGChainLive:
    """Integration tests for the full RAG chain (uses both Gemini and Mistral)."""

    def test_rag_chain_simple_query(self):
        """Test full RAG chain with a simple query."""
        from src.retrieval.chain import RAGChain
        from src.config import settings

        if not settings.google_api_key or not settings.mistral_api_key:
            pytest.skip("API keys not configured")

        chain = RAGChain()
        result = chain.query_with_metadata(
            question="Quels concerts y a-t-il à Paris?",
            session_id="test_live_session"
        )

        assert result is not None
        assert "answer" in result
        assert len(result["answer"]) > 0

    def test_rag_chain_greeting_bypass(self):
        """Test that greetings bypass the RAG pipeline."""
        from src.retrieval.chain import RAGChain
        from src.config import settings

        if not settings.google_api_key:
            pytest.skip("GOOGLE_API_KEY not configured")

        chain = RAGChain()
        result = chain.query_with_metadata(
            question="Bonjour!",
            session_id="test_greeting_session"
        )

        assert result is not None
        assert "answer" in result
        # Should contain greeting response
        assert "bonjour" in result["answer"].lower() or "hello" in result["answer"].lower()


class TestErrorHandling:
    """Test error handling with real API scenarios."""

    def test_invalid_api_key_handling(self):
        """Test that invalid API key produces clear error."""
        from src.generation.llm import MistralLLM
        import os

        # Temporarily set invalid key
        original_key = os.environ.get("GOOGLE_API_KEY")
        try:
            os.environ["GOOGLE_API_KEY"] = "invalid_key_12345"

            # Should handle gracefully (either raise or return error message)
            try:
                with patch('src.config.settings.google_api_key', 'invalid_key_12345'):
                    llm = MistralLLM()
                    response = llm.invoke("test")
                # If it reaches here, should have error in response
            except Exception as e:
                # Should be authentication error
                error_str = str(e).lower()
                assert "api" in error_str or "auth" in error_str or "key" in error_str or "invalid" in error_str
        finally:
            # Restore original key
            if original_key:
                os.environ["GOOGLE_API_KEY"] = original_key


