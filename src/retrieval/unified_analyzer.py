"""Unified LLM analyzer with MULTI-DIMENSIONAL classification.

This module consolidates multiple LLM calls into a SINGLE unified call:

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
from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

from langchain_mistralai import ChatMistralAI
from langchain_core.messages import HumanMessage, SystemMessage, BaseMessage

from src.config import settings
import calendar
import re

logger = logging.getLogger(__name__)


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
    """Map user-friendly category term to database category name."""
    if not category:
        return None
    category_lower = category.lower().strip()
    mapped = CATEGORY_MAPPING.get(category_lower)
    if mapped:
        logger.debug(f"[CATEGORY MAP] '{category}' → '{mapped}'")
        return mapped
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
    weekend_match = re.search(r'(first|second|third|fourth|last|1st|2nd|3rd|4th)\s+weekend', timeframe_lower)
    if not weekend_match:
        return day_value  # Not a weekend query, trust LLM

    ordinal = weekend_match.group(1)
    ordinal_map = {'first': 1, '1st': 1, 'second': 2, '2nd': 2, 'third': 3, '3rd': 3, 'fourth': 4, '4th': 4, 'last': -1}
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
    ABUSE = "abuse"
    OFF_TOPIC = "off_topic"


@dataclass
class QueryDimension:
    """A single dimension of query classification."""
    name: str                    # Dimension name (greeting, typo, statistical, etc.)
    detected: bool               # Whether this dimension was detected
    value: Optional[str] = None  # Extracted value (e.g., corrected city name)
    original: Optional[str] = None  # Original value before correction
    action: Optional[str] = None  # Action to take (acknowledge, count, filter, etc.)
    confidence: float = 1.0      # Confidence in this dimension


@dataclass
class UnifiedAnalysisResult:
    """Result from unified query analysis with multi-dimensional support."""
    # Primary intent (for backward compatibility)
    intent: QueryIntent
    intent_confidence: float

    # MULTI-DIMENSIONAL CLASSIFICATIONS
    dimensions: Dict[str, QueryDimension] = field(default_factory=dict)

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
    cities_sample = known_cities[:100] if len(known_cities) > 100 else known_cities
    cities_str = ", ".join(cities_sample)

    return f"""You are a query analyzer using MULTI-DIMENSIONAL classification.

A query can have MULTIPLE dimensions simultaneously. Analyze ALL dimensions independently.

---

## DIMENSION ANALYSIS

Analyze the query across these INDEPENDENT dimensions:

### 1. PRIMARY INTENT (required)
| Intent | Description |
|--------|-------------|
| greeting | Saying hello (hi, bonjour, salut) |
| chitchat | Casual conversation NOT about events (how are you, ça va) |
| capability | Asking what you can do (help, what can you do) |
| abuse | Insults or inappropriate content |
| off_topic | Unrelated to events (weather, math) |
| event_search | Wants cultural events |

### 2. GREETING DIMENSION
Does the query START with a greeting? (can coexist with event_search)
- "hello, I'm looking for concerts" → greeting=true, intent=event_search

### 3. TYPO DIMENSION
Did the user make a spelling error that you corrected?
- "Possy" → corrected to "Poissy"
- "Versaille" → corrected to "Versailles"

### 4. STATISTICAL DIMENSION
Is the user asking for a COUNT or statistics?
Keywords: "how many", "combien", "count", "total", "number of"
- If statistical=true, user wants ALL matching events counted, not a specific type

### 5. SCOPE DIMENSION
Does the user want ALL events or a specific type?
- "all events", "any events", "everything", "tous les événements", "n'importe quel événement" → scope="all"
- "if there are any events", "are there events", "y a-t-il des événements" → scope="all"
- "concerts", "jazz", "expositions" → scope="specific"
- If statistical=true AND no event_type specified → scope="all" (user wants total count)
- If NO specific event type mentioned → scope="all"

---

**TODAY'S DATE:** {today.strftime('%Y-%m-%d')} ({today.strftime('%A')})
**THIS WEEKEND:** {this_saturday.strftime('%B %d')} (Sat) and {this_sunday.strftime('%B %d')} (Sun)
**KNOWN IDF CITIES:** {cities_str}

---

## OUTPUT FORMAT (JSON only):

```json
{{
  "intent": "greeting|chitchat|capability|abuse|off_topic|event_search",
  "intent_confidence": 0.0-1.0,

  "dimensions": {{
    "greeting": {{
      "detected": true/false,
      "value": "the greeting phrase" or null
    }},
    "typo": {{
      "detected": true/false,
      "original": "what user typed" or null,
      "corrected": "corrected value" or null
    }},
    "statistical": {{
      "detected": true/false,
      "type": "count|total|summary" or null
    }},
    "scope": {{
      "detected": true/false,
      "value": "all|specific" or null
    }}
  }},

  "entities": {{
    "city_raw": "what user said" or null,
    "city_normalized": "official city name" or null,
    "event_type": "concert|exhibition|theater|festival|etc" or null,
    "timeframe_raw": "what user said" or null,
    "timeframe_resolved": {{"month": 1-12, "day": int/list, "year": int}}
  }},

  "is_complete": true/false,
  "missing": ["city", "event_type", "timeframe"],

  "filters": {{
    "city": "normalized city" or null,
    "month": int or null,
    "day": int or [list] or null,
    "year": int or null,
    "category": null,
    "is_free": true or null,
    "audience": "kids|family|professional" or null
  }},

  "refined_query": "typo-corrected search query"
}}
```

---

## CRITICAL RULES:

1. **GREETING + EVENT_SEARCH CAN COEXIST:**
   - "good morning, any concerts in Paris?" → intent=event_search, dimensions.greeting.detected=true

2. **STATISTICAL QUERIES ARE COMPLETE:**
   - "how many events in Poissy in January" → is_complete=true (no event_type needed!)
   - User wants COUNT of ALL events, don't ask for event type

3. **TYPO CORRECTION:**
   - "Possy" → city_raw="Possy", city_normalized="Poissy", dimensions.typo.detected=true

4. **NON-EVENT INTENTS (greeting, chitchat, capability, abuse, off_topic):**
   - Set is_complete=false, missing=[], dimensions as detected

5. **COMPLETENESS FOR EVENT_SEARCH (2 out of 3 rule):**
   A query is COMPLETE if it has **at least 2 of these 3 criteria**:
   - city (location specified)
   - timeframe (date/month/period specified by user)
   - event_type (what kind of event: concert, exhibition, theater, etc.)

   Examples:
   - "concerts in Paris" → city + event_type → COMPLETE
   - "events in March in Paris" → city + timeframe → COMPLETE
   - "concerts in February" → event_type + timeframe → COMPLETE
   - "events in Paris" → only city → INCOMPLETE (ask for timeframe or event_type)

6. **CONTEXT CARRYOVER (CRITICAL for follow-up queries):**
   If there is PREVIOUS CONVERSATION, carry forward filters that are NOT explicitly changed:
   - User says "Poissy would be better" → REPLACE city, but KEEP timeframe and audience from context
   - User says "maybe jazz instead" → REPLACE event_type, but KEEP city and timeframe from context
   - User says "make it this weekend" → REPLACE timeframe, but KEEP city and event_type from context

   **Rule:** Only replace what the user explicitly mentions. Preserve everything else from the previous query.

   Example:
   - Previous: "events in Paris for second weekend of March for professional reasons"
   - Follow-up: "Poissy would be better. Maybe jazz!"
   - Result: city=Poissy (changed), event_type=jazz (added), timeframe=second weekend of March (PRESERVED), audience=professional (PRESERVED)

---

## ENTITY EXTRACTION RULES:

1. **CITY NORMALIZATION:** Normalize to official names from the known cities list
2. **AUDIENCE:** "for kids/enfants" → audience="kids", "professional" → audience="professional"
3. **RELATIVE DATE CALCULATION:**
   Use TODAY'S DATE above to calculate any relative date expression:
   - "this weekend", "next weekend", "second weekend of March"
   - "next Tuesday", "this Friday", "coming Monday"
   - "first Monday of May", "last day of the month"
   - "in 2 weeks", "next month"

   **RULES:**
   - A weekend = Saturday + Sunday (2 consecutive days)
   - Return day as a single int OR a list [day1, day2] for date ranges

4. **OTHER DATES:**
   - "today" → month={today.month}, day={today.day}
   - "this weekend" → month={this_saturday.month}, day=[{this_saturday.day}, {this_sunday.day}]
   - "in January" → month=1
   - "next week" → calculate actual dates

---

**REMEMBER:** A query can have MULTIPLE dimensions. Analyze each independently.
"""


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

    def __init__(self, model: str = "mistral-small-latest"):
        """Initialize the unified analyzer.

        Args:
            model: Mistral model to use (default: mistral-small for speed)
        """
        self.model = model
        self.llm = ChatMistralAI(
            model=model,
            api_key=settings.mistral_api_key,
            temperature=0.0,
            max_tokens=500,
        )
        logger.info(f"Initialized UnifiedAnalyzer with model: {model}")

    def analyze(
        self,
        query: str,
        chat_history: List[BaseMessage] = None,
        known_cities: List[str] = None
    ) -> UnifiedAnalysisResult:
        """Analyze query in one unified LLM call with MULTI-DIMENSIONAL output.

        Args:
            query: User's input query
            chat_history: Optional chat history for context
            known_cities: List of valid IDF cities for normalization

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

            messages.append(HumanMessage(content=f"Query: {query}"))

            # Invoke LLM
            response = self.llm.invoke(messages)
            content = response.content.strip()

            # Parse JSON response
            if "```" in content:
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()

            result = json.loads(content)

            # Map intent to enum
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
            raw_dimensions = result.get("dimensions", {})

            # ========================================
            # VALIDATE DATE CALCULATIONS (code-level correction)
            # ========================================
            # LLMs can struggle with date arithmetic. Validate weekend calculations.
            timeframe_raw = entities.get("timeframe_raw", "")
            if filters.get("day") and filters.get("month") and timeframe_raw:
                year = filters.get("year", date.today().year)
                filters["day"] = validate_and_correct_weekend(
                    day_value=filters["day"],
                    month=filters["month"],
                    year=year,
                    timeframe_raw=timeframe_raw
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
                action="prefix_response" if greeting_data.get("detected") else None
            )

            # Typo dimension
            typo_data = raw_dimensions.get("typo", {})
            dimensions["typo"] = QueryDimension(
                name="typo",
                detected=typo_data.get("detected", False),
                original=typo_data.get("original"),
                value=typo_data.get("corrected"),
                action="acknowledge_correction" if typo_data.get("detected") else None
            )

            # Statistical dimension
            stat_data = raw_dimensions.get("statistical", {})
            dimensions["statistical"] = QueryDimension(
                name="statistical",
                detected=stat_data.get("detected", False),
                value=stat_data.get("type"),
                action="return_count" if stat_data.get("detected") else None
            )

            # Scope dimension
            scope_data = raw_dimensions.get("scope", {})
            dimensions["scope"] = QueryDimension(
                name="scope",
                detected=scope_data.get("detected", False),
                value=scope_data.get("value"),
                action="no_event_type_filter" if scope_data.get("value") == "all" else None
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
                    logger.warning(f"[MULTI-DIM] LLM hallucinated city '{city_normalized}' - not in known cities, setting to None")
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
                filters.get("month") is not None or
                filters.get("day") is not None or
                filters.get("year") is not None
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

            analysis = UnifiedAnalysisResult(
                intent=intent_map.get(intent_str, QueryIntent.EVENT_SEARCH),
                intent_confidence=float(result.get("intent_confidence", 0.8)),
                dimensions=dimensions,
                city=entities.get("city_raw"),
                city_normalized=city_normalized,  # Use validated value
                event_type=entities.get("event_type"),
                timeframe=entities.get("timeframe_raw"),
                is_complete=is_complete,
                missing_criteria=missing_criteria,
                filters=filters,
                refined_query=result.get("refined_query", query),
                raw_response=result
            )

            # Enhanced logging with dimensions
            dim_summary = ", ".join([
                f"{k}={v.detected}" for k, v in dimensions.items() if v.detected
            ]) or "none"
            logger.info(
                f"[MULTI-DIM] Query: '{query[:40]}...' → "
                f"intent={analysis.intent.value}, "
                f"city={analysis.city_normalized}, "
                f"complete={analysis.is_complete}, "
                f"dims=[{dim_summary}]"
            )

            return analysis

        except Exception as e:
            logger.error(f"[UNIFIED] Analysis failed: {e}", exc_info=True)
            # Return safe defaults with empty dimensions
            return UnifiedAnalysisResult(
                intent=QueryIntent.EVENT_SEARCH,
                intent_confidence=0.5,
                dimensions={
                    "greeting": QueryDimension("greeting", False),
                    "typo": QueryDimension("typo", False),
                    "statistical": QueryDimension("statistical", False),
                    "scope": QueryDimension("scope", False),
                },
                city=None,
                city_normalized=None,
                event_type=None,
                timeframe=None,
                is_complete=False,
                missing_criteria=["city", "event_type"],
                filters={},
                refined_query=query,
                raw_response={}
            )


# Global singleton
_analyzer: Optional[UnifiedAnalyzer] = None


def get_unified_analyzer() -> UnifiedAnalyzer:
    """Get or create the global UnifiedAnalyzer instance."""
    global _analyzer
    if _analyzer is None:
        _analyzer = UnifiedAnalyzer()
    return _analyzer


def unified_analyze(query: str, chat_history: List[BaseMessage] = None, known_cities: List[str] = None) -> UnifiedAnalysisResult:
    """Convenience function for unified analysis.

    Args:
        query: User's input query
        chat_history: Optional chat history for context
        known_cities: List of valid IDF cities

    Returns:
        UnifiedAnalysisResult with all extracted information
    """
    analyzer = get_unified_analyzer()
    return analyzer.analyze(query, chat_history, known_cities)
