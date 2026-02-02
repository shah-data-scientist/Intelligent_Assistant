"""LLM-based entity extraction for robust query understanding.

This module provides intelligent entity extraction using an LLM to handle
cases where keyword/regex matching fails:
- City name normalization (Plessis → Plessis-Robinson)
- Location extraction from varied prepositions (near, around, close to)
- Query completeness analysis

These LLM calls are FALLBACKS - only invoked when simpler methods fail.
Note: Primary entity extraction is handled by UnifiedAnalyzer.
"""

import json
import logging
from typing import Optional, Dict, Any, List, Tuple

from langchain_mistralai import ChatMistralAI
from langchain_core.messages import HumanMessage, SystemMessage

from src.config import settings

logger = logging.getLogger(__name__)


# ========================================
# LLM CITY NORMALIZER
# ========================================
# Fixes: "Plessis" → "Plessis-Robinson", "Boulogne" → "Boulogne-Billancourt"

CITY_NORMALIZER_PROMPT = """You are a city name resolver for Île-de-France (Paris region).

Given a user's city input, find the EXACT matching city from this list:
{known_cities}

RULES:
1. Match partial names to full official names (e.g., "Plessis" → "Le Plessis-Robinson")
2. Handle typos (e.g., "Possy" → "Poissy", "Versaille" → "Versailles")
3. Handle variations (e.g., "Saint Ouen" → "Saint-Ouen-sur-Seine")
4. If NO match is possible, return null

Respond with ONLY a JSON object:
{{"city": "exact-city-name" or null, "confidence": 0.0-1.0}}
"""


class EntityExtractor:
    """LLM-based entity extractor for query understanding."""

    def __init__(self, model: str = "mistral-small-latest"):
        """Initialize the entity extractor.

        Args:
            model: Mistral model to use (default: mistral-small-latest for speed)
        """
        self.model = model
        self.llm = ChatMistralAI(
            model=model,
            api_key=settings.mistral_api_key,
            temperature=0.0,
            max_tokens=100,
        )
        logger.info(f"Initialized EntityExtractor with model: {model}")

    def normalize_city(self, city_input: str, known_cities: List[str]) -> Tuple[Optional[str], float]:
        """Normalize a city name using LLM understanding.

        This is a FALLBACK when fuzzy matching fails (<0.75 threshold).
        Handles compound French city names like:
        - "Plessis" → "Le Plessis-Robinson"
        - "Boulogne" → "Boulogne-Billancourt"
        - "Saint Ouen" → "Saint-Ouen-sur-Seine"

        Args:
            city_input: The user's city input (possibly partial/typo)
            known_cities: List of valid city names from database

        Returns:
            Tuple of (normalized_city, confidence) or (None, 0.0)
        """
        try:
            # Limit city list to avoid token overflow (sample most relevant)
            # Sort cities to prioritize those starting with same letters
            prefix = city_input[:3].lower() if len(city_input) >= 3 else city_input.lower()
            relevant_cities = [c for c in known_cities if c.lower().startswith(prefix)]
            other_cities = [c for c in known_cities if not c.lower().startswith(prefix)]

            # Include relevant + sample of others (max 100 cities)
            sampled_cities = relevant_cities[:50] + other_cities[:50]
            cities_str = ", ".join(sampled_cities)

            prompt = CITY_NORMALIZER_PROMPT.format(known_cities=cities_str)
            messages = [SystemMessage(content=prompt), HumanMessage(content=f"User input: {city_input}")]

            response = self.llm.invoke(messages)
            content = response.content.strip()

            # Parse JSON response
            if "```" in content:
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()

            result = json.loads(content)
            city = result.get("city")
            confidence = float(result.get("confidence", 0.0))

            if city:
                logger.info(f"[LLM-CITY] Normalized '{city_input}' → '{city}' (confidence: {confidence:.2f})")
            else:
                logger.info(f"[LLM-CITY] No match found for '{city_input}'")

            return city, confidence

        except Exception as e:
            logger.warning(f"[LLM-CITY] Normalization failed: {e}")
            return None, 0.0


# ========================================
# LLM LOCATION EXTRACTOR
# ========================================
# Fixes: "near Paris", "around Versailles", "close to Paris"

LOCATION_EXTRACTOR_PROMPT = """You are a location extractor for cultural event queries.

Extract the city name from the query. Handle ALL prepositions:
- "in Paris" → Paris
- "near Paris" → Paris
- "around Versailles" → Versailles
- "close to Montreuil" → Montreuil
- "from Saint-Denis" → Saint-Denis
- "at the Louvre in Paris" → Paris

RULES:
1. Extract ONLY city names (not venues, neighborhoods, or landmarks)
2. If multiple cities mentioned, return the PRIMARY search location
3. If NO city mentioned, return null
4. Ignore words that look like cities but aren't (e.g., "Nice weather" → NOT a city)

Respond with ONLY a JSON object:
{{"city": "city-name" or null, "preposition": "in|near|around|at|from|null"}}
"""


def extract_location_from_query(query: str) -> Tuple[Optional[str], Optional[str]]:
    """Extract location from query using LLM (handles all prepositions).

    This REPLACES the regex-based detection in chain.py which only handles
    "in", "a", "à", "at" patterns. LLM handles:
    - "near Paris"
    - "around Versailles"
    - "close to Montreuil"
    - "events from Saint-Denis"

    Args:
        query: The user's query

    Returns:
        Tuple of (city_name, preposition) or (None, None)
    """
    try:
        llm = ChatMistralAI(
            model="mistral-small-latest",
            api_key=settings.mistral_api_key,
            temperature=0.0,
            max_tokens=50,
        )

        messages = [SystemMessage(content=LOCATION_EXTRACTOR_PROMPT), HumanMessage(content=f"Query: {query}")]

        response = llm.invoke(messages)
        content = response.content.strip()

        # Parse JSON
        if "```" in content:
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()

        result = json.loads(content)
        city = result.get("city")
        preposition = result.get("preposition")

        if city:
            logger.info(f"[LLM-LOCATION] Extracted '{city}' from '{query[:40]}...' (prep: {preposition})")

        return city, preposition

    except Exception as e:
        logger.warning(f"[LLM-LOCATION] Extraction failed: {e}")
        return None, None


# ========================================
# LLM QUERY COMPLETENESS ANALYZER (FALLBACK)
# ========================================
# Note: Primary completeness check is done by UnifiedAnalyzer (2-out-of-3 rule)
# This is a fallback for edge cases where UnifiedAnalyzer fails

COMPLETENESS_ANALYZER_PROMPT = """Analyze this cultural event search query for completeness.

A COMPLETE query for event search needs:
1. **Location** - A city name (Paris, Versailles, Montreuil, etc.) OR region (Île-de-France)
2. **Event type** - What kind of event (concert, exhibition, theater, festival, workshop, etc.)
3. **Timeframe** - When (this weekend, February, tomorrow, next month, etc.)

NOTE: Date is OPTIONAL if both location AND event type are present.

Analyze the query and determine what's missing (if anything).

Respond with ONLY a JSON object:
{{
  "has_location": true/false,
  "has_event_type": true/false,
  "has_timeframe": true/false,
  "detected_location": "city-name" or null,
  "detected_event_type": "type" or null,
  "detected_timeframe": "when" or null,
  "is_complete": true/false,
  "missing": ["location", "event_type", "timeframe"] or []
}}
"""


def analyze_query_completeness(query: str, chat_history: List[Any] = None) -> Dict[str, Any]:
    """Analyze query completeness using LLM (FALLBACK).

    Note: Primary completeness analysis is done by UnifiedAnalyzer.
    This function is a fallback for edge cases.

    Args:
        query: The user's query
        chat_history: Optional chat history for context

    Returns:
        Dict with completeness analysis
    """
    try:
        llm = ChatMistralAI(
            model="mistral-small-latest",
            api_key=settings.mistral_api_key,
            temperature=0.0,
            max_tokens=150,
        )

        # Include recent history context if available
        history_context = ""
        if chat_history:
            recent = chat_history[-3:] if len(chat_history) > 3 else chat_history
            history_context = "\n\nPrevious conversation context:\n"
            for msg in recent:
                if hasattr(msg, "content"):
                    history_context += f"- {msg.content[:100]}...\n"

        messages = [
            SystemMessage(content=COMPLETENESS_ANALYZER_PROMPT),
            HumanMessage(content=f"Query: {query}{history_context}"),
        ]

        response = llm.invoke(messages)
        content = response.content.strip()

        # Parse JSON
        if "```" in content:
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()

        result = json.loads(content)

        logger.info(
            f"[LLM-COMPLETE] Query '{query[:30]}...' -> complete={result.get('is_complete')}, missing={result.get('missing')}"
        )

        return result

    except Exception as e:
        logger.warning(f"[LLM-COMPLETE] Analysis failed: {e}")
        # Default: assume incomplete to be safe
        return {
            "has_location": False,
            "has_event_type": False,
            "has_timeframe": False,
            "is_complete": False,
            "missing": ["location", "event_type", "timeframe"],
        }


# Global singleton for reuse
_extractor: Optional[EntityExtractor] = None


def get_entity_extractor() -> EntityExtractor:
    """Get or create the global EntityExtractor instance."""
    global _extractor
    if _extractor is None:
        _extractor = EntityExtractor()
    return _extractor
