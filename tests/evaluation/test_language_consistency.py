"""
FILE: test_language_consistency.py
STATUS: Active
RESPONSIBILITY: Tests for bilingual consistency between French and English queries.

DEPENDENCIES (Who uses this file):
- pytest test runner
- Bilingual feature validation

IMPORTS (What this file needs):
- pytest: Test framework
- src.retrieval.chain: RAGChain for bilingual testing

LAST MAJOR UPDATE: 2026-01-31
MAINTAINER: QA Team
"""

import pytest
from src.retrieval.chain import RAGChain


@pytest.fixture
def rag_chain():
    """Initialize RAG chain for testing."""
    return RAGChain()


@pytest.mark.integration
@pytest.mark.skip(reason="Dynamic language support pending implementation in RAGChain")
def test_language_consistency_french(rag_chain):
    """Test that a French query returns a French response."""
    query_fr = "Quels sont les concerts de jazz à Paris ?"
    response = rag_chain.query(query_fr)

    # Simple heuristic checks for French stopwords
    french_indicators = ["le", "la", "les", "et", "à", "en", "est", "sont"]
    english_indicators = ["the", "and", "is", "are", "in", "at", "for"]

    response_lower = response.lower()

    fr_count = sum(1 for word in french_indicators if f" {word} " in response_lower)
    en_count = sum(1 for word in english_indicators if f" {word} " in response_lower)

    assert fr_count > en_count, f"Response to French query seems to be in English. Response: {response[:100]}..."


@pytest.mark.integration
def test_language_consistency_english(rag_chain):
    """Test that an English query returns an English response."""
    query_en = "What are the jazz concerts in Paris?"
    response = rag_chain.query(query_en)

    french_indicators = ["le", "la", "les", "et", "à", "en", "est", "sont"]
    english_indicators = ["the", "and", "is", "are", "in", "at", "for"]

    response_lower = response.lower()

    fr_count = sum(1 for word in french_indicators if f" {word} " in response_lower)
    en_count = sum(1 for word in english_indicators if f" {word} " in response_lower)

    assert en_count > fr_count, f"Response to English query seems to be in French. Response: {response[:100]}..."


@pytest.mark.integration
def test_response_length_constraint(rag_chain):
    """Test that the response adheres to length constraints."""
    query = "Tell me about all the theater events in Paris."
    response = rag_chain.query(query)

    # Calculate word count
    word_count = len(response.split())

    # We want to enforce a max length (e.g., 300 words for a concise summary)
    MAX_WORDS = 300
    assert word_count <= MAX_WORDS, f"Response too long: {word_count} words (Limit: {MAX_WORDS})"
