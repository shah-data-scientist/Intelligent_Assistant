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

LAST MAJOR UPDATE: 2026-01-28 (Enhanced grounding rules to prevent hallucinations)
MAINTAINER: Core Backend Team
"""

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from src.config import settings

# ========================================
# RAG SYSTEM PROMPTS (Bilingual: French and English)
# ========================================
# DESIGN DECISION: FR/EN prompts are kept as separate templates (not merged into a
# single base template) because:
# 1. They are TRANSLATIONS, not duplicated code - each has language-specific nuances
# 2. Explicit templates are easier to read/maintain than a placeholder system
# 3. Chatbot identity (name, personality) is already centralized via settings
# 4. Adding a base template + translation dict would increase complexity without benefit
#
# SHARED ELEMENTS (via settings):
# - __NAME__, __NAME_UPPER__: Chatbot name from config.py
# - __TAGLINE__: Language-specific tagline from config.py
# - __PERSONALITY__: Language-specific personality traits from config.py
#
# TEMPLATE VARIABLES (filled at runtime):
# - {today}, {k}, {total_matching}, {filters_applied}, {total_events}, {date_range}

# French System Prompt (uses centralized config for name and personality)
# Note: Uses .replace() to inject config values while preserving {today}, {k}, etc. as template vars
# ARCHITECTURE: Completeness validation (2-out-of-3 rule: city, event type, date) is handled
# BEFORE this prompt by UnifiedAnalyzer. When this prompt runs, query is confirmed complete.
_RAG_SYSTEM_PROMPT_FR_TEMPLATE = """Tu es **__NAME__**, __TAGLINE__.

**DATE D'AUJOURD'HUI:** {today}
**RESULTATS:** {k} evenements ({exact_count} dans la ville, {nearby_count} villes proches)
**FILTRES:** {filters_applied}
**BASE:** {total_events} evenements, {date_range}

**SOURCES:** "Exact Match" = ville demandee | "Nearby Location" = villes voisines (par distance)

**REGLES STRICTES:**

1. **ANCRAGE (ZERO HALLUCINATION):**
   - Liste UNIQUEMENT les evenements des SOURCES
   - NE JAMAIS inventer de details (titre, date, ville, prix, URL)
   - Si info manquante dans SOURCE, omettre le champ
   - Compte les SOURCES: dis "Voici {k} evenements"

2. **TRANSPARENCE:**
   - Repete les criteres (type evenement, date)
   - Mentionne la ville UNIQUEMENT si {exact_count} > 0
   - Indique {exact_count} vs {nearby_count} clairement
   - Si NOTE SYSTEME dates alternatives: signale-le

3. **FORMAT JSON:**
   {{
     "answer_text": "Voici {k} evenements...",
     "events": [EXACTEMENT {k} evenements]
   }}
   - Inclure TOUS les evenements des SOURCES
   - Ne pas consolider (meme titre + dates differentes = evenements separes)
   - Champs: title, date, city, location, url, match_type (requis) + timings, price_label, age_label (si disponibles)

4. **STYLE __NAME_UPPER__:** Chaleureux et enthousiaste !
"""

RAG_SYSTEM_PROMPT_FR = (
    _RAG_SYSTEM_PROMPT_FR_TEMPLATE
    .replace("__NAME__", settings.chatbot_name)
    .replace("__NAME_UPPER__", settings.chatbot_name.upper())
    .replace("__TAGLINE__", settings.chatbot_tagline_fr)
    .replace("__PERSONALITY__", settings.chatbot_personality_fr)
)

# English System Prompt (uses centralized config for name and personality)
# Note: Uses .replace() to inject config values while preserving {today}, {k}, etc. as template vars
# ARCHITECTURE: Completeness validation (2-out-of-3 rule: city, event type, date) is handled
# BEFORE this prompt by UnifiedAnalyzer. When this prompt runs, query is confirmed complete.
_RAG_SYSTEM_PROMPT_EN_TEMPLATE = """You are **__NAME__**, __TAGLINE__.

**TODAY'S DATE:** {today}
**RESULTS:** {k} events ({exact_count} in city, {nearby_count} nearby towns)
**FILTERS:** {filters_applied}
**DATABASE:** {total_events} events, {date_range}

**SOURCES:** "Exact Match" = requested city | "Nearby Location" = neighboring cities (by distance)

**STRICT RULES:**

1. **GROUNDING (ZERO HALLUCINATION):**
   - List ONLY events from SOURCES
   - NEVER fabricate details (title, date, city, price, URL)
   - If info missing in SOURCE, omit the field
   - Count SOURCES: say "Here are {k} events"

2. **TRANSPARENCY:**
   - Repeat query criteria (event type, date)
   - Mention city ONLY if {exact_count} > 0
   - Indicate {exact_count} vs {nearby_count} clearly
   - If SYSTEM NOTE mentions alternative dates: tell user

3. **JSON FORMAT:**
   {{
     "answer_text": "Here are {k} events...",
     "events": [EXACTLY {k} events]
   }}
   - Include ALL events from SOURCES
   - Do not consolidate (same title + different dates = separate events)
   - Fields: title, date, city, location, url, match_type (required) + timings, price_label, age_label (if available)

4. **STYLE __NAME_UPPER__:** Warm and enthusiastic!
"""

RAG_SYSTEM_PROMPT_EN = (
    _RAG_SYSTEM_PROMPT_EN_TEMPLATE
    .replace("__NAME__", settings.chatbot_name)
    .replace("__NAME_UPPER__", settings.chatbot_name.upper())
    .replace("__TAGLINE__", settings.chatbot_tagline_en)
    .replace("__PERSONALITY__", settings.chatbot_personality_en)
)

# Default prompt (for backward compatibility)
RAG_SYSTEM_PROMPT = RAG_SYSTEM_PROMPT_EN


def get_rag_system_prompt(language: str = "en") -> str:
    """Get language-specific RAG system prompt.

    Args:
        language: Language code ("fr" or "en")

    Returns:
        System prompt string in the requested language
    """
    if language == "fr":
        return RAG_SYSTEM_PROMPT_FR
    else:
        return RAG_SYSTEM_PROMPT_EN


# Update RAG prompt to accept chat history (though primarily used by the chain logic)

RAG_PROMPT = ChatPromptTemplate.from_messages(

    [

        ("system", RAG_SYSTEM_PROMPT),

        MessagesPlaceholder("chat_history"),

        ("human", "{input}"),

    ]

)



def get_rag_prompt(language: str = "en") -> ChatPromptTemplate:
    """Get the RAG prompt template with language-specific system prompt.

    Args:
        language: Language code ("fr" or "en")

    Returns:
        ChatPromptTemplate instance with language-specific system prompt
    """
    system_prompt = get_rag_system_prompt(language)

    # CRITICAL: Include {context} (source documents) in the human message
    # This ensures the LLM has access to the actual retrieved events to ground its response
    return ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        MessagesPlaceholder("chat_history"),
        ("human", "Question: {input}\n\n**SOURCES (GROUND YOUR RESPONSE IN THESE EVENTS ONLY - DO NOT INVENT ANY DETAILS):**\n{context}"),
    ])



