"""
FILE: unified_analyzer.py
STATUS: Active
RESPONSIBILITY: Multi-dimensional LLM-based query analysis with intent classification, entity extraction, and filter generation.

DEPENDENCIES (Who uses this file):
- src/retrieval/chain.py: Calls unified_analyze() for query analysis
- src/retrieval/response_builder.py: Uses UnifiedAnalysisResult for response composition
- tests/e2e/test_structured_output.py: Tests structured output format
- tests/integration/test_chat_history.py: Tests query analysis in conversation context

IMPORTS (What this file needs):
- src.generation.llm: get_chat_llm() for LLM instance
- src.retrieval.schemas: UnifiedAnalysisSchema for structured LLM output
- langchain_core.messages: Message types for LLM prompting
- tenacity: Retry logic for rate limit handling (Google Gemini API)
- src.config: LLM settings and configuration

LAST MAJOR UPDATE: 2026-01-28 (Enhanced multi-dimensional classification with typo correction)
MAINTAINER: Core Backend Team

MULTI-DIMENSIONAL APPROACH:
A single query can have MULTIPLE classifications that compose into a response:
- Greeting dimension (independent - can be prefixed to response)
- Typo correction dimension (acknowledged in response)
- Statistical dimension (changes output format - COUNT vs list)
- Event search dimension (main search functionality)
- Location dimension (filter)
- Timeframe dimension (filter)
- Audience dimension (filter)

Each dimension triggers an independent action, composed into a final response
that respects existing generation rules and fallbacks.

Example: "tell me how many events in Possy in January"
- Typo: "Possy" → "Poissy" (acknowledge correction)
- Statistical: "how many" → return COUNT
- Location: Poissy (filter)
- Timeframe: January (filter)
- Event type: None (user wants ALL events, no clarification needed)
"""

import json
import logging
import time
from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception, before_sleep_log, RetryError

from src.generation.llm import get_chat_llm
from langchain_core.messages import HumanMessage, SystemMessage, BaseMessage

from src.config import settings
from src.retrieval.schemas import UnifiedAnalysisSchema
import calendar
import re

logger = logging.getLogger(__name__)


# ========================================
# RETRY LOGIC FOR 429 RATE LIMIT ERRORS
# ========================================
# The Google Gemini API has strict rate limits that can cause 429 errors.
# We implement exponential backoff retry specifically for these errors.


def is_rate_limit_error(exception: Exception) -> bool:
    """Check if exception is a 429 rate limit error.

    Handles both Google Gemini and Mistral API rate limits.
    """
    error_str = str(exception).lower()
    return (
        "429" in error_str
        or "resource_exhausted" in error_str
        or "resource exhausted" in error_str
        or ("rate" in error_str and "limit" in error_str)  # Google's plain text variant
        or "too many requests" in error_str
        or "quota" in error_str
    )


# Retry decorator for rate limit errors
# Reduced to 2 attempts to avoid exhausting quota during rate limiting
llm_rate_limit_retry = retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=2, min=2, max=10),
    retry=retry_if_exception(is_rate_limit_error),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)


# Category mapping: user-friendly terms → DB category names
CATEGORY_MAPPING = {
    # Musique
    "concert": "Musique",
    "concerts": "Musique",
    "musique": "Musique",
    "jazz": "Musique",
    "opera": "Musique",
    "opéra": "Musique",
    "classical": "Musique",
    "classique": "Musique",
    "rock": "Musique",
    "music": "Musique",
    # Théâtre / Spectacle
    "theater": "Théâtre / Spectacle",
    "theatre": "Théâtre / Spectacle",
    "théâtre": "Théâtre / Spectacle",
    "spectacle": "Théâtre / Spectacle",
    "spectacles": "Théâtre / Spectacle",
    "comedy": "Théâtre / Spectacle",
    "comédie": "Théâtre / Spectacle",
    "show": "Théâtre / Spectacle",
    "shows": "Théâtre / Spectacle",
    # Art / Exposition
    "exhibition": "Art / Exposition",
    "exhibitions": "Art / Exposition",
    "exposition": "Art / Exposition",
    "expositions": "Art / Exposition",
    "expo": "Art / Exposition",
    "expos": "Art / Exposition",
    "art": "Art / Exposition",
    "gallery": "Art / Exposition",
    "galerie": "Art / Exposition",
    "museum": "Art / Exposition",
    "musée": "Art / Exposition",
    # Danse
    "dance": "Danse",
    "danse": "Danse",
    "ballet": "Danse",
    # Conférence / Débat
    "conference": "Conférence / Débat",
    "conférence": "Conférence / Débat",
    "debate": "Conférence / Débat",
    "débat": "Conférence / Débat",
    "talk": "Conférence / Débat",
    # Atelier / Workshop
    "workshop": "Atelier / Workshop",
    "atelier": "Atelier / Workshop",
    # Sport / Loisirs
    "sport": "Sport / Loisirs",
    "sports": "Sport / Loisirs",
    # Jeunesse / Famille
    "kids": "Jeunesse / Famille",
    "children": "Jeunesse / Famille",
    "enfants": "Jeunesse / Famille",
    "family": "Jeunesse / Famille",
    "famille": "Jeunesse / Famille",
    # Festival
    "festival": "Festival",
    "fête": "Festival",
    # Patrimoine
    "heritage": "Patrimoine",
    "patrimoine": "Patrimoine",
    "visite": "Patrimoine",
}


def map_category_to_db(category: str | None) -> str | None:
    """Map user-friendly category term to database category name.

    Supports:
    - Exact match: "concert" → "Musique"
    - Word-in-phrase match: "concerts de jazz" → "Musique" (via "concert" or "jazz")
    """
    if not category:
        return None
    category_lower = category.lower().strip()

    # First try exact match
    mapped = CATEGORY_MAPPING.get(category_lower)
    if mapped:
        logger.info(f"[CATEGORY MAP] '{category}' → '{mapped}' (exact match)")
        return mapped

    # Second, check if any mapping key appears as a word in the category
    # This handles cases like "concerts de jazz" matching "concert" or "jazz"
    category_words = set(category_lower.split())
    for key, db_category in CATEGORY_MAPPING.items():
        if key in category_words:
            logger.info(f"[CATEGORY MAP] '{category}' → '{db_category}' (word match: '{key}')")
            return db_category

    # If not in mapping, return as-is (might already be a DB category)
    return category


def validate_and_correct_weekend(day_value: Any, month: int, year: int, timeframe_raw: str) -> Any:
    """Validate and correct weekend calculations using Python's calendar.

    Args:
        day_value: The day(s) extracted by LLM (int or list)
        month: Month number (1-12)
        year: Year (e.g., 2026)
        timeframe_raw: Original timeframe text from user (e.g., "second weekend of March")

    Returns:
        Corrected day value (int or list)
    """
    if not timeframe_raw or month is None or year is None:
        return day_value

    timeframe_lower = timeframe_raw.lower()

    # Check if this is a weekend query
    weekend_match = re.search(r"(first|second|third|fourth|last|1st|2nd|3rd|4th)\s+weekend", timeframe_lower)
    if not weekend_match:
        return day_value  # Not a weekend query, trust LLM

    ordinal = weekend_match.group(1)
    ordinal_map = {"first": 1, "1st": 1, "second": 2, "2nd": 2, "third": 3, "3rd": 3, "fourth": 4, "4th": 4, "last": -1}
    weekend_number = ordinal_map.get(ordinal, 1)

    # Calculate correct weekend using Python calendar
    cal = calendar.Calendar()
    saturdays = []

    for day in cal.itermonthdays2(year, month):
        # day is (day_of_month, weekday) where Monday=0, Sunday=6
        day_num, weekday = day
        if day_num != 0 and weekday == 5:  # Saturday
            saturdays.append(day_num)

    if not saturdays:
        return day_value  # Edge case: no Saturdays (shouldn't happen)

    # Get the correct Saturday
    if weekend_number == -1:  # Last weekend
        saturday = saturdays[-1]
    elif weekend_number <= len(saturdays):
        saturday = saturdays[weekend_number - 1]
    else:
        return day_value  # Invalid weekend number

    sunday = saturday + 1
    # Handle month overflow (rare edge case)
    days_in_month = calendar.monthrange(year, month)[1]
    if sunday > days_in_month:
        sunday = 1  # Overflow to next month (edge case)

    correct_days = [saturday, sunday]

    # Check if LLM's answer matches
    if isinstance(day_value, list):
        if sorted(day_value) != sorted(correct_days):
            logger.info(f"[DATE VALIDATION] Correcting weekend: {day_value} → {correct_days}")
            return correct_days
    else:
        if day_value not in correct_days:
            logger.info(f"[DATE VALIDATION] Correcting weekend: {day_value} → {correct_days}")
            return correct_days

    return day_value


class QueryIntent(Enum):
    """Possible user query intents (primary intent for compatibility)."""

    EVENT_SEARCH = "event_search"
    GREETING = "greeting"
    CHITCHAT = "chitchat"
    CAPABILITY = "capability"
    DIRECTIONS = "directions"  # NEW: How to get to an event
    ABUSE = "abuse"
    OFF_TOPIC = "off_topic"


@dataclass
class QueryDimension:
    """A single dimension of query classification."""

    name: str  # Dimension name (greeting, typo, statistical, etc.)
    detected: bool  # Whether this dimension was detected
    value: Optional[str] = None  # Extracted value (e.g., corrected city name)
    original: Optional[str] = None  # Original value before correction
    action: Optional[str] = None  # Action to take (acknowledge, count, filter, etc.)
    confidence: float = 1.0  # Confidence in this dimension


@dataclass
class UnifiedAnalysisResult:
    """Result from unified query analysis with multi-dimensional support."""

    # Primary intent (for backward compatibility)
    intent: QueryIntent
    intent_confidence: float

    # MULTI-DIMENSIONAL CLASSIFICATIONS
    dimensions: Dict[str, QueryDimension] = field(default_factory=dict)

    # Language detection (replaces heuristic-based detection)
    detected_language: str = "fr"  # "fr" or "en"

    # Entity extraction
    city: Optional[str] = None
    city_normalized: Optional[str] = None  # Normalized to official name
    event_type: Optional[str] = None
    timeframe: Optional[str] = None

    # Query completeness (now respects statistical queries)
    is_complete: bool = False
    missing_criteria: List[str] = field(default_factory=list)

    # Search filters
    filters: Dict[str, Any] = field(default_factory=dict)

    # Refined query for search
    refined_query: str = ""

    # Raw response for debugging
    raw_response: Dict[str, Any] = field(default_factory=dict)

    # Convenience properties for dimension access
    @property
    def has_greeting(self) -> bool:
        """Check if query has a greeting component."""
        return self.dimensions.get("greeting", QueryDimension("greeting", False)).detected

    @property
    def has_typo_correction(self) -> bool:
        """Check if a typo was corrected."""
        return self.dimensions.get("typo", QueryDimension("typo", False)).detected

    @property
    def typo_correction(self) -> Optional[Tuple[str, str]]:
        """Get (original, corrected) tuple if typo was corrected."""
        dim = self.dimensions.get("typo")
        if dim and dim.detected:
            return (dim.original, dim.value)
        return None

    @property
    def is_statistical(self) -> bool:
        """Check if query is asking for statistics (count, how many, etc.)."""
        return self.dimensions.get("statistical", QueryDimension("statistical", False)).detected

    @property
    def wants_all_events(self) -> bool:
        """Check if user wants ALL events (no event type filter needed)."""
        dim = self.dimensions.get("scope")
        return dim and dim.detected and dim.value == "all"


def get_unified_analysis_prompt(today: date, known_cities: List[str]) -> str:
    """Generate the unified analysis system prompt with MULTI-DIMENSIONAL output.

    Args:
        today: Today's date for relative date calculation
        known_cities: List of valid IDF cities (for normalization)

    Returns:
        System prompt string
    """
    # Calculate weekend dates
    days_until_saturday = (5 - today.weekday()) % 7
    if days_until_saturday == 0 and today.weekday() != 5:
        days_until_saturday = 7
    this_saturday = today + timedelta(days=days_until_saturday)
    this_sunday = this_saturday + timedelta(days=1)

    # Sample of known cities for prompt (avoid token overflow)
    cities_sample = known_cities[:30] if len(known_cities) > 30 else known_cities
    cities_str = ", ".join(cities_sample)

    return f"""You are a query analyzer for cultural events in Île-de-France.

**TODAY:** {today.strftime('%Y-%m-%d')}
**THIS WEEKEND:** {this_saturday.strftime('%B %d')} - {this_sunday.strftime('%B %d')}
**KNOWN CITIES:** {cities_str}

**PRIMARY INTENT:** event_search (default), directions, greeting, chitchat, capability, abuse, off_topic

**DIMENSIONS:** greeting, typo correction, statistical, scope (all events vs specific type)

**LANGUAGE:** Detect "fr" or "en" (default: "fr")

**EVENT TYPE:** Extract category (concert, expo, théâtre, etc.), NOT theme

**COMPLETENESS (2/3 rule):** Query needs 2 of: city, timeframe, event_type
Statistical queries always complete.

**ENTITY EXTRACTION:**
- City: Normalize to known cities
- Dates: Calculate from TODAY (this weekend = [{this_saturday.day}, {this_sunday.day}])
- Audience: kids, professional, family
- Free: Detect "gratuit/free"

**CONTEXT:** Carry forward filters from previous conversation unless explicitly changed.

Return structured output with all dimensions."""


class UnifiedAnalyzer:
    """Unified LLM analyzer for query understanding.

    Combines:
    - Intent classification
    - Entity extraction (city, event_type, date)
    - City normalization
    - Filter extraction
    - Query reformulation

    Into ONE LLM call!
    """

    def __init__(self, model: str | None = None):
        """Initialize the unified analyzer.

        Args:
            model: Model to use (defaults based on llm_backend setting)
        """
        self.llm = get_chat_llm(
            model=model,
            temperature=0.0,
            max_tokens=500,
        )
        self.model = model or settings.llm_backend
        self._mistral_llm = None  # Lazy-loaded fallback LLM

        # Create structured output LLM for Gemini (if using Google backend)
        self.use_structured_output = self.model == "google"
        if self.use_structured_output:
            try:
                self.structured_llm = self.llm.with_structured_output(UnifiedAnalysisSchema)
                logger.info("Initialized UnifiedAnalyzer with STRUCTURED OUTPUT (Gemini)")
            except Exception as e:
                logger.warning(f"Failed to create structured output LLM: {e}. Using fallback JSON parsing.")
                self.use_structured_output = False
                self.structured_llm = None
        else:
            self.structured_llm = None

        logger.info(f"Initialized UnifiedAnalyzer with model: {self.model}")

    def _get_mistral_fallback_llm(self):
        """Get or create Mistral LLM for fallback (lazy-loaded)."""
        if self._mistral_llm is None:
            from langchain_mistralai import ChatMistralAI

            self._mistral_llm = ChatMistralAI(
                model="mistral-small-latest",
                temperature=0.0,
                max_tokens=500,
                api_key=settings.mistral_api_key,
            )
            logger.info("[FALLBACK] Initialized Mistral LLM as fallback")
        return self._mistral_llm

    def _try_mistral_fallback(self, query: str, messages: List[BaseMessage]) -> Optional[Dict[str, Any]]:
        """Try Mistral as fallback when primary LLM fails.

        Args:
            query: Original user query
            messages: Messages that were sent to primary LLM

        Returns:
            Parsed JSON result dict if successful, None if Mistral also fails
        """
        try:
            logger.info("[FALLBACK] Trying Mistral fallback for query analysis...")
            mistral_llm = self._get_mistral_fallback_llm()
            response = mistral_llm.invoke(messages)
            content = response.content.strip()

            # Try to parse JSON from response
            result = None

            # First, try to extract JSON from markdown code blocks
            json_block_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", content, re.IGNORECASE)
            if json_block_match:
                try:
                    result = json.loads(json_block_match.group(1))
                except json.JSONDecodeError:
                    pass

            # If that failed, try parsing the whole content as JSON
            if result is None:
                try:
                    result = json.loads(content)
                except json.JSONDecodeError:
                    pass

            # If still failed, try to find a JSON object anywhere in the content
            if result is None:
                json_match = re.search(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", content, re.DOTALL)
                if json_match:
                    try:
                        result = json.loads(json_match.group())
                    except json.JSONDecodeError:
                        pass

            if result:
                logger.info("[FALLBACK] Mistral fallback successful - extracted filters")
                return result
            else:
                logger.warning("[FALLBACK] Mistral response could not be parsed as JSON")
                return None

        except Exception as e:
            logger.warning(f"[FALLBACK] Mistral fallback failed: {e}")
            return None

    @llm_rate_limit_retry
    def _invoke_with_retry(self, messages: List[BaseMessage]) -> Any:
        """Invoke LLM with retry logic for 429 rate limit errors.

        Args:
            messages: Messages to send to the LLM

        Returns:
            LLM response

        Raises:
            Exception: If all retry attempts fail (after 5 attempts with exponential backoff)
        """
        logger.debug(f"[UNIFIED] Invoking LLM with {len(messages)} messages")
        return self.llm.invoke(messages)

    def _fallback_extraction(self, query: str, llm_response: str) -> Dict[str, Any]:
        """Extract query information using regex when LLM doesn't produce valid JSON.

        This is a fallback for smaller models that may not follow JSON format strictly.

        Args:
            query: Original user query
            llm_response: Raw LLM response text

        Returns:
            Dict with extracted information in expected format
        """
        query_lower = query.lower()
        result = {
            "intent": "event_search",
            "intent_confidence": 0.7,
            "detected_language": "fr" if any(w in query_lower for w in ["de", "à", "en", "le", "la", "les"]) else "en",
            "dimensions": {},
            "entities": {},
            "filters": {},
            "is_complete": False,
            "missing": [],
            "refined_query": query,
        }

        # Extract city from query using known patterns
        city_patterns = [
            r"\b(?:à|a|in|at)\s+([A-Z][a-zéèêëàâäùûüôöîï]+(?:-[A-Z][a-zéèêëàâäùûüôöîï]+)?)\b",
            r"\b(Paris|Versailles|Poissy|Montreuil|Pantin|Nanterre|Saint-Denis|Bobigny)\b",
        ]
        for pattern in city_patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                city = match.group(1)
                result["entities"]["city_normalized"] = city.title()
                result["filters"]["city"] = city.title()
                break

        # Extract month (with support for multi-month queries)
        month_map = {
            "janvier": 1,
            "january": 1,
            "février": 2,
            "fevrier": 2,
            "february": 2,
            "mars": 3,
            "march": 3,
            "avril": 4,
            "april": 4,
            "mai": 5,
            "may": 5,
            "juin": 6,
            "june": 6,
            "juillet": 7,
            "july": 7,
            "août": 8,
            "aout": 8,
            "august": 8,
            "septembre": 9,
            "september": 9,
            "octobre": 10,
            "october": 10,
            "novembre": 11,
            "november": 11,
            "décembre": 12,
            "decembre": 12,
            "december": 12,
        }

        # Check for multi-month patterns first (OR logic)
        or_pattern = r"(\w+)\s+(?:or|ou)\s+(\w+)"
        match = re.search(or_pattern, query_lower, re.IGNORECASE)
        if match:
            month1_name = match.group(1).lower()
            month2_name = match.group(2).lower()
            month1 = month_map.get(month1_name)
            month2 = month_map.get(month2_name)
            if month1 and month2:
                result["filters"]["month"] = [month1, month2]
                result["entities"]["timeframe_raw"] = f"{month1_name} or {month2_name}"
                logger.info(f"[MULTI-MONTH] Detected OR pattern: {result['filters']['month']}")

        # Check for date range patterns (May to August, June through September)
        if "month" not in result["filters"]:
            range_pattern = r"(\w+)\s+(?:to|through|until|à|jusqu\'à)\s+(\w+)"
            match = re.search(range_pattern, query_lower, re.IGNORECASE)
            if match:
                start_month_name = match.group(1).lower()
                end_month_name = match.group(2).lower()
                start_month = month_map.get(start_month_name)
                end_month = month_map.get(end_month_name)
                if start_month and end_month and start_month <= end_month:
                    result["filters"]["month"] = list(range(start_month, end_month + 1))
                    result["entities"]["timeframe_raw"] = f"{start_month_name} to {end_month_name}"
                    logger.info(f"[MULTI-MONTH] Detected range pattern: {result['filters']['month']}")

        # Single month extraction (if no multi-month pattern found)
        if "month" not in result["filters"]:
            for month_name, month_num in month_map.items():
                if month_name in query_lower:
                    result["filters"]["month"] = month_num
                    result["entities"]["timeframe_raw"] = month_name
                    break

        # Extract event type from category mapping
        for keyword, category in CATEGORY_MAPPING.items():
            if keyword in query_lower:
                result["entities"]["event_type"] = keyword
                result["filters"]["category"] = category
                break

        # Determine completeness (2 out of 3 rule)
        has_city = result["filters"].get("city") is not None
        has_timeframe = result["filters"].get("month") is not None
        has_event_type = result["entities"].get("event_type") is not None

        if sum([has_city, has_timeframe, has_event_type]) >= 2:
            result["is_complete"] = True
        else:
            if not has_city:
                result["missing"].append("city")
            if not has_timeframe:
                result["missing"].append("timeframe")
            if not has_event_type:
                result["missing"].append("event_type")

        logger.info(
            f"[FALLBACK] Extracted: city={result['filters'].get('city')}, "
            f"month={result['filters'].get('month')}, event_type={result['entities'].get('event_type')}"
        )
        return result

    def _build_result_from_dict(
        self, query: str, result: Dict[str, Any], known_cities: Optional[List[str]] = None
    ) -> "UnifiedAnalysisResult":
        """Build UnifiedAnalysisResult from a dict (from fallback or Mistral).

        Args:
            query: Original user query
            result: Dict with extracted information
            known_cities: List of valid IDF cities for normalization

        Returns:
            UnifiedAnalysisResult object
        """
        intent_str = result.get("intent", "event_search")
        intent_map = {
            "event_search": QueryIntent.EVENT_SEARCH,
            "greeting": QueryIntent.GREETING,
            "chitchat": QueryIntent.CHITCHAT,
            "capability": QueryIntent.CAPABILITY,
            "abuse": QueryIntent.ABUSE,
            "off_topic": QueryIntent.OFF_TOPIC,
        }

        entities = result.get("entities", {})
        filters = result.get("filters", {})

        # Map category to DB format if present
        if filters.get("category"):
            filters["category"] = map_category_to_db(filters["category"])

        # Build basic dimensions (all false for fallback)
        dimensions = {
            "greeting": QueryDimension("greeting", False),
            "typo": QueryDimension("typo", False),
            "statistical": QueryDimension("statistical", False),
            "scope": QueryDimension("scope", False),
        }

        # Validate city against known cities
        city_normalized = entities.get("city_normalized") or filters.get("city")
        if city_normalized and known_cities:
            known_cities_lower = [c.lower() for c in known_cities]
            if city_normalized.lower() not in known_cities_lower:
                logger.warning(f"[FALLBACK] City '{city_normalized}' not in known cities, clearing")
                city_normalized = None
                filters.pop("city", None)

        detected_language = result.get("detected_language", "fr")
        if detected_language not in ["fr", "en"]:
            detected_language = "fr"

        is_complete = result.get("is_complete", False)
        missing_criteria = result.get("missing", [])

        return UnifiedAnalysisResult(
            intent=intent_map.get(intent_str, QueryIntent.EVENT_SEARCH),
            intent_confidence=float(result.get("intent_confidence", 0.6)),
            dimensions=dimensions,
            detected_language=detected_language,
            city=entities.get("city_raw"),
            city_normalized=city_normalized,
            event_type=entities.get("event_type"),
            timeframe=entities.get("timeframe_raw"),
            is_complete=is_complete,
            missing_criteria=missing_criteria,
            filters=filters,
            refined_query=result.get("refined_query", query),
            raw_response=result,
        )

    def analyze(
        self,
        query: str,
        chat_history: List[BaseMessage] = None,
        known_cities: List[str] = None,
        previous_events: list[dict] | None = None,
    ) -> UnifiedAnalysisResult:
        """Analyze query in one unified LLM call with MULTI-DIMENSIONAL output.

        Args:
            query: User's input query
            chat_history: Optional chat history for context
            known_cities: List of valid IDF cities for normalization
            previous_events: Optional events from previous response (for coreference resolution)

        Returns:
            UnifiedAnalysisResult with all extracted information including dimensions
        """
        if known_cities is None:
            known_cities = []

        try:
            # Build system prompt with today's date and known cities
            today = date.today()
            system_prompt = get_unified_analysis_prompt(today, known_cities)

            # Build messages
            messages = [SystemMessage(content=system_prompt)]

            # Add history context if available
            if chat_history:
                recent = chat_history[-3:] if len(chat_history) > 3 else chat_history
                history_context = "Previous conversation:\n"
                for msg in recent:
                    if hasattr(msg, "content"):
                        role = "User" if hasattr(msg, "type") and msg.type == "human" else "Assistant"
                        history_context += f"{role}: {msg.content[:100]}...\n"
                messages.append(SystemMessage(content=history_context))

            # Add previous events context for coreference resolution
            if previous_events:
                events_context = "\n**PREVIOUS RESULTS (for coreference resolution):**\n"
                events_context += "The assistant just returned these events:\n"
                for i, event in enumerate(previous_events[:5], 1):
                    events_context += f"{i}. {event.get('title')} ({event.get('category')})\n"
                    events_context += f"   Location: {event.get('address') or event.get('city')}\n"
                events_context += "\nIf the user's query references these events (e.g., 'that concert', 'the last event', event name), classify as DIRECTIONS if asking how to get there.\n"
                messages.append(SystemMessage(content=events_context))

            messages.append(HumanMessage(content=f"Query: {query}"))

            # ========================================
            # PHASE 2: PYDANTIC STRUCTURED OUTPUT FOR GEMINI
            # ========================================
            result = None

            if self.use_structured_output:
                # Use Gemini's structured output (returns Pydantic object directly)
                try:
                    logger.info("[STRUCTURED] Using Gemini with_structured_output")
                    structured_result = self.structured_llm.invoke(messages)

                    # Convert Pydantic object to dict format matching existing code
                    result = {
                        "intent": structured_result.intent.value,
                        "intent_confidence": structured_result.intent_confidence,
                        "detected_language": structured_result.detected_language,
                        "refined_query": structured_result.refined_query,
                        "is_complete": structured_result.is_complete,
                        "missing": structured_result.missing_info,
                        "entities": {
                            "city_raw": structured_result.city,
                            "city_normalized": structured_result.city_normalized,
                            "event_type": structured_result.event_type,
                            "timeframe_raw": structured_result.timeframe,
                        },
                        "filters": structured_result.filters.model_dump(exclude_none=True),
                        "dimensions": {
                            "greeting": {"detected": structured_result.is_greeting, "value": None},
                            "typo": {
                                "detected": structured_result.has_typo,
                                "original": structured_result.original_query,
                                "corrected": structured_result.corrected_query,
                            },
                            "statistical": {"detected": structured_result.is_statistical, "type": None},
                            "scope": {
                                "detected": structured_result.wants_all_events,
                                "value": "all" if structured_result.wants_all_events else None,
                            },
                        },
                        "coreference": {
                            "references_previous": structured_result.coreference.references_previous,
                            "event_id": structured_result.coreference.event_id,
                            "event_name": structured_result.coreference.event_name,
                            "reference_type": structured_result.coreference.reference_type,
                        },
                    }
                    logger.info(f"[STRUCTURED] Successfully parsed structured output for intent={result['intent']}")

                except Exception as e:
                    logger.warning(f"[STRUCTURED] Failed to use structured output: {e}. Falling back to JSON parsing.")
                    result = None

            # Fallback for non-Gemini backends or if structured output failed
            if result is None:
                # Invoke LLM with retry for 429 rate limit errors
                # Retries up to 5 times with exponential backoff (2s, 4s, 8s, 16s, 32s max 60s)
                response = self._invoke_with_retry(messages)
                content = response.content.strip()

                # Parse JSON response - handle markdown code blocks (```json ... ```)
                # First, try to extract JSON from markdown code blocks
                json_block_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", content, re.IGNORECASE)
                if json_block_match:
                    try:
                        result = json.loads(json_block_match.group(1))
                    except json.JSONDecodeError:
                        pass

                # If that failed, try parsing the whole content as JSON
                if result is None:
                    try:
                        result = json.loads(content)
                    except json.JSONDecodeError:
                        pass

                # If still failed, try to find a JSON object anywhere in the content
                if result is None:
                    json_match = re.search(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", content, re.DOTALL)
                    if json_match:
                        try:
                            result = json.loads(json_match.group())
                        except json.JSONDecodeError:
                            pass

                # If all parsing failed, try Mistral fallback before basic extraction
                if result is None:
                    logger.warning("[UNIFIED] Could not parse JSON from response, trying Mistral fallback...")
                    result = self._try_mistral_fallback(query, messages)
                    if result is None:
                        logger.warning("[UNIFIED] Mistral fallback failed, using basic keyword extraction")
                        result = self._fallback_extraction(query, content)

            # Map intent to enum
            intent_str = result.get("intent", "event_search")
            intent_map = {
                "event_search": QueryIntent.EVENT_SEARCH,
                "greeting": QueryIntent.GREETING,
                "chitchat": QueryIntent.CHITCHAT,
                "capability": QueryIntent.CAPABILITY,
                "directions": QueryIntent.DIRECTIONS,  # FIX: Add missing directions mapping
                "abuse": QueryIntent.ABUSE,
                "off_topic": QueryIntent.OFF_TOPIC,
            }

            entities = result.get("entities", {})
            filters = result.get("filters", {})
            raw_dimensions = result.get("dimensions", {})

            # ========================================
            # CODE-LEVEL FILTER INFERENCE (robust extraction)
            # ========================================
            # The LLM extracts entities and filters, but may miss connections.
            # This section ensures ALL filters are properly derived from the query.

            # 1. SYNC CITY: Ensure filters.city matches entities.city_normalized
            city_normalized = entities.get("city_normalized")
            if city_normalized and not filters.get("city"):
                filters["city"] = city_normalized
                logger.info(f"[FILTER-SYNC] Derived city from entities: '{city_normalized}'")
            elif filters.get("city") and not city_normalized:
                # LLM put city in filters but not entities - sync back
                entities["city_normalized"] = filters["city"]
                logger.info(f"[FILTER-SYNC] Synced city to entities: '{filters['city']}'")

            # 2. DERIVE CATEGORY from event_type
            # TERMINOLOGY CLARIFICATION:
            #   - event_type: User input term (informal, lowercase) e.g., "jazz", "concert", "théâtre"
            #   - category: Database classification filter (formal) e.g., "Musique", "Théâtre / Spectacle"
            # LLM extracts event_type from user query but often leaves category=null
            # This logic bridges the gap: copy event_type → category for database filtering
            event_type = entities.get("event_type")
            if event_type and not filters.get("category"):
                filters["category"] = event_type  # User's informal term becomes database filter
                logger.info(f"[FILTER-INFER] Derived category from event_type: '{event_type}'")

            # 3. DETECT FREE EVENTS from query keywords
            # If LLM missed "gratuit/free" keywords, detect them
            query_lower = query.lower()
            free_keywords = ["gratuit", "gratuitement", "free", "sans frais", "entrée libre"]
            if not filters.get("is_free") and any(kw in query_lower for kw in free_keywords):
                filters["is_free"] = True
                logger.info("[FILTER-INFER] Detected free event from keywords")

            # 4. DETECT AUDIENCE from query keywords
            # If LLM missed audience keywords, detect them
            if not filters.get("audience"):
                audience_patterns = {
                    "kids": ["enfant", "enfants", "kids", "children", "jeune public", "tout-petit"],
                    "family": ["famille", "familial", "family", "pour tous"],
                    "professional": ["professionnel", "professional", "pro", "b2b"],
                }
                for audience_type, keywords in audience_patterns.items():
                    if any(kw in query_lower for kw in keywords):
                        filters["audience"] = audience_type
                        logger.info(f"[FILTER-INFER] Detected audience '{audience_type}' from keywords")
                        break

            # 5. DETECT CATEGORY from query keywords (fallback if event_type was also missed)
            # This handles cases where LLM extracted neither event_type nor category
            if not filters.get("category"):
                # Command phrases that should NOT trigger category detection
                # "show me events" = display command, NOT theatre show
                command_phrases = ["show me", "show all", "show the", "shows me", "display"]
                is_command_phrase = any(phrase in query_lower for phrase in command_phrases)

                for keyword, db_category in CATEGORY_MAPPING.items():
                    # Skip "show/shows" if it's part of a command phrase
                    if keyword in ("show", "shows") and is_command_phrase:
                        continue

                    # Use word boundary matching to avoid partial matches
                    # e.g., "showcase" shouldn't match "show"
                    pattern = r"\b" + re.escape(keyword) + r"\b"
                    if re.search(pattern, query_lower):
                        filters["category"] = db_category
                        logger.info(f"[FILTER-INFER] Detected category '{db_category}' from keyword '{keyword}'")
                        break

            # ========================================
            # VALIDATE DATE CALCULATIONS (code-level correction)
            # ========================================
            # LLMs can struggle with date arithmetic. Validate weekend calculations.
            timeframe_raw = entities.get("timeframe_raw", "")
            if filters.get("day") and filters.get("month") and timeframe_raw:
                year = filters.get("year", date.today().year)
                filters["day"] = validate_and_correct_weekend(
                    day_value=filters["day"], month=filters["month"], year=year, timeframe_raw=timeframe_raw
                )

            # ========================================
            # MAP CATEGORY TO DB FORMAT (code-level normalization)
            # ========================================
            # LLM extracts user-friendly terms like "concert", but DB uses "Musique"
            if filters.get("category"):
                original_category = filters["category"]
                filters["category"] = map_category_to_db(original_category)
                if filters["category"] != original_category:
                    logger.info(f"[CATEGORY MAP] '{original_category}' → '{filters['category']}'")

            # Parse dimensions into QueryDimension objects
            dimensions: Dict[str, QueryDimension] = {}

            # Greeting dimension
            greeting_data = raw_dimensions.get("greeting", {})
            dimensions["greeting"] = QueryDimension(
                name="greeting",
                detected=greeting_data.get("detected", False),
                value=greeting_data.get("value"),
                action="prefix_response" if greeting_data.get("detected") else None,
            )

            # Typo dimension
            typo_data = raw_dimensions.get("typo", {})
            dimensions["typo"] = QueryDimension(
                name="typo",
                detected=typo_data.get("detected", False),
                original=typo_data.get("original"),
                value=typo_data.get("corrected"),
                action="acknowledge_correction" if typo_data.get("detected") else None,
            )

            # Statistical dimension
            stat_data = raw_dimensions.get("statistical", {})
            dimensions["statistical"] = QueryDimension(
                name="statistical",
                detected=stat_data.get("detected", False),
                value=stat_data.get("type"),
                action="return_count" if stat_data.get("detected") else None,
            )

            # Scope dimension
            scope_data = raw_dimensions.get("scope", {})
            dimensions["scope"] = QueryDimension(
                name="scope",
                detected=scope_data.get("detected", False),
                value=scope_data.get("value"),
                action="no_event_type_filter" if scope_data.get("value") == "all" else None,
            )

            # Determine completeness based on dimensions
            is_complete = result.get("is_complete", False)
            missing_criteria = result.get("missing", [])

            # VALIDATION: Ensure city_normalized is actually in known cities list
            # The LLM might hallucinate a city name that's not in our database
            city_normalized = entities.get("city_normalized")
            if city_normalized and known_cities:
                # Normalize for comparison (lowercase)
                known_cities_lower = [c.lower() for c in known_cities]
                if city_normalized.lower() not in known_cities_lower:
                    logger.warning(
                        f"[MULTI-DIM] LLM hallucinated city '{city_normalized}' - not in known cities, setting to None"
                    )
                    city_normalized = None
                    entities["city_normalized"] = None

            # ========================================
            # COMPLETENESS: 2 OUT OF 3 RULE
            # ========================================
            # A query is complete if it has at least 2 of these 3 criteria:
            # 1. city (location)
            # 2. timeframe (user-specified date/month/period)
            # 3. event_type (what kind of event)

            has_city = city_normalized is not None
            has_timeframe = (
                filters.get("month") is not None or filters.get("day") is not None or filters.get("year") is not None
            )
            has_event_type = entities.get("event_type") is not None

            criteria_count = sum([has_city, has_timeframe, has_event_type])

            # Log criteria status
            logger.info(
                f"[COMPLETENESS] city={has_city}, timeframe={has_timeframe}, "
                f"event_type={has_event_type} → {criteria_count}/3"
            )

            # 2 out of 3 criteria = COMPLETE
            if criteria_count >= 2:
                is_complete = True
                missing_criteria = []
                logger.info(f"[COMPLETENESS] Query is COMPLETE ({criteria_count}/3 criteria met)")
            else:
                is_complete = False
                # Determine what's missing
                missing_criteria = []
                if not has_city:
                    missing_criteria.append("city")
                if not has_timeframe:
                    missing_criteria.append("timeframe")
                if not has_event_type:
                    missing_criteria.append("event_type")
                logger.info(f"[COMPLETENESS] Query INCOMPLETE, missing: {missing_criteria}")

            # SPECIAL CASE: Statistical queries are always COMPLETE if city is present
            if dimensions["statistical"].detected and has_city:
                is_complete = True
                missing_criteria = []
                logger.info("[MULTI-DIM] Statistical query with city is COMPLETE (special case)")

            # SPECIAL CASE: "All events" scope with city is COMPLETE
            if dimensions["scope"].value == "all" and has_city:
                is_complete = True
                missing_criteria = []
                logger.info("[MULTI-DIM] 'All events' scope with city is COMPLETE (special case)")

            # SPECIAL CASE: Non-event intents are COMPLETE (no clarification needed)
            # Greetings, capability questions, directions, off-topic, etc. should NOT trigger clarification
            if intent_str in ["greeting", "chitchat", "capability", "directions", "off_topic", "abuse"]:
                is_complete = True
                missing_criteria = []
                logger.info(f"[MULTI-DIM] Non-event intent '{intent_str}' is COMPLETE (no clarification needed)")

            # Extract detected language (default to "fr" if not present)
            detected_language = result.get("detected_language", "fr")
            if detected_language not in ["fr", "en"]:
                detected_language = "fr"  # Normalize to valid values

            analysis = UnifiedAnalysisResult(
                intent=intent_map.get(intent_str, QueryIntent.EVENT_SEARCH),
                intent_confidence=float(result.get("intent_confidence", 0.8)),
                dimensions=dimensions,
                detected_language=detected_language,
                city=entities.get("city_raw"),
                city_normalized=city_normalized,  # Use validated value
                event_type=entities.get("event_type"),
                timeframe=entities.get("timeframe_raw"),
                is_complete=is_complete,
                missing_criteria=missing_criteria,
                filters=filters,
                refined_query=result.get("refined_query", query),
                raw_response=result,
            )

            # Enhanced logging with dimensions
            dim_summary = ", ".join([f"{k}={v.detected}" for k, v in dimensions.items() if v.detected]) or "none"
            logger.info(
                f"[MULTI-DIM] Query: '{query[:40]}...' → "
                f"intent={analysis.intent.value}, "
                f"lang={analysis.detected_language}, "
                f"city={analysis.city_normalized}, "
                f"complete={analysis.is_complete}, "
                f"dims=[{dim_summary}]"
            )

            return analysis

        except RetryError as e:
            # All retry attempts exhausted for rate limit error
            logger.error(f"[UNIFIED] Analysis failed after all retries (rate limit): {e.last_attempt.exception()}")

            # Try Mistral fallback before returning empty defaults
            logger.info("[UNIFIED] Primary LLM exhausted, trying Mistral fallback...")
            try:
                # Rebuild messages if needed (may have been built successfully)
                today = date.today()
                system_prompt = get_unified_analysis_prompt(today, known_cities or [])
                fallback_messages = [SystemMessage(content=system_prompt), HumanMessage(content=f"Query: {query}")]
                result = self._try_mistral_fallback(query, fallback_messages)
                if result:
                    # Use the Mistral result with basic processing
                    return self._build_result_from_dict(query, result, known_cities)
            except Exception as fallback_e:
                logger.warning(f"[UNIFIED] Mistral fallback also failed: {fallback_e}")

            # Fall back to basic keyword extraction
            logger.info("[UNIFIED] Using basic keyword extraction as last resort")
            basic_result = self._fallback_extraction(query, "")
            return self._build_result_from_dict(query, basic_result, known_cities)

        except Exception as e:
            # Check if it's a rate limit error that wasn't caught by retry
            is_rate_limit = is_rate_limit_error(e)
            if is_rate_limit:
                logger.error(f"[UNIFIED] Analysis failed (rate limit): {e}")
            else:
                logger.error(f"[UNIFIED] Analysis failed: {e}", exc_info=True)

            # Try Mistral fallback before returning empty defaults
            logger.info("[UNIFIED] Primary LLM failed, trying Mistral fallback...")
            try:
                today = date.today()
                system_prompt = get_unified_analysis_prompt(today, known_cities or [])
                fallback_messages = [SystemMessage(content=system_prompt), HumanMessage(content=f"Query: {query}")]
                result = self._try_mistral_fallback(query, fallback_messages)
                if result:
                    return self._build_result_from_dict(query, result, known_cities)
            except Exception as fallback_e:
                logger.warning(f"[UNIFIED] Mistral fallback also failed: {fallback_e}")

            # Fall back to basic keyword extraction
            logger.info("[UNIFIED] Using basic keyword extraction as last resort")
            basic_result = self._fallback_extraction(query, "")
            return self._build_result_from_dict(query, basic_result, known_cities)


# Global singleton
_analyzer: Optional[UnifiedAnalyzer] = None


def get_unified_analyzer() -> UnifiedAnalyzer:
    """Get or create the global UnifiedAnalyzer instance."""
    global _analyzer
    if _analyzer is None:
        _analyzer = UnifiedAnalyzer()
    return _analyzer


# ========================================
# ANALYSIS CACHE (reduces API calls)
# ========================================
_ANALYSIS_CACHE: Dict[str, Tuple[UnifiedAnalysisResult, float]] = {}
_ANALYSIS_CACHE_TTL = 300  # 5 minutes
_ANALYSIS_CACHE_MAX_SIZE = 100


def unified_analyze(
    query: str,
    chat_history: List[BaseMessage] = None,
    known_cities: List[str] = None,
    previous_events: list[dict] | None = None,
) -> UnifiedAnalysisResult:
    """Convenience function for unified analysis with caching.

    Args:
        query: User's input query
        chat_history: Optional chat history for context
        known_cities: List of valid IDF cities
        previous_events: Optional list of events from previous response (for coreference)

    Returns:
        UnifiedAnalysisResult with all extracted information
    """
    # Create cache key from query (normalized)
    cache_key = query.lower().strip()

    # Check cache (only for queries without context or previous events)
    if (chat_history is None or len(chat_history) == 0) and previous_events is None:
        if cache_key in _ANALYSIS_CACHE:
            cached_result, cached_time = _ANALYSIS_CACHE[cache_key]
            if time.time() - cached_time < _ANALYSIS_CACHE_TTL:
                logger.info(f"[UNIFIED-CACHE] HIT for query: {query[:30]}...")
                return cached_result
            else:
                del _ANALYSIS_CACHE[cache_key]

    # Cache miss - run analysis
    analyzer = get_unified_analyzer()
    result = analyzer.analyze(query, chat_history, known_cities, previous_events=previous_events)

    # Language consistency check: Override if user has been consistently using one language
    if chat_history and len(chat_history) >= 2:
        # Extract last 3-5 user queries (not assistant responses)
        recent_user_queries = [
            msg.content for msg in chat_history[-10:] if hasattr(msg, "type") and msg.type == "human"
        ][
            -5:
        ]  # Last 5 user queries

        if len(recent_user_queries) >= 2:
            # Simple heuristic: Check for English vs French indicators
            english_count = sum(
                1
                for q in recent_user_queries
                if any(word in q.lower() for word in [" in ", " at ", " on ", " this ", " what ", " how ", " the "])
            )
            french_count = sum(
                1
                for q in recent_user_queries
                if any(word in q.lower() for word in [" à ", " de ", " le ", " la ", " les ", " du ", " en ", " pour "])
            )

            # If user has been consistently using English (>= 2 recent queries), override to English
            if english_count >= 2 and english_count > french_count:
                if result.detected_language == "fr":
                    logger.info(
                        f"[LANGUAGE-CONSISTENCY] Overriding detected_language: fr → en (user pattern: {english_count} EN vs {french_count} FR)"
                    )
                    result.detected_language = "en"
            # If user has been consistently using French, ensure it stays French
            elif french_count >= 2 and french_count > english_count:
                if result.detected_language == "en":
                    logger.info(
                        f"[LANGUAGE-CONSISTENCY] Overriding detected_language: en → fr (user pattern: {french_count} FR vs {english_count} EN)"
                    )
                    result.detected_language = "fr"

    # Store in cache (only for single-turn queries)
    if chat_history is None or len(chat_history) == 0:
        # Evict oldest if full
        if len(_ANALYSIS_CACHE) >= _ANALYSIS_CACHE_MAX_SIZE:
            oldest_key = min(_ANALYSIS_CACHE.keys(), key=lambda k: _ANALYSIS_CACHE[k][1])
            del _ANALYSIS_CACHE[oldest_key]
        _ANALYSIS_CACHE[cache_key] = (result, time.time())
        logger.info(f"[UNIFIED-CACHE] STORED for query: {query[:30]}...")

    return result
