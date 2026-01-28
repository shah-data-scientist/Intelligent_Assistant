"""LLM-based intent classifier for robust query understanding.

This module provides intent classification using an LLM to determine
the user's intent before processing the query. This is more robust
than keyword-based detection as it handles:
- Variations in phrasing
- New conversational patterns
- Context-dependent intent
- Multilingual queries

Intents:
- event_search: User wants to find cultural events
- greeting: User is greeting the assistant
- chitchat: Casual conversation (how are you, what's up)
- capability: User asking what the assistant can do
- abuse: Insults or inappropriate content
- off_topic: Questions outside cultural events scope
"""

import json
import logging
from enum import Enum
from typing import Optional, Tuple
from functools import lru_cache

from langchain_mistralai import ChatMistralAI
from langchain_core.messages import HumanMessage, SystemMessage

from src.config import settings

logger = logging.getLogger(__name__)


class QueryIntent(Enum):
    """Possible user query intents."""
    EVENT_SEARCH = "event_search"
    GREETING = "greeting"
    CHITCHAT = "chitchat"
    CAPABILITY = "capability"
    ABUSE = "abuse"
    OFF_TOPIC = "off_topic"


# System prompt for intent classification
INTENT_CLASSIFIER_PROMPT = """You are an intent classifier for a cultural events chatbot in Ile-de-France (Paris region).

Classify the user's query into ONE of these intents:
- **event_search**: User wants to find cultural events (concerts, exhibitions, theater, festivals, shows, workshops)
- **greeting**: User is greeting (hello, hi, bonjour, salut, hey)
- **chitchat**: Casual conversation NOT about events (how are you, what's up, how do you do, ca va)
- **capability**: User asking what you can do (help, what can you do, how do you work)
- **abuse**: Insults, profanity, or inappropriate content (idiot, stupid, f*ck)
- **off_topic**: Questions outside cultural events (weather, recipes, math, translation, news)

IMPORTANT RULES:
1. "how are you" is CHITCHAT, not event_search
2. "what can you do" is CAPABILITY, not event_search
3. Short phrases without event keywords are likely chitchat/greeting
4. If query mentions cities, dates, OR event types, it's likely event_search
5. When in doubt between chitchat and event_search, choose chitchat for very short queries

Respond with ONLY a JSON object:
{"intent": "event_search|greeting|chitchat|capability|abuse|off_topic", "confidence": 0.0-1.0}
"""


class IntentClassifier:
    """LLM-based intent classifier for query understanding."""

    def __init__(self, model: str = "mistral-small-latest"):
        """Initialize the intent classifier.

        Args:
            model: Mistral model to use (default: mistral-small-latest for speed)
        """
        self.model = model
        self.llm = ChatMistralAI(
            model=model,
            api_key=settings.mistral_api_key,
            temperature=0.0,  # Deterministic for consistency
            max_tokens=50,  # Intent classification is short
        )
        logger.info(f"Initialized IntentClassifier with model: {model}")

    def classify(self, query: str) -> Tuple[QueryIntent, float]:
        """Classify the intent of a user query.

        Args:
            query: The user's query text

        Returns:
            Tuple of (QueryIntent, confidence_score)
        """
        try:
            messages = [
                SystemMessage(content=INTENT_CLASSIFIER_PROMPT),
                HumanMessage(content=f"Query: {query}")
            ]

            response = self.llm.invoke(messages)
            content = response.content.strip()

            # Parse JSON response
            # Handle potential markdown code blocks
            if "```" in content:
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()

            result = json.loads(content)
            intent_str = result.get("intent", "event_search")
            confidence = float(result.get("confidence", 0.8))

            # Map string to enum
            intent_map = {
                "event_search": QueryIntent.EVENT_SEARCH,
                "greeting": QueryIntent.GREETING,
                "chitchat": QueryIntent.CHITCHAT,
                "capability": QueryIntent.CAPABILITY,
                "abuse": QueryIntent.ABUSE,
                "off_topic": QueryIntent.OFF_TOPIC,
            }

            intent = intent_map.get(intent_str, QueryIntent.EVENT_SEARCH)
            logger.info(f"[INTENT] Query: '{query[:50]}...' -> {intent.value} (confidence: {confidence:.2f})")

            return intent, confidence

        except json.JSONDecodeError as e:
            logger.warning(f"[INTENT] Failed to parse LLM response: {e}. Defaulting to event_search.")
            return QueryIntent.EVENT_SEARCH, 0.5
        except Exception as e:
            logger.error(f"[INTENT] Classification error: {e}. Defaulting to event_search.")
            return QueryIntent.EVENT_SEARCH, 0.5


# Global singleton for reuse
_classifier: Optional[IntentClassifier] = None


def get_intent_classifier() -> IntentClassifier:
    """Get or create the global IntentClassifier instance."""
    global _classifier
    if _classifier is None:
        _classifier = IntentClassifier()
    return _classifier


def classify_intent(query: str) -> Tuple[QueryIntent, float]:
    """Convenience function to classify intent using global classifier.

    Args:
        query: The user's query text

    Returns:
        Tuple of (QueryIntent, confidence_score)
    """
    classifier = get_intent_classifier()
    return classifier.classify(query)
