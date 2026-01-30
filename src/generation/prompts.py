"""
FILE: prompts.py
STATUS: Active
RESPONSIBILITY: Bilingual LangChain prompt templates for RAG system with grounding rules and JSON output format.

DEPENDENCIES (Who uses this file):
- src/retrieval/chain.py: Uses get_rag_prompt() for answer generation
- tests/unit/test_prompts.py: Tests prompt structure and template variables
- tests/integration/test_code_integration.py: Integration tests with prompt templates

IMPORTS (What this file needs):
- langchain_core.prompts: ChatPromptTemplate for structured prompts
- src.config: Chatbot name, tagline, and personality settings
- src.utils.i18n: Translation system for bilingual prompts

LAST MAJOR UPDATE: 2026-01-31 (v1.10.0 - migrated to i18n framework)
MAINTAINER: Core Backend Team
"""

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from src.config import settings
from src.utils.i18n import get_translator


def build_rag_system_prompt(language: str = "fr") -> str:
    """Build RAG system prompt from i18n templates.

    Args:
        language: Language code (fr/en)

    Returns:
        Complete system prompt with chatbot identity injected
    """
    t = get_translator(language)

    # Get language-specific tagline from settings
    tagline = settings.chatbot_tagline_fr if language == "fr" else settings.chatbot_tagline_en

    # Build prompt from translated components
    prompt_parts = [
        t.get("prompts.rag_system_base", name=settings.chatbot_name, tagline=tagline),
        "",
        t.get("prompts.rag_system_date"),
        t.get("prompts.rag_system_results"),
        t.get("prompts.rag_system_filters"),
        t.get("prompts.rag_system_database"),
        "",
        t.get("prompts.rag_system_sources"),
        "",
        t.get("prompts.rule_grounding"),
        "",
        t.get("prompts.rule_transparency"),
        "",
        t.get("prompts.rule_format"),
        "",
        t.get("prompts.rule_style", name_upper=settings.chatbot_name.upper()),
    ]

    return "\n".join(prompt_parts)


# Pre-build prompts for both languages
RAG_SYSTEM_PROMPT_FR = build_rag_system_prompt("fr")
RAG_SYSTEM_PROMPT_EN = build_rag_system_prompt("en")

# Default prompt (for backward compatibility)
RAG_SYSTEM_PROMPT = RAG_SYSTEM_PROMPT_EN


def get_rag_system_prompt(language: str = "en") -> str:
    """Get language-specific RAG system prompt.

    Args:
        language: Language code (fr/en)

    Returns:
        RAG system prompt string
    """
    if language == "fr":
        return RAG_SYSTEM_PROMPT_FR
    else:
        return RAG_SYSTEM_PROMPT_EN


def get_rag_prompt(language: str = "en") -> ChatPromptTemplate:
    """Get RAG prompt template with language-specific system prompt.

    Args:
        language: Language code (fr/en)

    Returns:
        ChatPromptTemplate with system prompt, chat history, and human message
    """
    system_prompt = get_rag_system_prompt(language)

    # CRITICAL: Include {context} (source documents) in the human message
    # This ensures the LLM has access to the actual retrieved events to ground its response
    return ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            MessagesPlaceholder("chat_history"),
            (
                "human",
                "Question: {input}\n\n**SOURCES (GROUND YOUR RESPONSE IN THESE EVENTS ONLY - DO NOT INVENT ANY DETAILS):**\n{context}",
            ),
        ]
    )
