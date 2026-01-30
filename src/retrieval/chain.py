"RAG orchestration chain for cultural events with history."

import logging
import re
import threading
from typing import Any, Dict, List, Optional, Tuple
from datetime import date, timedelta

from langchain_core.runnables import RunnablePassthrough, RunnableLambda, RunnableBranch
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from langchain_core.output_parsers.base import BaseOutputParser
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, BaseMessage
import json

from src.models.vector_store import EventVectorStore
from src.generation.llm import MistralLLM
from src.generation.prompts import get_rag_prompt
from src.retrieval.cache import QueryCache
from src.retrieval.manager import RetrievalManager
from src.data.chat_history import SQLiteChatMessageHistory
from src.data.storage import EventStorage
from src.data.chat_storage import ChatStorage
from src.security.guardrails import check_safety
from src.utils.geo import CityLocator
from src.utils.keywords import get_keyword_locator
from src.retrieval.unified_analyzer import unified_analyze, QueryIntent as UnifiedIntent, UnifiedAnalysisResult, QueryDimension, map_category_to_db
from src.retrieval.response_builder import ResponseBuilder
from src.config import settings

# ========================================
# ROBUST JSON PARSER WITH TEXT FALLBACK
# ========================================
# Handles JSON parsing failures by extracting text content from the LLM response.
# This is critical for HuggingFace models that may return truncated JSON.

class RobustJsonParser(BaseOutputParser):
    """JSON parser with fallback to text extraction when JSON parsing fails.

    When the LLM returns truncated or malformed JSON (common with smaller models),
    this parser extracts the readable text content instead of raising an error.
    """

    def parse(self, text: str) -> Dict[str, Any]:
        """Parse LLM output, falling back to text extraction if JSON fails."""
        # First, try standard JSON parsing
        try:
            # Try to find JSON in the text (may be wrapped in markdown code blocks)
            json_match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(1))

            # Try parsing the whole text as JSON
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # JSON parsing failed - extract text content as fallback
        logger.warning(f"[ROBUST-PARSER] JSON parsing failed, extracting text fallback")

        # Try to extract answer_text from partial JSON
        answer_match = re.search(r'"answer_text"\s*:\s*"(.*?)(?:"|$)', text, re.DOTALL)
        if answer_match:
            answer_text = answer_match.group(1)
            # Unescape common JSON escapes
            answer_text = answer_text.replace('\\n', '\n').replace('\\"', '"')
            logger.info(f"[ROBUST-PARSER] Extracted answer_text from partial JSON ({len(answer_text)} chars)")
            return {"answer_text": answer_text, "events": []}

        # Try to extract readable text before any JSON
        # HuggingFace models often produce: "Here are the events:\n1. Event A\n2. Event B\n\n{json...}"
        json_start = text.find('{')
        if json_start > 50:  # Significant text before JSON
            readable_text = text[:json_start].strip()
            if readable_text:
                logger.info(f"[ROBUST-PARSER] Extracted pre-JSON text ({len(readable_text)} chars)")
                return {"answer_text": readable_text, "events": []}

        # Last resort: use the entire text as the answer (cleaned up)
        # Remove any partial JSON fragments
        clean_text = re.sub(r'\{[^}]*$', '', text)  # Remove trailing incomplete JSON
        clean_text = re.sub(r'```json.*', '', clean_text, flags=re.DOTALL)  # Remove code blocks
        clean_text = clean_text.strip()

        if clean_text:
            logger.info(f"[ROBUST-PARSER] Using cleaned text as answer ({len(clean_text)} chars)")
            return {"answer_text": clean_text, "events": []}

        # Absolute fallback
        logger.warning("[ROBUST-PARSER] No usable text found, returning empty response")
        return {"answer_text": "Je n'ai pas pu traiter votre demande. Veuillez reformuler.", "events": []}

    @property
    def _type(self) -> str:
        return "robust_json"


# Feature flag: Use unified LLM analyzer instead of keyword-based checks
# This consolidates intent + entity extraction + filters into ONE LLM call
# Benefits: Better city normalization (Plessis → Le Plessis-Robinson),
# robust intent detection, no keyword false positives ("search" as city)
USE_UNIFIED_ANALYZER = True

# Global city locator for scope validation
_city_locator = None

def get_city_locator() -> CityLocator:
    """Get or create the global CityLocator instance."""
    global _city_locator
    if _city_locator is None:
        _city_locator = CityLocator()
    return _city_locator

logger = logging.getLogger(__name__)

# ========================================
# ASYNC DATABASE WRITE HELPER
# ========================================
# Fire-and-forget database writes to reduce response latency

def _background_db_write(func, *args, **kwargs):
    """Execute a database write in a background thread (fire-and-forget).

    This reduces perceived latency by not waiting for database writes.
    Errors are logged but don't block the response.

    Args:
        func: The function to call (e.g., chat_storage.add_chat_message)
        *args: Positional arguments for the function
        **kwargs: Keyword arguments for the function
    """
    def _worker():
        try:
            func(*args, **kwargs)
        except Exception as e:
            logger.error(f"[BACKGROUND-DB] Write failed: {e}")

    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()

# ========================================
# SPECIAL QUERY HANDLERS
# ========================================
# These handle greetings, off-topic queries, and capability questions
# BEFORE the RAG chain is invoked.
#
# OPTIMIZATION: All special query detection uses KeywordLocator (database-backed)
# with fuzzy matching for typo detection. No regex patterns needed.

# Greeting responses (bilingual) - Uses centralized config for chatbot name
GREETING_RESPONSES = {
    "fr": f"""Bonjour ! Je suis **{settings.chatbot_name}**, {settings.chatbot_tagline_fr}.

Je peux vous aider a decouvrir des evenements culturels : concerts, expositions, theatre, festivals et plus encore !

**Essayez de me demander :**
- "Concerts de jazz a Paris ce week-end"
- "Expositions gratuites en fevrier"
- "Evenements pour enfants a Versailles"

Qu'est-ce qui vous ferait plaisir aujourd'hui ?""",

    "en": f"""Hello! I'm **{settings.chatbot_name}**, {settings.chatbot_tagline_en}.

I can help you discover cultural events: concerts, exhibitions, theater, festivals and more!

**Try asking me:**
- "Jazz concerts in Paris this weekend"
- "Free exhibitions in February"
- "Family events in Versailles"

What would you like to explore today?"""
}

# Chitchat responses - friendly replies to casual conversation (bilingual)
CHITCHAT_RESPONSES = {
    "fr": f"""Je vais bien, merci de demander !

Je suis **{settings.chatbot_name}**, votre guide des evenements culturels en Ile-de-France.

Y a-t-il un evenement que vous aimeriez decouvrir aujourd'hui ? Par exemple :
- Des concerts ou spectacles
- Des expositions ou musees
- Des evenements pour enfants

Je suis la pour vous aider !""",

    "en": f"""I'm doing well, thanks for asking!

I'm **{settings.chatbot_name}**, your guide to cultural events in Ile-de-France.

Is there an event you'd like to discover today? For example:
- Concerts or shows
- Exhibitions or museums
- Family events

I'm here to help!"""
}

# Capability responses (bilingual) - Uses centralized config for chatbot name
CAPABILITY_RESPONSES = {
    "fr": f"""Je suis **{settings.chatbot_name}**, {settings.chatbot_tagline_fr} !

**Ce que je peux faire :**
- Trouver des evenements culturels (concerts, theatre, expositions, festivals)
- Filtrer par ville, date, categorie, prix (gratuit/payant)
- Suggerer des alternatives si rien ne correspond exactement
- Repondre en francais ou en anglais

**Ce que je ne peux PAS faire :**
- Donner la meteo, ecrire des poemes, ou traduire
- Reserver des billets ou faire des achats
- Repondre a des questions hors du domaine culturel

**Exemples de questions :**
- "Concerts de jazz a Paris en fevrier"
- "Expositions gratuites ce week-end"
- "Evenements pour enfants a Versailles"

Comment puis-je vous aider ?""",

    "en": f"""I'm **{settings.chatbot_name}**, {settings.chatbot_tagline_en}!

**What I can do:**
- Find cultural events (concerts, theater, exhibitions, festivals)
- Filter by city, date, category, price (free/paid)
- Suggest alternatives if nothing matches exactly
- Answer in French or English

**What I canNOT do:**
- Give weather forecasts, write poems, or translate
- Book tickets or make purchases
- Answer questions outside the cultural domain

**Example questions:**
- "Jazz concerts in Paris in February"
- "Free exhibitions this weekend"
- "Family events in Versailles"

How can I help you?"""
}

# Off-topic responses (bilingual)
OFF_TOPIC_RESPONSES = {
    "fr": """Je suis desole, mais je suis specialisee dans les evenements culturels de l'Ile-de-France.

Je ne peux pas vous aider avec cette demande, mais je serais ravie de vous aider a trouver :
- Des concerts, spectacles ou festivals
- Des expositions d'art ou des musees
- Des pieces de theatre ou des spectacles de danse
- Des evenements pour enfants ou en famille

Y a-t-il un evenement culturel que vous aimeriez decouvrir ?""",

    "en": """I'm sorry, but I specialize in cultural events in Ile-de-France.

I can't help with that request, but I'd be happy to help you find:
- Concerts, shows, or festivals
- Art exhibitions or museums
- Theater plays or dance performances
- Family or children's events

Is there a cultural event you'd like to discover?"""
}

# Abuse/insult responses (bilingual) - polite response to rude queries
ABUSE_RESPONSES = {
    "fr": """Je comprends que vous puissiez etre frustre, mais je suis la pour vous aider a decouvrir des evenements culturels en Ile-de-France.

Puis-je vous aider a trouver un concert, une exposition ou un spectacle ?""",

    "en": """I understand you may be frustrated, but I'm here to help you discover cultural events in Ile-de-France.

Can I help you find a concert, exhibition, or show?"""
}

# Directions/transport responses (bilingual) - NEW
DIRECTIONS_RESPONSES = {
    "fr": """Je peux vous aider avec les directions vers un événement !

Pourriez-vous préciser de quel événement vous parlez ? Par exemple, citez le nom de l'événement ou la salle.

Une fois identifié, je vous fournirai l'adresse et un lien Google Maps pour les directions.""",

    "en": """I can help you with directions to an event!

Could you specify which event you're referring to? For example, mention the event name or venue.

Once identified, I'll provide the address and a Google Maps link for directions."""
}

# Out-of-scope city responses (bilingual)
OUT_OF_SCOPE_CITY_RESPONSES = {
    "fr": """Je suis desole, mais **{city}** est en dehors de ma zone de couverture.

Je suis specialisee dans les evenements culturels de la region **Ile-de-France** (Paris et ses environs).

Voulez-vous que je cherche des evenements dans une ville d'Ile-de-France ? Par exemple :
- Paris, Versailles, Saint-Denis
- Boulogne-Billancourt, Montreuil, Nanterre
- Fontainebleau, Meaux, Pontoise""",

    "en": """I'm sorry, but **{city}** is outside my coverage area.

I specialize in cultural events in the **Ile-de-France** region (Paris and its surroundings).

Would you like me to search for events in an Ile-de-France city? For example:
- Paris, Versailles, Saint-Denis
- Boulogne-Billancourt, Montreuil, Nanterre
- Fontainebleau, Meaux, Pontoise"""
}

# Statistical query responses (bilingual) - Now used differently in multi-dimensional mode
STATISTICAL_RESPONSES = {
    "fr": """Je suis conçue pour vous aider à **trouver des événements culturels**, pas pour fournir des statistiques.

**Je peux vous aider à :**
- Trouver des concerts, expositions ou spectacles
- Rechercher par ville, date ou catégorie
- Suggérer des événements selon vos préférences

**Exemple :** "Quels concerts de jazz y a-t-il à Paris ce week-end ?"

Que souhaitez-vous découvrir ?""",

    "en": """I'm designed to help you **find cultural events**, not provide statistics.

**I can help you:**
- Find concerts, exhibitions, or shows
- Search by city, date, or category
- Suggest events based on your preferences

**Example:** "What jazz concerts are there in Paris this weekend?"

What would you like to discover?"""
}

# ========================================
# MULTI-DIMENSIONAL RESPONSE COMPONENTS
# ========================================
# These are building blocks for composing multi-dimensional responses

# Greeting prefixes (added to start of response when greeting dimension detected)
GREETING_PREFIXES = {
    "fr": "Bonjour ! ",
    "en": "Hello! "
}

# Typo correction acknowledgments (added when typo dimension detected)
TYPO_ACKNOWLEDGMENTS = {
    "fr": "Je suppose que vous voulez dire **{corrected}** (et non \"{original}\"). ",
    "en": "I assume you mean **{corrected}** (not \"{original}\"). "
}

# Statistical response templates (used when statistical dimension detected)
STATISTICAL_TEMPLATES = {
    "fr": """J'ai trouvé **{count} événement(s)** correspondant à votre recherche{filters_desc}.

{event_breakdown}""",
    "en": """I found **{count} event(s)** matching your search{filters_desc}.

{event_breakdown}"""
}

# Filter description templates
FILTER_DESC_TEMPLATES = {
    "fr": {
        "city": " à **{value}**",
        "month": " en **{value}**",
        "category": " dans la catégorie **{value}**",
    },
    "en": {
        "city": " in **{value}**",
        "month": " in **{value}**",
        "category": " in category **{value}**",
    }
}

MONTH_NAMES = {
    "fr": ["", "janvier", "février", "mars", "avril", "mai", "juin",
           "juillet", "août", "septembre", "octobre", "novembre", "décembre"],
    "en": ["", "January", "February", "March", "April", "May", "June",
           "July", "August", "September", "October", "November", "December"]
}


def compose_response_prefix(analysis: UnifiedAnalysisResult, language: str, session_id: str = None, correction_tracker: Dict = None) -> str:
    """Compose response prefix based on detected dimensions.

    Args:
        analysis: The unified analysis result with dimensions
        language: Target language (fr/en)
        session_id: Optional session ID for tracking corrections
        correction_tracker: Optional dict to track shown corrections per session

    Returns:
        Prefix string to prepend to main response
    """
    prefix_parts = []

    # Add greeting prefix if greeting dimension detected
    if analysis.has_greeting:
        prefix_parts.append(GREETING_PREFIXES.get(language, ""))

    # Add typo correction acknowledgment ONLY if:
    # 1. The correction was accepted (city_normalized is not None)
    # 2. This correction hasn't been shown before in this session
    if analysis.has_typo_correction and analysis.city_normalized:
        original, corrected = analysis.typo_correction
        correction_key = f"{original.lower()}->{corrected.lower()}"

        # Check if this correction was already shown in this session
        should_show = True
        if session_id and correction_tracker is not None:
            if session_id not in correction_tracker:
                correction_tracker[session_id] = set()
            elif correction_key in correction_tracker[session_id]:
                should_show = False  # Already shown this correction
                logger.info(f"[CORRECTION-SKIP] Already shown '{correction_key}' in session {session_id[:8]}")

            if should_show:
                # Track this correction
                correction_tracker[session_id].add(correction_key)

        if should_show:
            ack = TYPO_ACKNOWLEDGMENTS.get(language, TYPO_ACKNOWLEDGMENTS["en"])
            prefix_parts.append(ack.format(original=original, corrected=corrected))

    return "".join(prefix_parts)


def build_filter_description(filters: Dict[str, Any], language: str) -> str:
    """Build human-readable filter description.

    Args:
        filters: Applied filters dict
        language: Target language

    Returns:
        Filter description string
    """
    templates = FILTER_DESC_TEMPLATES.get(language, FILTER_DESC_TEMPLATES["en"])
    parts = []

    if filters.get("city"):
        parts.append(templates["city"].format(value=filters["city"]))

    if filters.get("month"):
        month_num = filters["month"]
        month_names = MONTH_NAMES.get(language, MONTH_NAMES["en"])
        if 1 <= month_num <= 12:
            parts.append(templates["month"].format(value=month_names[month_num]))

    if filters.get("category"):
        parts.append(templates["category"].format(value=filters["category"]))

    return "".join(parts)


def build_statistical_response(
    count: int,
    filters: Dict[str, Any],
    category_breakdown: Dict[str, int],
    language: str
) -> str:
    """Build statistical response when count/how many dimension detected.

    Args:
        count: Total event count
        filters: Applied filters
        category_breakdown: Event counts by category
        language: Target language

    Returns:
        Complete statistical response
    """
    template = STATISTICAL_TEMPLATES.get(language, STATISTICAL_TEMPLATES["en"])
    filters_desc = build_filter_description(filters, language)

    # Build category breakdown
    breakdown_lines = []
    for category, cat_count in sorted(category_breakdown.items(), key=lambda x: -x[1]):
        if cat_count > 0:
            breakdown_lines.append(f"- **{category}**: {cat_count}")

    event_breakdown = "\n".join(breakdown_lines) if breakdown_lines else ""

    return template.format(
        count=count,
        filters_desc=filters_desc,
        event_breakdown=event_breakdown
    )

# No hardcoded out-of-scope list needed - we use the database as the source of truth.
# If a city is in our database, it's in scope. Everything else is out of scope.

# ========================================
# DEFAULT TIMEFRAME & REFINEMENT SUGGESTIONS
# ========================================
# When user doesn't specify a timeframe, we default to "upcoming events" (next 30 days)
# and invite them to refine their search with available filters

DEFAULT_TIMEFRAME_DAYS = 30  # Default to next 30 days when no timeframe specified

# Default timeframe notice (added when we auto-apply the default)
DEFAULT_TIMEFRAME_NOTICE = {
    "fr": "\n\n📅 *Résultats filtrés sur les **30 prochains jours**.*",
    "en": "\n\n📅 *Results filtered to the **next 30 days**.*"
}

# Refinement suggestions (invite user to refine their search)
REFINEMENT_SUGGESTIONS = {
    "fr": """

---
💡 **Affiner votre recherche ?** Vous pouvez préciser :
- 📆 Une **date** ou **période** (ex: "ce week-end", "en février")
- 🎫 **Événements gratuits** (ex: "gratuit", "entrée libre")
- 👨‍👩‍👧 **Public cible** (ex: "pour enfants", "en famille")
- 🎭 **Type d'événement** (ex: "concerts", "expositions", "théâtre")""",
    "en": """

---
💡 **Want to refine your search?** You can specify:
- 📆 A **date** or **period** (e.g., "this weekend", "in February")
- 🎫 **Free events** (e.g., "free", "no charge")
- 👨‍👩‍👧 **Target audience** (e.g., "for kids", "family-friendly")
- 🎭 **Event type** (e.g., "concerts", "exhibitions", "theater")"""
}

# Shorter refinement hint for when results are found (less intrusive)
REFINEMENT_HINT = {
    "fr": "\n\n💡 *Précisez une date, un type d'événement, ou \"gratuit\" pour affiner.*",
    "en": "\n\n💡 *Specify a date, event type, or \"free\" to refine your search.*"
}

# Broadening suggestion when < 8 results
BROADENING_SUGGESTION = {
    "fr": "\n\n💡 *Peu de résultats ? Essayez d'élargir votre recherche : changez la date, la ville, ou simplifiez vos critères.*",
    "en": "\n\n💡 *Few results? Try broadening your search: change the date, city, or simplify your criteria.*"
}


def build_filter_echo(filters: Dict[str, Any], search_terms: List[str], language: str) -> str:
    """Build a summary of applied filters and search terms for transparency.

    Args:
        filters: Applied filters (city, month, day, category, audience, etc.)
        search_terms: Accumulated search query terms
        language: Target language (fr/en)

    Returns:
        Formatted string showing what filters were used
    """
    parts = []

    # Structured filters
    filter_items = []
    if filters.get("city"):
        filter_items.append(f"📍 {filters['city']}")
    if filters.get("month"):
        month_names_en = ["", "January", "February", "March", "April", "May", "June",
                         "July", "August", "September", "October", "November", "December"]
        month_names_fr = ["", "janvier", "février", "mars", "avril", "mai", "juin",
                         "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
        month_num = filters["month"]
        if 1 <= month_num <= 12:
            month_name = month_names_fr[month_num] if language == "fr" else month_names_en[month_num]
            if filters.get("day"):
                days = filters["day"]
                if isinstance(days, list):
                    filter_items.append(f"📅 {days[0]}-{days[-1]} {month_name}")
                else:
                    filter_items.append(f"📅 {days} {month_name}")
            else:
                filter_items.append(f"📅 {month_name}")
    if filters.get("category"):
        filter_items.append(f"🎭 {filters['category']}")
    if filters.get("audience"):
        filter_items.append(f"👥 {filters['audience']}")
    if filters.get("is_free"):
        filter_items.append("🎫 " + ("gratuit" if language == "fr" else "free"))

    # Search terms (accumulated text queries)
    if search_terms:
        terms_str = " + ".join([f'"{t}"' for t in search_terms])
        filter_items.append(f"🔍 {terms_str}")

    if filter_items:
        header = "**Filtres appliqués:**" if language == "fr" else "**Applied filters:**"
        parts.append(f"\n\n---\n{header} {' | '.join(filter_items)}")

    return "".join(parts)


def should_apply_default_timeframe(filters: Dict[str, Any]) -> bool:
    """Check if we should apply the default timeframe.

    Returns True if no timeframe was specified by the user.
    """
    has_month = filters.get("month") is not None
    has_day = filters.get("day") is not None
    has_year = filters.get("year") is not None
    return not (has_month or has_day or has_year)


def apply_default_timeframe(filters: Dict[str, Any]) -> Dict[str, Any]:
    """Apply default timeframe (next 30 days) if none specified.

    Args:
        filters: Current filters dict

    Returns:
        Updated filters with default timeframe applied
    """
    from datetime import date, timedelta

    if should_apply_default_timeframe(filters):
        today = date.today()
        # Set filter to current month (as a simple approach)
        # The retrieval will handle date-based filtering
        filters = filters.copy()
        filters["_default_timeframe_applied"] = True
        filters["_timeframe_start"] = today.isoformat()
        filters["_timeframe_end"] = (today + timedelta(days=DEFAULT_TIMEFRAME_DAYS)).isoformat()
        logger.info(f"[DEFAULT-TIMEFRAME] Applied default: {today} to {today + timedelta(days=DEFAULT_TIMEFRAME_DAYS)}")
    return filters


def build_refinement_suffix(
    filters: Dict[str, Any],
    has_results: bool,
    language: str
) -> str:
    """Build refinement suggestion suffix based on what filters are already applied.

    Args:
        filters: Applied filters
        has_results: Whether the search returned results
        language: Target language

    Returns:
        Refinement suggestion string
    """
    suffix_parts = []

    # Add default timeframe notice if it was applied
    if filters.get("_default_timeframe_applied"):
        suffix_parts.append(DEFAULT_TIMEFRAME_NOTICE.get(language, DEFAULT_TIMEFRAME_NOTICE["en"]))

    # Add refinement suggestions
    # Use shorter hint if results found, full suggestions if no results
    if has_results:
        suffix_parts.append(REFINEMENT_HINT.get(language, REFINEMENT_HINT["en"]))
    else:
        suffix_parts.append(REFINEMENT_SUGGESTIONS.get(language, REFINEMENT_SUGGESTIONS["en"]))

    return "".join(suffix_parts)


def detect_language_from_query(query: str) -> str:
    """Detect language from query (simple heuristic)."""
    french_indicators = ["bonjour", "salut", "coucou", "merci", "s'il", "qu'est", "evenement", "cherche", "trouve", "veux", "peux"]
    query_lower = query.lower()
    french_count = sum(1 for word in french_indicators if word in query_lower)
    return "fr" if french_count >= 1 else "en"


def detect_out_of_scope_city(query: str) -> tuple[Optional[str], Optional[str]]:
    """Detect if query mentions a city outside Ile-de-France scope.

    Uses the database as the source of truth: if a city is in our database,
    it's in scope. Everything else is out of scope.

    OPTIMIZATION: Now includes fuzzy matching (Levenshtein) to suggest corrections
    for typos like "Possy" → "Poissy" before marking as out-of-scope.

    Args:
        query: The user query

    Returns:
        Tuple of (out_of_scope_city, suggested_city):
        - (None, None): City is in scope OR no city detected
        - ("Delhi", None): City is out of scope with no suggestion
        - ("Possy", "Poissy"): Typo detected, suggestion available
    """
    city_locator = get_city_locator()
    known_cities = set(city_locator.city_cache.keys())

    # Check for explicit "in <city>" or "a <city>" patterns
    location_patterns = [
        r"\bin\s+([A-Za-zÀ-ÿ\-]+)",  # "in Montreal"
        r"\ba\s+([A-Za-zÀ-ÿ\-]+)",   # "a Montreal" (French)
        r"\bà\s+([A-Za-zÀ-ÿ\-]+)",   # "à Montreal"
        r"\bat\s+([A-Za-zÀ-ÿ\-]+)",  # "at Montreal"
    ]

    for pattern in location_patterns:
        match = re.search(pattern, query, re.IGNORECASE)
        if match:
            potential_city = match.group(1).lower().strip()
            # Skip common words that aren't cities
            skip_words = {
                # Articles and determiners (English)
                "the", "a", "an", "this", "that", "my", "your", "some", "any",
                # Articles and determiners (French)
                "le", "la", "les", "un", "une", "des", "ce", "cette", "mon", "ma",
                # Question words and pronouns (CRITICAL: prevent "which" -> city)
                "which", "what", "how", "why", "when", "where", "who", "whom",
                "way", "order", "case", "fact", "general", "particular", "addition",
                # Common nouns that appear after "in/a" (CRITICAL: prevent "events" -> city)
                "event", "events", "evenement", "evenements", "thing", "things",
                "place", "places", "area", "areas", "town", "towns", "city", "cities",
                "time", "times", "day", "days", "week", "weeks", "month", "months",
                "morning", "afternoon", "evening", "night", "weekend", "weekends",
                # Common event-related adjectives/nouns that appear after "a/in"
                "cultural", "culturel", "culturelle", "music", "musical", "musicale",
                "art", "artistic", "artistique", "jazz", "rock", "pop", "classical",
                "classique", "traditional", "traditionnel", "traditionnelle",
                "contemporary", "contemporain", "contemporaine", "modern", "moderne",
                "free", "gratuit", "gratuite", "public", "publique", "private", "prive",
                "local", "locale", "national", "nationale", "international", "internationale",
                "live", "outdoor", "indoor", "virtual", "virtuel", "virtuelle",
                "family", "familial", "familiale", "kid", "kids", "children", "enfant", "enfants",
                "few", "many", "much", "little", "lot", "bit", "moment", "while",
                "new", "nouveau", "nouvelle", "old", "ancien", "ancienne",
                "great", "good", "nice", "beautiful", "beau", "belle",
                "special", "spécial", "speciale", "unique", "rare",
                "professional", "professionnel", "professionnelle", "corporate",
                # Event types that shouldn't be cities
                "concert", "concerts", "exposition", "expositions", "expo", "expos",
                "festival", "festivals", "spectacle", "spectacles", "show", "shows",
                "theatre", "theater", "théâtre", "opera", "opéra", "ballet", "dance", "danse",
                "exhibition", "exhibitions", "performance", "performances",
                "workshop", "workshops", "atelier", "ateliers",
            }

            # Skip region-related words that aren't cities
            # Prevents "Ile de France" from being parsed as city "Ile"
            region_words = {
                "ile", "île", "france", "region", "région", "idf",
                "île-de-france", "ile-de-france", "iledefrance",
            }

            if potential_city in region_words:
                continue

            # Skip date-related words (months, days, time indicators)
            # These are often falsely detected as cities in queries like "events in April"
            date_words = {
                # Months (English)
                "january", "february", "march", "april", "may", "june",
                "july", "august", "september", "october", "november", "december",
                # Months (French)
                "janvier", "février", "fevrier", "mars", "avril", "mai", "juin",
                "juillet", "août", "aout", "septembre", "octobre", "novembre", "décembre", "decembre",
                # Days (English)
                "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
                # Days (French)
                "lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche",
                # Time indicators
                "today", "tomorrow", "yesterday", "morning", "afternoon", "evening", "night",
                "aujourd'hui", "demain", "hier", "matin", "après-midi", "soir", "nuit",
                # Relative time
                "week", "weekend", "week-end", "month", "year", "semaine", "mois", "année", "annee"
            }

            if potential_city in skip_words or potential_city in date_words:
                continue
            # If it looks like a city name but is NOT in our database, check further
            if len(potential_city) > 2 and potential_city not in known_cities:
                # Check partial matches - but be strict to avoid false positives
                # Only match if the known city is a PREFIX of the query term (e.g., "paris 15" → "paris")
                # Or if the query term exactly equals a known city
                is_partial_match = False
                for kc in known_cities:
                    # Only allow: "paris" matches "paris 15" (kc is prefix of potential_city)
                    if potential_city.startswith(kc) and len(potential_city) <= len(kc) + 5:
                        is_partial_match = True
                        break
                    # Also allow: query is Paris and we check "paris 15eme" → match
                    if kc.startswith(potential_city) and len(kc) <= len(potential_city) + 10:
                        is_partial_match = True
                        break

                if not is_partial_match:
                    # OPTIMIZATION: Try fuzzy matching BEFORE marking as out-of-scope
                    # This catches typos like "Possy" → "Poissy", "Versaille" → "Versailles"
                    fuzzy_match = city_locator.find_closest_city(potential_city, threshold=0.75)
                    if fuzzy_match:
                        logger.info(f"[EARLY-FUZZY] Typo detected: '{potential_city}' → suggested: '{fuzzy_match}'")
                        return (potential_city.title(), fuzzy_match.title())

                    # No fuzzy match found - truly out of scope
                    logger.debug(f"Detected out-of-scope city: {potential_city}")
                    return (potential_city.title(), None)

    return (None, None)




class SimpleSummaryBufferMemory:
    """Custom implementation of Summary Buffer Memory with actual LLM summarization."""
    
    def __init__(self, llm, chat_memory, max_token_limit=1000, memory_key="chat_history"):
        self.llm = llm
        self.chat_memory = chat_memory
        self.max_token_limit = max_token_limit
        self.memory_key = memory_key
        self.summary_key = "history_summary"
        
    def load_memory_variables(self, inputs: Dict[str, Any]) -> Dict[str, List[BaseMessage]]:
        """Load history, summarizing older messages if the list is too long."""
        all_messages = self.chat_memory.messages
        
        if len(all_messages) > 10:
            to_summarize = all_messages[:-10]
            to_keep = all_messages[-10:]
            history_str = "\n".join([f"{m.type}: {m.content}" for m in to_summarize])
            
            try:
                summary_prompt = f"Summarize the key facts and user preferences from this cultural events chat history in 2-3 sentences:\n\n{history_str}"
                summary = self.llm.invoke(summary_prompt).content
                context_message = SystemMessage(content=f"Summary of previous conversation: {summary}")
                return {self.memory_key: [context_message] + to_keep}
            except Exception as e:
                logger.warning(f"Summarization failed: {e}")
                return {self.memory_key: all_messages[-20:]}
            
        return {self.memory_key: all_messages}

    def save_context(self, inputs: Dict[str, Any], outputs: Dict[str, str]) -> None:
        pass


class RAGChain:
    """Orchestrator for the Cultural Events RAG system with Summary Buffer Memory."""

    def __init__(
        self,
        vector_store: EventVectorStore | None = None,
        llm: MistralLLM | None = None,
        k: int = 8,
        chat_storage: ChatStorage | None = None,
        enable_cache: bool = True,
        cache_ttl_minutes: int = 60,
    ) -> None:
        """Initialize the RAG chain."""
        self.vector_store = vector_store or EventVectorStore()
        # OPTIMIZATION D: Lazy initialization - delay index loading until first query
        self._index_loaded = False

        # Use get_chat_llm() to respect llm_backend setting (mistral/google/huggingface)
        from src.generation.llm import get_chat_llm, MistralLLM
        raw_llm = llm or get_chat_llm()
        # Wrap in MistralLLM for consistent interface (it expects self.llm.llm pattern)
        if isinstance(raw_llm, MistralLLM):
            self.llm = raw_llm
        else:
            # Create a simple wrapper to provide consistent interface
            self.llm = type('LLMWrapper', (), {'llm': raw_llm, 'invoke': raw_llm.invoke})()
        self.chat_storage = chat_storage or ChatStorage()
        self.k = k

        # Initialize deterministic retrieval manager
        self.retrieval_manager = RetrievalManager(self.vector_store, k=k)

        self.cache = QueryCache(ttl_minutes=cache_ttl_minutes) if enable_cache else None

        # SESSION FILTER CACHE: Store last analysis filters per session for follow-up merging
        # This enables code-level filter preservation instead of relying on LLM to re-interpret
        self._session_filters: Dict[str, Dict[str, Any]] = {}

        # SESSION CORRECTION TRACKER: Track which typo corrections have been shown per session
        # to avoid repeating "I assume you mean X" messages
        self._session_corrections: Dict[str, Set[str]] = {}  # {session_id: {correction_key}}

        try:
            total_events_val = self.vector_store.storage.count_events()
            min_date, max_date = self.vector_store.storage.get_date_range()
            date_range_val = f"{min_date.strftime('%Y-%m-%d') if min_date else '?'} to {max_date.strftime('%Y-%m-%d') if max_date else '?'}"
        except:
            total_events_val = "Unknown"
            date_range_val = "Unknown"

        # CRITICAL: Use dynamic date, not hardcoded
        from datetime import date
        current_date_val = date.today().strftime("%Y-%m-%d")

        # 1. Prepare Inputs - Now just passes through (no separate reformulation call)
        # Also passes through pre-computed filters from unified analyzer if available
        def prepare_inputs(inputs):
            history = inputs.get("chat_history", [])
            q = inputs["input"]
            return {
                "q": q,
                "raw_q": q,
                "history": history,
                "pre_filters": inputs.get("pre_filters"),
                "pre_refined_query": inputs.get("pre_refined_query")
            }

        # 2. Hybrid Retrieval with pre-computed filters from UnifiedAnalyzer
        # ARCHITECTURE: UnifiedAnalyzer runs BEFORE this, providing filters via pre_filters
        def retrieve_docs_hybrid(inputs):
            input_query = inputs["q"]
            raw_query = inputs["raw_q"]
            history = inputs["history"]

            # Get pre-computed filters from UnifiedAnalyzer (always provided in normal flow)
            pre_filters = inputs.get("pre_filters")
            pre_refined_query = inputs.get("pre_refined_query")

            try:
                # Use pre-computed filters from UnifiedAnalyzer
                refined_query = pre_refined_query or input_query
                raw_filters = pre_filters or {}
                logger.info(f"[RETRIEVAL] Using filters from UnifiedAnalyzer")

                logger.info(f"[UNIFIED] Query: '{input_query}' -> Refined: '{refined_query}' | Filters: {raw_filters}")

                # Parse intent from filters
                intent = self.retrieval_manager.parse_intent(raw_filters)

                # Execute Multi-Stage Search
                result = self.retrieval_manager.execute_search(refined_query, intent)

                return {
                    "docs": result["docs"],
                    "filters": raw_filters,
                    "actual_k": result["total_count"],
                    "total_in_database": result.get("total_in_database", result["total_count"]),
                    "filters_applied": result.get("filters_applied", {}),
                    "exact_count": result.get("exact_count", 0)
                }
            except Exception as e:
                logger.error(f"Unified retrieval failed: {e}", exc_info=True)
                return {"docs": [], "filters": {}, "actual_k": 0, "exact_count": 0}

        def format_docs(docs, filters):
            if not docs:
                return "NO RELEVANT EVENTS FOUND.", 0
            
            formatted = []
            system_notes = []
            source_num = 1
            for doc in docs:
                meta = doc.metadata
                if "nearby_date_note" in meta:
                    system_notes.append(meta["nearby_date_note"])
                if meta.get("match_type") == "System": continue
                
                header = f"=== SOURCE {source_num} (Title: {meta.get('title')}, City: {meta.get('city')}, Date: {meta.get('start_date')}, Match: {meta.get('match_type')}, Distance: {meta.get('distance_km', 0):.1f}km) ==="
                formatted.append(f"{header}\n{doc.page_content}")
                source_num += 1
            
            final_text = ""
            if system_notes:
                final_text += "SYSTEM NOTES:\n" + "\n".join(set(system_notes)) + "\n\n"
            final_text += "\n\n".join(formatted)
            return final_text, len(formatted)

        # 3. Chain Construction
        def select_prompt(x):
            """Select language-specific prompt based on input language parameter."""
            lang = x.get("language", "fr")  # Default to French
            return get_rag_prompt(language=lang)

        self.rag_chain = (
            RunnablePassthrough.assign(
                retrieved_data=RunnableLambda(prepare_inputs) | retrieve_docs_hybrid,
                total_events=lambda _: str(total_events_val),
                date_range=lambda _: date_range_val,
                current_date=lambda _: current_date_val
            )
            .assign(
                formatting_results=lambda x: format_docs(x["retrieved_data"]["docs"], x["retrieved_data"]["filters"])
            )
            .assign(
                answer=(
                    RunnablePassthrough.assign(
                        context=lambda x: x["formatting_results"][0],
                        k=lambda x: str(x["formatting_results"][1]),
                        today=lambda x: x["current_date"],
                        total_matching=lambda x: str(x["retrieved_data"].get("total_in_database", x["formatting_results"][1])),
                        filters_applied=lambda x: str(x["retrieved_data"].get("filters_applied", {})),
                        exact_count=lambda x: str(min(x["retrieved_data"].get("exact_count", 0), x["formatting_results"][1])),
                        nearby_count=lambda x: str(max(0, x["formatting_results"][1] - x["retrieved_data"].get("exact_count", 0)))
                    )
                    | RunnableLambda(select_prompt)
                    | self.llm.llm
                    | RobustJsonParser()
                ),
                context=lambda x: x["retrieved_data"]["docs"]
            )
        )

    def _get_memory(self, session_id: str) -> SimpleSummaryBufferMemory:
        chat_memory = SQLiteChatMessageHistory(session_id=session_id, storage=self.chat_storage)
        return SimpleSummaryBufferMemory(llm=self.llm.llm, chat_memory=chat_memory)

    def _get_previous_events(self, session_id: str) -> list[dict] | None:
        """Extract retrieved events from the most recent assistant message.

        Args:
            session_id: Session identifier

        Returns:
            List of event dicts from the last assistant message, or None
        """
        try:
            history = self.chat_storage.get_chat_history(session_id, limit=10)
            # Find the most recent assistant message with retrieved_events
            for entry in reversed(history):
                if entry["role"] == "assistant" and entry.get("retrieved_events"):
                    return entry["retrieved_events"]
            return None
        except Exception as e:
            logger.warning(f"Failed to extract previous events: {e}")
            return None

    def _store_session_filters(self, session_id: str, filters: Dict[str, Any], refined_query: str = None) -> None:
        """Store filters and refined_query from this turn for follow-up query merging.

        Args:
            session_id: The session identifier
            filters: The extracted filters to store
            refined_query: The refined search query text (may be accumulated from previous)
        """
        # Store a copy to avoid mutation issues
        stored = {
            k: v for k, v in filters.items()
            if v is not None and not k.startswith("_")  # Exclude None and internal keys
        }

        # Preserve the accumulated search terms from merged filters
        if "_search_terms" in filters:
            stored["_search_terms"] = filters["_search_terms"]
        elif refined_query:
            # First turn - just the single query
            stored["_search_terms"] = [refined_query]

        self._session_filters[session_id] = stored
        filters_only = {k: v for k, v in stored.items() if not k.startswith('_')}
        logger.info(f"[SESSION-FILTERS] Stored for {session_id}: filters={filters_only}, search_terms={stored.get('_search_terms', [])}")

    def _merge_with_previous_filters(
        self,
        session_id: str,
        current_filters: Dict[str, Any],
        current_refined_query: str = None,
        analysis: "UnifiedAnalysisResult" = None
    ) -> Tuple[Dict[str, Any], str]:
        """Merge current filters with previous session filters and accumulate search terms.

        For follow-up queries, this preserves filters that weren't explicitly changed
        and accumulates search terms across turns.

        SMART CLEARING RULES:
        - If user says "any kind of event" (scope=all), DON'T carry over category
        - If user specifies a new month, DON'T carry over the day from previous month
        - If user specifies a new date range, clear previous single-day filters

        Args:
            session_id: The session identifier
            current_filters: Filters extracted from current query
            current_refined_query: Current turn's refined query text
            analysis: The UnifiedAnalysisResult for smart filter clearing

        Returns:
            Tuple of (merged_filters, accumulated_search_query)
        """
        previous = self._session_filters.get(session_id, {})
        if not previous:
            return current_filters, current_refined_query

        merged = current_filters.copy()
        carried_over = []
        cleared = []

        # ========================================
        # SMART CLEARING RULES
        # ========================================

        # Rule 1: If scope="all" (any kind of event), DON'T carry over category
        wants_all_events = False
        if analysis and hasattr(analysis, 'wants_all_events'):
            wants_all_events = analysis.wants_all_events
            if wants_all_events:
                cleared.append("category (scope=all)")
                logger.info(f"[FILTER-CLEAR] User wants all events - NOT carrying over category")

        # Rule 2: If user specifies a new month, DON'T carry over day
        # (e.g., "in February" should clear day=18 from March)
        month_changed = (
            merged.get("month") is not None and
            previous.get("month") is not None and
            merged.get("month") != previous.get("month")
        )
        if month_changed:
            cleared.append(f"day (month changed from {previous.get('month')} to {merged.get('month')})")
            logger.info(f"[FILTER-CLEAR] Month changed - NOT carrying over day")

        # Only carry over if current value is None, previous has a value,
        # AND smart clearing rules allow it
        for key in ["city", "month", "day", "year", "category", "audience"]:
            # Skip keys that should be cleared
            if key == "category" and wants_all_events:
                continue  # Don't carry over category when user wants all events
            if key == "day" and month_changed:
                continue  # Don't carry over day when month changed

            if merged.get(key) is None and previous.get(key) is not None:
                merged[key] = previous[key]
                carried_over.append(f"{key}={previous[key]}")

        if carried_over:
            logger.info(f"[FILTER-MERGE] Carried over from previous: {', '.join(carried_over)}")
        if cleared:
            logger.info(f"[FILTER-CLEAR] Smart clearing applied: {', '.join(cleared)}")

        # Accumulate search terms (individual terms, not combined strings)
        previous_terms = previous.get("_search_terms", [])

        # Build the list of all individual search terms
        if current_refined_query and current_refined_query not in previous_terms:
            all_terms = previous_terms + [current_refined_query]
        else:
            all_terms = previous_terms

        # Create combined search query for semantic search
        if len(all_terms) > 1:
            accumulated_query = " OR ".join(all_terms)
            logger.info(f"[QUERY-MERGE] Accumulated search terms: {all_terms}")
        elif all_terms:
            accumulated_query = all_terms[0]
        else:
            accumulated_query = current_refined_query or ""

        # Store the individual terms (not the combined string) in merged filters
        merged["_search_terms"] = all_terms

        return merged, accumulated_query

    def _ensure_ready(self) -> None:
        """OPTIMIZATION D: Lazy initialization - load index on first query."""
        if not self._index_loaded:
            try:
                self.vector_store.load_index()
                self._index_loaded = True
                logger.info("FAISS index loaded (lazy initialization)")
            except Exception as e:
                logger.warning(f"Could not load FAISS index: {e}.")

    def _unified_pre_analysis(self, question: str, chat_history: List[BaseMessage], language: str, session_id: str = None) -> Optional[Dict[str, Any]]:
        """Use unified LLM analyzer for MULTI-DIMENSIONAL intent analysis.

        This performs multi-dimensional classification where a query can have
        multiple classifications that compose into a single response:
        - Greeting dimension (prefix added to response)
        - Typo correction dimension (acknowledgment added)
        - Statistical dimension (changes output to count instead of list)
        - Scope dimension (all events vs specific type)

        Args:
            question: User's query
            chat_history: Previous conversation turns
            language: Detected/specified language
            session_id: Session ID to check for existing filters (enables follow-up handling)

        Returns:
            Dict with early response if query is special/incomplete, None to continue RAG
        """
        try:
            # Get known cities for normalization
            city_locator = get_city_locator()
            known_cities = list(city_locator.city_cache.keys())

            # Extract previous events from chat history for coreference resolution
            previous_events = None
            if session_id:
                previous_events = self._get_previous_events(session_id)
                if previous_events:
                    logger.info(f"[COREFERENCE] Found {len(previous_events)} events from previous turn")

            # ONE unified LLM call with multi-dimensional output
            analysis = unified_analyze(question, chat_history, known_cities, previous_events=previous_events)

            # CRITICAL: Update language from analysis IMMEDIATELY (before any early returns)
            # This ensures all responses use the correct detected language
            detected_lang = getattr(analysis, 'detected_language', language)
            if detected_lang in ["fr", "en"]:
                language = detected_lang
                logger.info(f"[LANGUAGE] Updated from LLM analysis: {language}")

            # Log dimensions
            dims_str = ", ".join([
                f"{k}={v.detected}" for k, v in analysis.dimensions.items() if v.detected
            ]) or "none"
            logger.info(
                f"[MULTI-DIM] intent={analysis.intent.value}, "
                f"city={analysis.city_normalized}, "
                f"complete={analysis.is_complete}, "
                f"dims=[{dims_str}]"
            )

            # ========================================
            # PURE NON-EVENT INTENTS (no event search component)
            # ========================================
            # Handle pure greeting, chitchat, capability, abuse, off_topic
            # EXCEPTION: If greeting dimension + event_search intent, continue to RAG
            if analysis.intent != UnifiedIntent.EVENT_SEARCH and analysis.intent_confidence >= 0.7:
                # Pure non-event intent (not a compound query like "hello, find me concerts")
                # CRITICAL: Use detected_language from analysis (not fallback language parameter)
                detected_lang = getattr(analysis, 'detected_language', language)
                if detected_lang not in ["fr", "en"]:
                    detected_lang = "fr"  # Normalize to valid values

                response_map = {
                    UnifiedIntent.GREETING: GREETING_RESPONSES,
                    UnifiedIntent.CHITCHAT: CHITCHAT_RESPONSES,
                    UnifiedIntent.CAPABILITY: CAPABILITY_RESPONSES,
                    UnifiedIntent.DIRECTIONS: DIRECTIONS_RESPONSES,
                    UnifiedIntent.ABUSE: ABUSE_RESPONSES,
                    UnifiedIntent.OFF_TOPIC: OFF_TOPIC_RESPONSES,
                }
                responses = response_map.get(analysis.intent, OFF_TOPIC_RESPONSES)
                logger.info(f"[LANGUAGE] Early response using detected_language: {detected_lang}")
                return {
                    "early_response": responses[detected_lang],
                    "query_type": analysis.intent.value,
                    "analysis": analysis
                }

            # ========================================
            # OUT-OF-SCOPE CITY
            # ========================================
            if analysis.city and not analysis.city_normalized:
                # Use detected language from analysis
                detected_lang = getattr(analysis, 'detected_language', language)
                if detected_lang not in ["fr", "en"]:
                    detected_lang = "fr"

                # Build response prefix for dimensions
                prefix = compose_response_prefix(analysis, detected_lang)

                if detected_lang == "fr":
                    response = prefix + OUT_OF_SCOPE_CITY_RESPONSES["fr"].format(city=analysis.city.title())
                else:
                    response = prefix + OUT_OF_SCOPE_CITY_RESPONSES["en"].format(city=analysis.city.title())
                return {
                    "early_response": response,
                    "query_type": "out_of_scope_city",
                    "analysis": analysis
                }

            # ========================================
            # STATISTICAL QUERIES (how many, count, total)
            # ========================================
            # Statistical queries with city are COMPLETE - proceed to RAG with special handling
            if analysis.is_statistical:
                logger.info("[MULTI-DIM] Statistical query detected - will return count")
                # Continue to RAG but flag for statistical output
                return {
                    "continue_rag": True,
                    "is_statistical": True,
                    "filters": analysis.filters,
                    "refined_query": analysis.refined_query,
                    "analysis": analysis,
                    "response_prefix": compose_response_prefix(analysis, language)
                }

            # ========================================
            # RATE LIMIT EXHAUSTED - TEMPORARY ERROR
            # ========================================
            # If the analyzer failed due to rate limiting (after all retries),
            # show a clear message instead of asking for clarification
            if analysis.raw_response.get("error") == "rate_limit_exhausted":
                rate_limit_messages = {
                    "fr": (
                        "**Erreur API : Limite de requetes atteinte**\n\n"
                        "Le service d'intelligence artificielle est temporairement indisponible "
                        "(trop de requetes). Veuillez patienter 30 secondes avant de reessayer."
                    ),
                    "en": (
                        "**API Error: Rate limit reached**\n\n"
                        "The AI service is temporarily unavailable (too many requests). "
                        "Please wait 30 seconds before trying again."
                    )
                }
                return {
                    "early_response": rate_limit_messages.get(language, rate_limit_messages["en"]),
                    "query_type": "rate_limit_error",
                    "analysis": analysis
                }

            # ========================================
            # INCOMPLETE QUERIES (need clarification)
            # ========================================
            # CRITICAL: Statistical and "all events" scope queries skip this check
            # ALSO CRITICAL: If session has existing filters, this is a follow-up query
            # that will have context merged - don't ask for clarification
            has_session_context = session_id and bool(self._session_filters.get(session_id))

            if not analysis.is_complete and analysis.missing_criteria and not has_session_context:
                from src.retrieval.clarifications import get_clarification_response
                # Convert missing to format expected by clarifications
                reason = "missing_" + "+".join(analysis.missing_criteria)
                backup_prefix, backup_questions = get_clarification_response(reason, language)

                if backup_prefix and backup_questions:
                    # Build response prefix for dimensions (greeting, typo acknowledgment)
                    dim_prefix = compose_response_prefix(analysis, language)
                    questions_text = "\n".join([f"- {q}" for q in backup_questions])
                    answer_text = f"{dim_prefix}{backup_prefix}{questions_text}"

                    # CRITICAL FIX: Store partial filters for follow-up query merging
                    # Without this, user's clarification response would be treated as new standalone query
                    if session_id and (analysis.filters or analysis.refined_query):
                        self._store_session_filters(
                            session_id,
                            analysis.filters or {},
                            analysis.refined_query
                        )
                        logger.info(f"[CLARIFICATION] Stored partial context for follow-up: filters={analysis.filters}")

                    return {
                        "early_response": answer_text,
                        "query_type": "broad_query",
                        "needs_clarification": True,
                        "clarifying_questions": backup_questions,
                        "analysis": analysis
                    }
            elif has_session_context and not analysis.is_complete:
                logger.info(f"[FOLLOW-UP] Query incomplete but session has context - continuing to RAG with filter merge")

            # ========================================
            # VALID EVENT SEARCH - CONTINUE TO RAG
            # ========================================
            # Build response prefix for dimensions (greeting, typo acknowledgment)
            response_prefix = compose_response_prefix(analysis, language)

            return {
                "continue_rag": True,
                "is_statistical": False,
                "filters": analysis.filters,
                "refined_query": analysis.refined_query,
                "analysis": analysis,
                "response_prefix": response_prefix
            }

        except Exception as e:
            logger.error(f"[MULTI-DIM] Analysis failed: {e}. Falling back to keyword-based flow.")
            return None  # Fallback to old keyword-based flow

    def query(self, question: str, session_id: str = "default_session") -> str:
        """Simple wrapper for backward compatibility."""
        result = self.query_with_metadata(question, session_id)
        return result["answer"]

    def query_with_metadata(self, question: str, session_id: str = "default_session", language: str = None) -> Dict[str, Any]:
        # OPTIMIZATION D: Ensure index is loaded (lazy init on first query)
        self._ensure_ready()

        logger.info(f"Query: {question}")
        check_safety(question, session_id=session_id)

        # Track if language was explicitly provided vs auto-detected
        language_explicit = language is not None

        # Temporary fallback to French (will be overridden by unified analyzer if used)
        if language is None:
            language = "fr"  # Default to French, will be updated by unified analyzer

        # Cache check - labels are now pre-computed in database, no enrichment needed
        if self.cache:
            cached = self.cache.get(question, session_id)
            if cached:
                logger.debug(f"[CACHE] Returning cached response")
                return cached

        memory = self._get_memory(session_id)
        chat_history = memory.load_memory_variables({})["chat_history"]

        # ========================================
        # UNIFIED LLM ANALYZER
        # ========================================
        # Single LLM call for:
        # - Intent classification (greeting, chitchat, event_search, etc.)
        # - Entity extraction (city, event_type, date)
        # - City normalization (Plessis → Le Plessis-Robinson)
        # - Query completeness check
        # - Filter extraction
        unified_result = None
        if USE_UNIFIED_ANALYZER:
            unified_result = self._unified_pre_analysis(question, chat_history, language, session_id)

            # Update language from unified analyzer if not explicitly provided
            if unified_result and not language_explicit:
                analysis = unified_result.get("analysis")
                if analysis and hasattr(analysis, "detected_language"):
                    language = analysis.detected_language
                    logger.info(f"[LANGUAGE] Using LLM-detected language: {language}")

            if unified_result:
                # Handle early responses (greeting, chitchat, out-of-scope, incomplete)
                if "early_response" in unified_result:
                    response_text = unified_result["early_response"]
                    query_type = unified_result.get("query_type", "special")
                    logger.info(f"[UNIFIED] Early response: {query_type}")

                    _background_db_write(self.chat_storage.add_chat_message, session_id, "user", question)
                    message_id = self.chat_storage.add_chat_message(session_id, "assistant", response_text)

                    result_dict = {
                        "answer": response_text,
                        "sources": [],
                        "structured_events": [],
                        "message_id": message_id,
                        "query_type": query_type
                    }
                    if unified_result.get("needs_clarification"):
                        result_dict["needs_clarification"] = True
                        result_dict["clarifying_questions"] = unified_result.get("clarifying_questions", [])
                    return result_dict

        # Prepare pre-computed filters if unified analyzer was used
        pre_filters = None
        pre_refined_query = None
        response_prefix = ""
        is_statistical = False

        default_timeframe_applied = False
        analysis = None  # UnifiedAnalysisResult for smart filter clearing
        if unified_result and unified_result.get("continue_rag"):
            pre_filters = unified_result.get("filters")
            pre_refined_query = unified_result.get("refined_query")
            response_prefix = unified_result.get("response_prefix", "")
            is_statistical = unified_result.get("is_statistical", False)
            analysis = unified_result.get("analysis")  # For smart clearing rules

            # ========================================
            # FILTER MERGING: Preserve context from previous turn
            # ========================================
            # For follow-up queries, merge current filters with previous session filters.
            # Only values that are None in current but exist in previous are carried over.
            # Also accumulates search terms across turns.
            # SMART CLEARING: Pass analysis for scope=all and month change detection
            if pre_filters:
                pre_filters, pre_refined_query = self._merge_with_previous_filters(
                    session_id, pre_filters, pre_refined_query, analysis=analysis
                )
                # CRITICAL: Apply category mapping after merge to ensure valid DB category
                # This fixes the bug where merged category was raw (e.g., 'concerts de jazz')
                # instead of mapped (e.g., 'Musique')
                if pre_filters.get("category"):
                    raw_category = pre_filters["category"]
                    pre_filters["category"] = map_category_to_db(raw_category)
                    if pre_filters["category"] != raw_category:
                        logger.info(f"[CATEGORY-MAP] Post-merge mapping: '{raw_category}' → '{pre_filters['category']}'")

            # Apply default timeframe if none specified (Option B: auto-apply next 30 days)
            if pre_filters and should_apply_default_timeframe(pre_filters):
                pre_filters = apply_default_timeframe(pre_filters)
                default_timeframe_applied = True
                logger.info(f"[DEFAULT-TIMEFRAME] Auto-applied 30-day default to filters")

            logger.info(f"[OPTIMIZED] Passing unified analyzer filters to RAG: {pre_filters}")
            if response_prefix:
                logger.info(f"[MULTI-DIM] Response prefix: '{response_prefix[:50]}...'")
            if is_statistical:
                logger.info("[MULTI-DIM] Statistical query mode - will return count")

        # Track if this is an error response (don't cache errors)
        _is_error_response = False
        try:
            result = self.rag_chain.invoke({
                "input": question,
                "chat_history": chat_history,
                "language": language,
                "pre_filters": pre_filters,
                "pre_refined_query": pre_refined_query
            })

            logger.debug(f"[DEBUG-ANSWER] result['answer'] type: {type(result.get('answer'))}")
            if isinstance(result["answer"], dict):
                answer_text = result["answer"].get("answer_text", "")
                structured_events = result["answer"].get("events", [])

                logger.info(f"[POST-PROCESS] Event count: {len(structured_events)}")

                # Ensure events is a list (type safety)
                if not isinstance(structured_events, list):
                    logger.warning(f"structured_events is not a list: {type(structured_events)}")
                    structured_events = []

                needs_clarification = False
                clarifying_questions = []
            else:
                answer_text = str(result["answer"])
                structured_events = []
                needs_clarification = False
                clarifying_questions = []

            # ========================================
            # MULTI-DIMENSIONAL RESPONSE COMPOSITION
            # ========================================

            # Handle STATISTICAL queries - return count instead of event list
            if is_statistical and unified_result:
                analysis = unified_result.get("analysis")
                if analysis:
                    # Get count from retrieval stats
                    retrieval_stats = result.get("retrieved_data", {})
                    total_count = retrieval_stats.get("total_in_database", len(structured_events))

                    # Build category breakdown from results
                    category_counts: Dict[str, int] = {}
                    for doc in result.get("context", []):
                        cat = doc.metadata.get("category", "Autre")
                        category_counts[cat] = category_counts.get(cat, 0) + 1

                    # Build statistical response
                    stat_response = build_statistical_response(
                        count=total_count,
                        filters=analysis.filters,
                        category_breakdown=category_counts,
                        language=language
                    )
                    answer_text = stat_response
                    logger.info(f"[MULTI-DIM] Built statistical response for {total_count} events")

            # ========================================
            # COMPOSE FINAL RESPONSE USING BUILDER PATTERN (Phase 3B)
            # ========================================
            # Clean, maintainable composition replacing scattered string concatenation
            builder = ResponseBuilder(language=language)

            # Set main content (automatically strips existing suffix markers)
            builder.set_main_content(answer_text)

            # Add prefix for greetings, typo acknowledgments
            if response_prefix:
                builder.add_prefix(response_prefix)

            # Add filter-related suffixes if filters were applied
            if pre_filters:
                result_count = len(structured_events)
                has_results = result_count > 0 or len(result.get("context", [])) > 0

                # Add refinement suffix (default timeframe notice, hints)
                refinement_suffix = build_refinement_suffix(
                    filters=pre_filters,
                    has_results=has_results,
                    language=language
                )
                builder.add_refinement_suffix(refinement_suffix)

                # Add broadening suggestion if < 8 results
                builder.add_broadening_suggestion(result_count, threshold=8)

                # Echo applied filters and search terms for transparency
                search_terms = pre_filters.get("_search_terms", [])
                builder.add_filter_echo(pre_filters, search_terms)

                logger.info(f"[REFINEMENT] Added refinement (has_results={has_results}, count={result_count})")

            # Build final composed response
            answer_text = builder.build()
            logger.info(f"[RESPONSE-BUILDER] Final response composed ({len(answer_text)} chars)")

        except Exception as e:
            error_str = str(e).lower()
            error_type = type(e).__name__
            logger.error(f"Chain failed ({error_type}): {e}", exc_info=True)

            # Import HuggingFace error types for specific handling
            from src.generation.hf_wrapper import (
                HuggingFaceModelLoadingError,
                HuggingFaceRateLimitError,
                HuggingFaceQueueError,
            )

            # Provide clear, user-friendly error message based on error type
            # HuggingFace-specific: Model loading (cold start)
            if isinstance(e, HuggingFaceModelLoadingError) or "model is currently loading" in error_str or "is currently loading" in error_str:
                error_messages = {
                    "fr": (
                        "**Modele en cours de chargement**\n\n"
                        "Le modele IA demarre (cela peut prendre 20-30 secondes). "
                        "Veuillez reessayer dans un moment."
                    ),
                    "en": (
                        "**Model Loading**\n\n"
                        "The AI model is starting up (this can take 20-30 seconds). "
                        "Please try again in a moment."
                    )
                }
            # HuggingFace-specific: Rate limit
            elif isinstance(e, HuggingFaceRateLimitError) or "rate" in error_str and "limit" in error_str or "429" in error_str or "resource_exhausted" in error_str:
                error_messages = {
                    "fr": (
                        "**Limite de requetes atteinte**\n\n"
                        "Le service IA est temporairement sature. "
                        "Veuillez patienter 30 secondes avant de reessayer."
                    ),
                    "en": (
                        "**Rate Limit Reached**\n\n"
                        "The AI service is temporarily busy. "
                        "Please wait 30 seconds before trying again."
                    )
                }
            # HuggingFace-specific: Queue/timeout
            elif isinstance(e, HuggingFaceQueueError) or "queue" in error_str:
                error_messages = {
                    "fr": (
                        "**Service occupe**\n\n"
                        "Le service IA traite beaucoup de demandes. "
                        "Veuillez reessayer dans quelques secondes."
                    ),
                    "en": (
                        "**Service Busy**\n\n"
                        "The AI service is processing many requests. "
                        "Please try again in a few seconds."
                    )
                }
            # General: Connection/timeout errors
            elif "timeout" in error_str or "connection" in error_str:
                error_messages = {
                    "fr": (
                        "**Erreur de connexion**\n\n"
                        "Impossible de joindre le service IA. "
                        "Verifiez votre connexion internet et reessayez."
                    ),
                    "en": (
                        "**Connection Error**\n\n"
                        "Unable to reach the AI service. "
                        "Please check your internet connection and try again."
                    )
                }
            # General: Unknown error
            else:
                error_messages = {
                    "fr": (
                        "**Erreur inattendue**\n\n"
                        "Une erreur s'est produite lors du traitement de votre demande. "
                        "Veuillez reformuler votre question ou reessayer plus tard."
                    ),
                    "en": (
                        "**Unexpected Error**\n\n"
                        "An error occurred while processing your request. "
                        "Please rephrase your question or try again later."
                    )
                }

            answer_text = error_messages.get(language, error_messages["en"])
            structured_events = []
            needs_clarification = False
            clarifying_questions = []
            result = {"context": []}
            # Mark this as an error response - DO NOT CACHE
            _is_error_response = True

        # Extract complete source metadata (including enrichment fields for cache)
        sources = []
        for d in result.get("context", []):
            meta = d.metadata
            sources.append({
                "event_id": meta.get("event_id"),
                "title": meta.get("title"),
                "city": meta.get("city"),
                "category": meta.get("category"),
                "date": meta.get("start_date"),
                "url": meta.get("url"),
                "score": meta.get("score", 0.0),
                "match_type": meta.get("match_type", "Unknown"),
                # Enriched fields for display
                "price_label": meta.get("price_label", "Non spécifié"),
                "age_label": meta.get("age_label", "Tout public"),
                "timings": meta.get("timings", []),
                "periods": meta.get("periods", []),
                "is_full_day": meta.get("is_full_day", False),
                "conditions": meta.get("conditions"),
                "age_min": meta.get("age_min"),
                "age_max": meta.get("age_max"),
                "address": meta.get("address"),
                "postal_code": meta.get("postal_code"),
            })

        # Prepare retrieved_events for coreference resolution (lightweight version)
        retrieved_events = [
            {
                "event_id": s["event_id"],
                "title": s["title"],
                "city": s["city"],
                "address": s.get("address"),
                "category": s["category"],
            }
            for s in sources[:10]  # Limit to top 10 events to avoid bloating context
        ] if sources else None

        # Save to persistent storage (user msg async, assistant sync for message_id)
        _background_db_write(self.chat_storage.add_chat_message, session_id, "user", question)
        message_id = self.chat_storage.add_chat_message(
            session_id,
            "assistant",
            answer_text,
            retrieved_events=retrieved_events
        )

        # Add retrieval stats with transparency counts
        retrieval_stats = result.get("retrieved_data", {})
        exact_count = retrieval_stats.get("exact_count", sum(1 for s in sources if s.get("match_type") == "Exact Match"))
        nearby_count = len(sources) - exact_count

        res = {
            "answer": answer_text,
            "structured_events": structured_events,
            "message_id": message_id,
            "sources": sources,
            "retrieval_stats": {
                "total_count": retrieval_stats.get("actual_k", len(sources)),
                "exact_count": exact_count,
                "nearby_count": nearby_count
            },
            # Include clarification info for transparency
            "needs_clarification": needs_clarification,
            "clarifying_questions": clarifying_questions
        }

        # Store filters and search terms for follow-up query merging
        if pre_filters:
            self._store_session_filters(session_id, pre_filters, pre_refined_query)

        # Don't cache error responses - transient failures shouldn't persist
        if self.cache and not _is_error_response:
            self.cache.set(question, session_id, res)
        return res
