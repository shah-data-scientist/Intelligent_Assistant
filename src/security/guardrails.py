"""Security guardrails for the RAG system."""

import logging
import re

logger = logging.getLogger(__name__)

class SecurityException(ValueError):
    """Exception raised when a security guardrail is triggered."""
    pass

# Refusal message for inappropriate language
REFUSAL_MESSAGE = (
    "I cannot process your request because it contains inappropriate or abusive language. "
    "Please use respectful language when interacting with the assistant.\n\n"
    "Je ne peux pas traiter votre demande car elle contient un langage inapproprié ou abusif. "
    "Merci d'utiliser un langage respectueux lors de vos échanges avec l'assistant."
)

# Patterns indicative of prompt injection or malicious intent
MALICIOUS_PATTERNS = [
    r"ignore previous instructions",
    r"ignore all instructions",
    r"delete database",
    r"drop table",
    r"system override",
    r"you are now",  # Jailbreak attempt
    r"developer mode",
]

TOXIC_KEYWORDS = [
    # English
    "hate", "kill", "death", "stupid", "idiot", "dumb", "moron",
    "fuck", "shit", "asshole", "bitch", "damn", "cunt", "dick", "pussy",
    "bastard", "motherfucker", "cock", "slut", "whore", "rape", "sexist", "racist",
    # French
    "merde", "putain", "con", "connard", "salope", "abruti", "débile", "enculé", 
    "crétin", "va te faire", "nique", "pute", "bordel", "chier"
]

# Regex to catch variations like f u c k or f.u.c.k
PROFANITY_REGEX = r"(?i)\b(f[ \.\-_]*u[ \.\-_]*c[ \.\-_]*k|s[ \.\-_]*h[ \.\-_]*i[ \.\-_]*t|a[ \.\-_]*s[ \.\-_]*s|p[ \.\-_]*u[ \.\-_]*t[ \.\-_]*a[ \.\-_]*i[ \.\-_]*n|m[ \.\-_]*e[ \.\-_]*r[ \.\-_]*d[ \.\-_]*e)\b"

def check_safety(query: str) -> None:
    """Check if the query contains malicious patterns or toxic content.

    Args:
        query: User input string

    Raises:
        SecurityException: If safety check fails
    """
    query_lower = query.lower()

    # 1. Check for prompt injection patterns
    for pattern in MALICIOUS_PATTERNS:
        if re.search(pattern, query_lower):
            logger.warning(f"Blocked malicious query: {query}")
            raise SecurityException("Request rejected: Potential prompt injection detected.")

    # 2. Check for regex-based profanity variations
    if re.search(PROFANITY_REGEX, query_lower):
        logger.warning(f"Blocked regex profanity query: {query}")
        raise SecurityException(REFUSAL_MESSAGE)

    # 3. Check for basic toxicity keywords
    for word in TOXIC_KEYWORDS:
        pattern = rf"\b{re.escape(word)}\b"
        if re.search(pattern, query_lower):
            logger.warning(f"Blocked toxic query: {word} in {query}")
            raise SecurityException(REFUSAL_MESSAGE)
            
    logger.info("Query passed safety check.")
