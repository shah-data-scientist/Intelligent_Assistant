"RAG orchestration chain for cultural events with history."

import logging
import re
import threading
from typing import Any, Dict, List, Optional, Tuple
from datetime import date, timedelta

from langchain_core.runnables import RunnablePassthrough, RunnableLambda, RunnableBranch
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, BaseMessage

from src.models.vector_store import EventVectorStore
from src.generation.llm import MistralLLM
from src.generation.prompts import get_rag_prompt, get_query_understanding_prompt
from src.retrieval.cache import QueryCache
from src.retrieval.manager import RetrievalManager
from src.data.chat_history import SQLiteChatMessageHistory
from src.data.storage import EventStorage
from src.data.chat_storage import ChatStorage
from src.security.guardrails import check_safety
from src.utils.geo import CityLocator
from src.utils.keywords import get_keyword_locator
from src.config import settings

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

def _async_db_write(func, *args, **kwargs):
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
            logger.error(f"[ASYNC-DB] Background write failed: {e}")

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

# Statistical query responses (bilingual)
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

# No hardcoded out-of-scope list needed - we use the database as the source of truth.
# If a city is in our database, it's in scope. Everything else is out of scope.


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
                # Event types that shouldn't be cities
                "concert", "concerts", "exposition", "expositions", "expo", "expos",
                "festival", "festivals", "spectacle", "spectacles", "show", "shows",
                "theatre", "theater", "théâtre", "opera", "opéra", "ballet", "dance", "danse",
                "exhibition", "exhibitions", "performance", "performances",
                "workshop", "workshops", "atelier", "ateliers",
            }

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


def is_broad_query(query: str, chat_history: Optional[List[Any]] = None) -> Tuple[bool, str]:
    """Detect if a query is too broad and needs clarification.

    STRICT 3-CRITERIA REQUIREMENT:
    A query must have ALL THREE of:
    - City (e.g., "Paris", "Versailles")
    - Event type (e.g., "concerts", "expositions", "jazz")
    - Date/timeframe (e.g., "ce week-end", "en février", "today")

    If ANY criterion is missing (from query + chat history context),
    the query is considered broad and needs clarification.

    EXCEPTION: Explicit "all/everything" intent bypasses this check.

    Args:
        query: The user query
        chat_history: Optional list of previous chat messages (HumanMessage/AIMessage)

    Returns:
        Tuple of (is_broad, reason) where reason describes what's missing
    """
    query_lower = query.lower().strip()
    words = query_lower.split()

    # Skip very short queries (greetings handled elsewhere)
    if len(words) < 1:
        return (False, "")

    # EXCEPTION: Explicit "all/everything" intent - user wants broad search
    broad_intent_words = {
        "all", "everything", "anything", "tous", "tout", "toutes",
        "n'importe", "nimporte", "whatever", "any"
    }
    if any(word in query_lower for word in broad_intent_words):
        logger.debug(f"Explicit broad intent detected in query: '{query}'")
        return (False, "")

    # Known IDF cities (check against city locator cache)
    city_locator = get_city_locator()
    known_cities = set(city_locator.city_cache.keys())

    # Also accept "île-de-france", "idf", "region" as valid city context
    region_words = {"île-de-france", "ile-de-france", "idf", "région", "region", "paris region"}

    # OPTIMIZATION: Use database-backed KeywordLocator for event types and dates
    # This provides fuzzy matching, typo detection, and comprehensive keyword coverage
    # (327 event descriptors, 78 date keywords with variants)
    keyword_locator = get_keyword_locator()

    # Check what the current query contains
    has_city = any(city in query_lower for city in known_cities) or any(r in query_lower for r in region_words)
    # KeywordLocator provides fuzzy matching for typos like "wekend" -> "weekend"
    has_event_type = keyword_locator.has_event_indicator(query)
    has_date = keyword_locator.has_date_indicator(query)

    # Track what was found in query vs history for debugging
    city_from_query = has_city
    event_from_query = has_event_type
    date_from_query = has_date

    logger.info(f"[BROAD-QUERY] Query analysis: city={has_city}, event_type={has_event_type}, date={has_date}")

    # IMPORTANT: Check chat history context (last 5 messages only for relevance)
    # If history mentions city/event_type/date, treat it as present
    if chat_history:
        # Only check recent history (last 5 messages) to avoid stale context
        recent_history = chat_history[-5:] if len(chat_history) > 5 else chat_history

        history_text = ""
        for msg in recent_history:
            if hasattr(msg, "content"):
                history_text += " " + msg.content.lower()

        logger.info(f"[BROAD-QUERY] Checking history context ({len(recent_history)} messages)")

        # Check if history contains the missing criteria
        if not has_city:
            has_city = any(city in history_text for city in known_cities) or any(r in history_text for r in region_words)
            if has_city:
                logger.info("[BROAD-QUERY] Found CITY in history context")
        if not has_event_type:
            # Use KeywordLocator for fuzzy matching in history context
            has_event_type = keyword_locator.has_event_indicator(history_text)
            if has_event_type:
                logger.info("[BROAD-QUERY] Found EVENT TYPE in history context")
        if not has_date:
            # Use KeywordLocator for date detection (including specific date formats)
            has_date = keyword_locator.has_date_indicator(history_text)
            if has_date:
                logger.info("[BROAD-QUERY] Found DATE in history context")

        # Summary of incremental clarification
        if has_city or has_event_type or has_date:
            logger.info(
                f"[BROAD-QUERY] After history check: city={has_city} (from_history={has_city and not city_from_query}), "
                f"event_type={has_event_type} (from_history={has_event_type and not event_from_query}), "
                f"date={has_date} (from_history={has_date and not date_from_query})"
            )

    # STRICT 3-CRITERIA: Build list of missing criteria
    missing = []
    if not has_city:
        missing.append("city")
    if not has_event_type:
        missing.append("event_type")
    if not has_date:
        missing.append("date")

    # If ANY criterion is missing, query is broad
    if missing:
        reason = "missing_" + "+".join(missing)
        logger.debug(f"Broad query detected. Missing: {missing}. Query: '{query}'")
        return (True, reason)

    return (False, "")


def check_special_query(query: str, language: Optional[str] = None) -> Optional[Tuple[str, str]]:
    """Check if query is a special case (greeting, capability, off-topic, out-of-scope city, statistical).

    Uses database-backed KeywordLocator as the SINGLE SOURCE OF TRUTH for all special query detection.
    Provides fuzzy matching for typo detection: "helo" -> "hello", "bonour" -> "bonjour", "wether" -> "weather".

    Detection order (priority):
    1. Greetings (bonjour, hello, salut) - checked first for fast response
    2. Capability questions (help, what can you do)
    3. Statistical queries (how many events, combien)
    4. Off-topic queries (weather, recipe, translate)
    5. Out-of-scope cities (Delhi, London) - with fuzzy city correction

    Args:
        query: The user query
        language: Optional language code ("fr" or "en")

    Returns:
        Tuple of (response_text, query_type) if special query detected, None otherwise
    """
    # Defensive: Auto-detect language if not provided
    if language is None:
        language = detect_language_from_query(query)

    # Get KeywordLocator for fuzzy matching (single source of truth)
    keyword_locator = get_keyword_locator()

    # ========================================
    # 1. GREETING CHECK
    # ========================================
    greeting_match = keyword_locator.detect_greeting(query)
    if greeting_match:
        logger.info(f"[SPECIAL-QUERY] Greeting detected: '{greeting_match.original}' -> '{greeting_match.matched}' ({greeting_match.match_type})")
        return (GREETING_RESPONSES[language], "greeting")

    # ========================================
    # 2. CAPABILITY CHECK
    # ========================================
    capability_match = keyword_locator.detect_capability(query)
    if capability_match:
        logger.info(f"[SPECIAL-QUERY] Capability detected: '{capability_match.original}' -> '{capability_match.matched}' ({capability_match.match_type})")
        return (CAPABILITY_RESPONSES[language], "capability")

    # ========================================
    # 3. STATISTICAL CHECK
    # ========================================
    statistical_match = keyword_locator.detect_statistical(query)
    if statistical_match:
        logger.info(f"[SPECIAL-QUERY] Statistical detected: '{statistical_match.original}' -> '{statistical_match.matched}' ({statistical_match.match_type})")
        return (STATISTICAL_RESPONSES[language], "statistical")

    # ========================================
    # 4. OFF-TOPIC CHECK
    # ========================================
    off_topic_match = keyword_locator.detect_off_topic(query)
    if off_topic_match:
        logger.info(f"[SPECIAL-QUERY] Off-topic detected: '{off_topic_match.original}' -> '{off_topic_match.matched}' ({off_topic_match.match_type}, subcategory: {off_topic_match.implied_category})")
        return (OFF_TOPIC_RESPONSES[language], "off_topic")

    # ========================================
    # 5. OUT-OF-SCOPE CITY CHECK
    # ========================================
    out_of_scope_city, suggested_city = detect_out_of_scope_city(query)
    if out_of_scope_city:
        if suggested_city:
            # Typo detected with fuzzy match - offer correction
            if language == "fr":
                response = f"""Je n'ai pas trouve **{out_of_scope_city}**, mais vouliez-vous dire **{suggested_city}** ?

Si oui, reformulez votre demande avec "{suggested_city}" et je serai ravie de vous aider !

Sinon, je couvre uniquement la region **Ile-de-France** (Paris et environs)."""
            else:
                response = f"""I couldn't find **{out_of_scope_city}**, but did you mean **{suggested_city}**?

If so, rephrase your request with "{suggested_city}" and I'll be happy to help!

Otherwise, I only cover the **Ile-de-France** region (Paris and surroundings)."""
            return (response, "city_typo_suggestion")
        else:
            # Truly out of scope, no fuzzy match
            response = OUT_OF_SCOPE_CITY_RESPONSES[language].format(city=out_of_scope_city)
            return (response, "out_of_scope_city")

    return None

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

        self.llm = llm or MistralLLM()
        self.chat_storage = chat_storage or ChatStorage()
        self.k = k

        # Initialize deterministic retrieval manager
        self.retrieval_manager = RetrievalManager(self.vector_store, k=k)

        self.cache = QueryCache(ttl_minutes=cache_ttl_minutes) if enable_cache else None

        # Chains - Use UNIFIED prompt (combines reformulation + refinement + extraction into 1 LLM call)
        # OLD: 3 separate chains = 3 LLM calls (~15-24s)
        # NEW: 1 unified chain = 1 LLM call (~5-8s)
        self.unified_understanding_chain = get_query_understanding_prompt() | self.llm.llm.bind(response_format={"type": "json_object"}) | JsonOutputParser()

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
        def prepare_inputs(inputs):
            history = inputs.get("chat_history", [])
            q = inputs["input"]
            return {"q": q, "raw_q": q, "history": history}

        # 2. UNIFIED Query Understanding + Hybrid Retrieval
        # Combines: reformulation + typo correction + filter extraction into ONE LLM call
        def retrieve_docs_hybrid(inputs):
            input_query = inputs["q"]
            raw_query = inputs["raw_q"]
            history = inputs["history"]

            try:
                # UNIFIED: One LLM call for reformulation + refinement + extraction
                understanding_result = self.unified_understanding_chain.invoke({
                    "question": input_query,
                    "chat_history": history
                })

                # Extract results from unified response
                refined_query = understanding_result.get("refined_query", input_query)
                raw_filters = understanding_result.get("filters", {})

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
                    "filters_applied": result.get("filters_applied", {})
                }
            except Exception as e:
                logger.error(f"Unified retrieval failed: {e}", exc_info=True)
                return {"docs": [], "filters": {}, "actual_k": 0}

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
                        filters_applied=lambda x: str(x["retrieved_data"].get("filters_applied", {}))
                    )
                    | RunnableLambda(select_prompt)
                    | self.llm.llm.bind(response_format={"type": "json_object"})
                    | JsonOutputParser()
                ),
                context=lambda x: x["retrieved_data"]["docs"]
            )
        )

    def _get_memory(self, session_id: str) -> SimpleSummaryBufferMemory:
        chat_memory = SQLiteChatMessageHistory(session_id=session_id, storage=self.chat_storage)
        return SimpleSummaryBufferMemory(llm=self.llm.llm, chat_memory=chat_memory)

    def _ensure_ready(self) -> None:
        """OPTIMIZATION D: Lazy initialization - load index on first query."""
        if not self._index_loaded:
            try:
                self.vector_store.load_index()
                self._index_loaded = True
                logger.info("FAISS index loaded (lazy initialization)")
            except Exception as e:
                logger.warning(f"Could not load FAISS index: {e}.")

    def query(self, question: str, session_id: str = "default_session") -> str:
        """Simple wrapper for backward compatibility."""
        result = self.query_with_metadata(question, session_id)
        return result["answer"]

    def query_with_metadata(self, question: str, session_id: str = "default_session", language: str = None) -> Dict[str, Any]:
        # OPTIMIZATION D: Ensure index is loaded (lazy init on first query)
        self._ensure_ready()

        logger.info(f"Query: {question}")
        check_safety(question)

        # Default to French if language not specified, or auto-detect
        if language is None:
            language = detect_language_from_query(question)

        # Check for special queries (greetings, capabilities, off-topic, statistical, out-of-scope city)
        # OPTIMIZATION: All fast-path queries handled here BEFORE any LLM call
        # Includes: greeting, capability, off_topic, statistical, out_of_scope_city, city_typo_suggestion
        special_result = check_special_query(question, language)
        if special_result:
            response_text, query_type = special_result
            logger.info(f"Special query detected: {query_type}")
            # Save to persistent storage (user msg async, assistant sync for message_id)
            _async_db_write(self.chat_storage.add_chat_message, session_id, "user", question)
            message_id = self.chat_storage.add_chat_message(session_id, "assistant", response_text)
            return {
                "answer": response_text,
                "sources": [],
                "structured_events": [],
                "message_id": message_id,
                "query_type": query_type
            }

        # Cache check - labels are now pre-computed in database, no enrichment needed
        if self.cache:
            cached = self.cache.get(question, session_id)
            if cached:
                logger.debug(f"[CACHE] Returning cached response")
                return cached

        memory = self._get_memory(session_id)
        chat_history = memory.load_memory_variables({})["chat_history"]

        # ========================================
        # OPTIMIZATION 1: EARLY BROAD QUERY CHECK
        # ========================================
        # Check if query is missing required criteria BEFORE calling LLM
        # This saves ~5-8s and API costs for vague queries
        is_broad, broad_reason = is_broad_query(question, chat_history)
        if is_broad:
            logger.info(f"[EARLY-BROAD] Query missing criteria: {broad_reason}. Skipping LLM.")
            from src.retrieval.clarifications import get_clarification_response
            backup_prefix, backup_questions = get_clarification_response(broad_reason, language)

            if backup_prefix and backup_questions:
                questions_text = "\n".join([f"- {q}" for q in backup_questions])
                answer_text = f"{backup_prefix}{questions_text}"

                # Save to persistent storage (user msg async, assistant sync for message_id)
                _async_db_write(self.chat_storage.add_chat_message, session_id, "user", question)
                message_id = self.chat_storage.add_chat_message(session_id, "assistant", answer_text)

                return {
                    "answer": answer_text,
                    "sources": [],
                    "structured_events": [],
                    "message_id": message_id,
                    "query_type": "broad_query",
                    "needs_clarification": True,
                    "clarifying_questions": backup_questions
                }

        try:
            result = self.rag_chain.invoke({
                "input": question,
                "chat_history": chat_history,
                "language": language
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
        except Exception as e:
            logger.error(f"Chain failed: {e}", exc_info=True)
            answer_text = "I encountered an error."
            structured_events = []
            needs_clarification = False
            clarifying_questions = []
            result = {"context": []}

        # Save to persistent storage (user msg async, assistant sync for message_id)
        _async_db_write(self.chat_storage.add_chat_message, session_id, "user", question)
        message_id = self.chat_storage.add_chat_message(session_id, "assistant", answer_text)

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
                "score": meta.get("score", 0.0),
                "match_type": meta.get("match_type", "Unknown"),
                # Include enrichment metadata for cache re-enrichment
                "conditions": meta.get("conditions"),
                "age_min": meta.get("age_min"),
                "age_max": meta.get("age_max"),
            })

        # Add retrieval stats
        retrieval_stats = result.get("retrieved_data", {})

        res = {
            "answer": answer_text,
            "structured_events": structured_events,
            "message_id": message_id,
            "sources": sources,
            "retrieval_stats": {
                "total_count": retrieval_stats.get("actual_k", len(sources)),
                "exact_count": sum(1 for s in sources if s.get("match_type") == "Exact Match")
            },
            # Include clarification info for transparency
            "needs_clarification": needs_clarification,
            "clarifying_questions": clarifying_questions
        }
        if self.cache: self.cache.set(question, session_id, res)
        return res
