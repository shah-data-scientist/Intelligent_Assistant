"""
FILE: test_prompts.py
STATUS: Active
RESPONSIBILITY: Unit tests for LLM prompt templates (French and English RAG prompts).

DEPENDENCIES (Who uses this file):
- pytest test runner
- Prompt template validation

IMPORTS (What this file needs):
- pytest: Test framework
- src.generation.prompts: Prompt templates

LAST MAJOR UPDATE: 2026-01-31
MAINTAINER: QA Team
"""

import pytest
import json
from src.generation.prompts import (
    RAG_SYSTEM_PROMPT,
    RAG_SYSTEM_PROMPT_FR,
    RAG_SYSTEM_PROMPT_EN,
    get_rag_system_prompt,
    get_rag_prompt,
)


class TestPromptStructure:
    """Test prompt structure and required sections."""

    def test_rag_prompt_fr_has_required_sections(self):
        """Test French RAG_SYSTEM_PROMPT has all required sections."""
        assert "Tu es" in RAG_SYSTEM_PROMPT_FR
        assert "REGLES" in RAG_SYSTEM_PROMPT_FR
        assert "ANCRAGE" in RAG_SYSTEM_PROMPT_FR
        assert "FORMAT" in RAG_SYSTEM_PROMPT_FR or "JSON" in RAG_SYSTEM_PROMPT_FR

    def test_rag_prompt_en_has_required_sections(self):
        """Test English RAG_SYSTEM_PROMPT has all required sections."""
        assert "You are" in RAG_SYSTEM_PROMPT_EN
        assert "RULES" in RAG_SYSTEM_PROMPT_EN
        assert "GROUNDING" in RAG_SYSTEM_PROMPT_EN
        assert "FORMAT" in RAG_SYSTEM_PROMPT_EN or "JSON" in RAG_SYSTEM_PROMPT_EN

    def test_rag_prompt_has_template_variables(self):
        """Test prompt has required template variables."""
        # Check French prompt
        assert "{today}" in RAG_SYSTEM_PROMPT_FR
        assert "{k}" in RAG_SYSTEM_PROMPT_FR

        # Check English prompt
        assert "{today}" in RAG_SYSTEM_PROMPT_EN
        assert "{k}" in RAG_SYSTEM_PROMPT_EN

    def test_rag_prompt_specifies_json_format(self):
        """Test prompt requires JSON output."""
        # Check French prompt
        assert "JSON" in RAG_SYSTEM_PROMPT_FR or "json" in RAG_SYSTEM_PROMPT_FR
        assert "answer_text" in RAG_SYSTEM_PROMPT_FR
        assert "events" in RAG_SYSTEM_PROMPT_FR

        # Check English prompt
        assert "JSON" in RAG_SYSTEM_PROMPT_EN or "json" in RAG_SYSTEM_PROMPT_EN
        assert "answer_text" in RAG_SYSTEM_PROMPT_EN
        assert "events" in RAG_SYSTEM_PROMPT_EN

    def test_rag_prompt_prevents_hallucination(self):
        """Test prompt has anti-hallucination rules."""
        # French prompt should mention sources/grounding
        prompt_fr_lower = RAG_SYSTEM_PROMPT_FR.lower()
        assert any(word in prompt_fr_lower for word in ["sources", "uniquement", "ancrage"])

        # English prompt should mention sources/grounding
        prompt_en_lower = RAG_SYSTEM_PROMPT_EN.lower()
        assert any(word in prompt_en_lower for word in ["sources", "only", "grounding"])

    def test_rag_prompt_not_empty(self):
        """Test prompts are not empty."""
        assert len(RAG_SYSTEM_PROMPT_FR) > 100
        assert len(RAG_SYSTEM_PROMPT_EN) > 100

    def test_rag_prompt_en_is_default(self):
        """Test English is the default prompt."""
        assert RAG_SYSTEM_PROMPT == RAG_SYSTEM_PROMPT_EN

    def test_get_rag_system_prompt_french(self):
        """Test get_rag_system_prompt returns French prompt."""
        prompt = get_rag_system_prompt(language="fr")
        assert prompt == RAG_SYSTEM_PROMPT_FR

    def test_get_rag_system_prompt_english(self):
        """Test get_rag_system_prompt returns English prompt."""
        prompt = get_rag_system_prompt(language="en")
        assert prompt == RAG_SYSTEM_PROMPT_EN

    def test_get_rag_system_prompt_defaults_to_english(self):
        """Test get_rag_system_prompt defaults to English."""
        prompt = get_rag_system_prompt()
        assert prompt == RAG_SYSTEM_PROMPT_EN


class TestPromptTemplate:
    """Test prompt template creation."""

    def test_get_rag_prompt_french(self):
        """Test get_rag_prompt returns valid template for French."""
        prompt_template = get_rag_prompt(language="fr")
        assert prompt_template is not None
        assert len(prompt_template.messages) > 0

    def test_get_rag_prompt_english(self):
        """Test get_rag_prompt returns valid template for English."""
        prompt_template = get_rag_prompt(language="en")
        assert prompt_template is not None
        assert len(prompt_template.messages) > 0

    def test_prompt_template_has_system_message(self):
        """Test prompt template includes system message."""
        prompt_template = get_rag_prompt(language="fr")
        # Should have at least one message
        assert len(prompt_template.messages) >= 1

    def test_prompt_template_has_human_message(self):
        """Test prompt template includes human message placeholder."""
        prompt_template = get_rag_prompt(language="fr")
        # Should have multiple messages (system + human)
        assert len(prompt_template.messages) >= 2


class TestPromptConsistency:
    """Test consistency between French and English prompts."""

    def test_both_prompts_have_similar_length(self):
        """Test French and English prompts have similar structure."""
        # Both should have similar length (within 50%)
        length_ratio = len(RAG_SYSTEM_PROMPT_EN) / len(RAG_SYSTEM_PROMPT_FR)
        assert 0.5 < length_ratio < 1.5, "Prompts have very different lengths"

    def test_both_prompts_have_same_core_template_variables(self):
        """Test both prompts use same core template variables."""
        # Both should have these core variables
        core_vars = ["{today}", "{k}"]
        for var in core_vars:
            assert var in RAG_SYSTEM_PROMPT_FR, f"Missing {var} in French prompt"
            assert var in RAG_SYSTEM_PROMPT_EN, f"Missing {var} in English prompt"

    def test_both_prompts_specify_json_output(self):
        """Test both prompts require same JSON structure."""
        assert "answer_text" in RAG_SYSTEM_PROMPT_FR
        assert "answer_text" in RAG_SYSTEM_PROMPT_EN
        assert "events" in RAG_SYSTEM_PROMPT_FR
        assert "events" in RAG_SYSTEM_PROMPT_EN


class TestPromptFormatting:
    """Test prompt formatting with actual values."""

    def test_prompt_format_with_all_variables(self):
        """Test prompt can be formatted with all required variables."""
        template_vars = {
            "today": "2026-01-30",
            "k": 5,
            "exact_count": 3,
            "nearby_count": 2,
            "filters_applied": "Paris, Jazz, February",
            "total_events": 1000,
            "date_range": "2026-01 to 2026-12",
        }
        formatted = RAG_SYSTEM_PROMPT_FR.format(**template_vars)

        # Should contain the formatted values
        assert "2026-01-30" in formatted
        # Should not contain template placeholders for required vars
        assert "{today}" not in formatted
        assert "{k}" not in formatted

    def test_prompt_format_handles_zero_results(self):
        """Test prompt formatting with zero results."""
        template_vars = {
            "today": "2026-01-30",
            "k": 0,
            "exact_count": 0,
            "nearby_count": 0,
            "filters_applied": "None",
            "total_events": 1000,
            "date_range": "2026-01 to 2026-12",
        }
        formatted = RAG_SYSTEM_PROMPT_FR.format(**template_vars)

        # Should handle k=0 gracefully
        assert "0" in formatted


class TestPromptEdgeCases:
    """Test prompt behavior with edge cases."""

    def test_prompt_not_too_long(self):
        """Test prompt is not excessively long (token limit concerns)."""
        # Rough estimate: 1 token ≈ 4 characters
        # Keep prompts under 4000 tokens (16000 chars)
        assert len(RAG_SYSTEM_PROMPT_FR) < 16000, "French prompt may exceed token limits"
        assert len(RAG_SYSTEM_PROMPT_EN) < 16000, "English prompt may exceed token limits"

    def test_prompt_uses_template_variables_for_dates(self):
        """Test prompt uses {today} template variable."""
        assert "{today}" in RAG_SYSTEM_PROMPT_FR
        assert "{today}" in RAG_SYSTEM_PROMPT_EN

    def test_prompt_encoding_is_utf8(self):
        """Test prompt can be encoded as UTF-8 (handles French characters)."""
        try:
            RAG_SYSTEM_PROMPT_FR.encode("utf-8")
            RAG_SYSTEM_PROMPT_EN.encode("utf-8")
        except UnicodeEncodeError:
            pytest.fail("Prompt contains characters that cannot be encoded as UTF-8")

    def test_prompt_has_zero_hallucination_rules(self):
        """Test prompt explicitly prohibits hallucination."""
        # French prompt
        fr_lower = RAG_SYSTEM_PROMPT_FR.lower()
        assert any(word in fr_lower for word in ["jamais inventer", "ne pas inventer", "uniquement"])

        # English prompt
        en_lower = RAG_SYSTEM_PROMPT_EN.lower()
        assert any(word in en_lower for word in ["never fabricate", "only", "must correspond"])


# Mark integration tests that make real LLM calls
@pytest.mark.integration
@pytest.mark.skip(reason="Requires LLM API call - expensive and slow")
class TestPromptOutputFormat:
    """Integration tests for prompt output format (requires LLM)."""

    def test_prompt_generates_valid_json(self):
        """Test prompt produces parseable JSON (integration test)."""
        from src.generation.llm import get_llm

        llm = get_llm()
        test_query = "Concerts de jazz à Paris"
        test_sources = [{"title": "Concert 1", "date": "2026-02-01"}, {"title": "Concert 2", "date": "2026-02-15"}]

        template_vars = {
            "today": "2026-01-30",
            "k": 2,
            "exact_count": 2,
            "nearby_count": 0,
            "filters_applied": "Paris, Jazz",
            "total_events": 1000,
            "date_range": "2026-01 to 2026-12",
        }
        formatted_prompt = RAG_SYSTEM_PROMPT_FR.format(**template_vars)
        response = llm.invoke(formatted_prompt + f"\nQuery: {test_query}\nSources: {test_sources}")

        # Should be parseable as JSON
        try:
            data = json.loads(response)
            assert "answer_text" in data
            assert "events" in data
        except json.JSONDecodeError:
            pytest.fail("Prompt did not generate valid JSON")
