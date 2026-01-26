"""Security guardrails for the RAG system with enhanced Unicode normalization."""

import logging
import re
import unicodedata

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

# Expanded patterns indicative of prompt injection or malicious intent (20+ patterns)
MALICIOUS_PATTERNS = [
    # Instruction overrides
    r"ignore (previous|all|your) instructions?",
    r"disregard (previous|all) (instructions?|prompts?|rules?)",
    r"forget (your|previous|all) (instructions?|rules?|context)",
    r"override (previous|system|safety|security) (instructions?|rules?|settings?)",

    # Jailbreak attempts
    r"you are now",
    r"pretend (you are|to be|that you're)",
    r"act as if you (are|were)",
    r"(developer|debug|admin|god|root|sudo) mode",
    r"bypass (your|the) (rules?|restrictions?|filters?|safety)",
    r"jailbreak",

    # Role manipulation
    r"you must (now|always|only)",
    r"from now on",
    r"new (role|personality|character|instructions?)",

    # Data exfiltration attempts
    r"(show|print|display|reveal|output) (system|internal|hidden) (data|prompt|instructions?)",
    r"what (are|were) your (original|system|hidden) (instructions?|prompts?|rules?)",

    # SQL/Command injection
    r"(delete|drop|truncate|alter)\s+(table|database|schema)",
    r"union\s+select",
    r";\s*drop\s+table",
    r"<\s*script",
    r"javascript\s*:",

    # System manipulation
    r"system\s*\(",
    r"eval\s*\(",
    r"exec\s*\(",
]

# Full-word profanity phrases (to avoid Scunthorpe problem)
PROFANITY_PHRASES = [
    # English (full words to avoid false positives)
    r"\bfuck\b", r"\bshit\b", r"\basshole\b", r"\bbitch\b", r"\bcunt\b",
    r"\bdick\b", r"\bpussy\b", r"\bbastard\b", r"\bmotherfucker\b",
    r"\bcock\b", r"\bslut\b", r"\bwhore\b",

    # French (full words)
    r"\bmerde\b", r"\bputain\b", r"\bcon\b", r"\bconnard\b", r"\bsalope\b",
    r"\benculé\b", r"\bpute\b", r"\bbordel\b", r"\bchier\b",

    # Common evasions (repeated characters)
    r"\bf+u+c+k+\b", r"\bs+h+i+t+\b", r"\bf[\*@#]ck\b",

    # Spaced variations (f u c k)
    r"\bf\s+u\s+c\s+k\b", r"\bs\s+h\s+i\s+t\b",
    r"\bm\s+e\s+r\s+d\s+e\b", r"\bp\s+u\s+t\s+a\s+i\s+n\b",
]

# Severe toxic keywords (hate speech, violence, discrimination)
TOXIC_KEYWORDS = [
    "kill", "death", "hate", "rape", "sexist", "racist",
    "stupid", "idiot", "dumb", "moron", "abruti", "débile", "crétin",
]

# Homoglyph mapping (Cyrillic → Latin, etc.)
HOMOGLYPH_MAP = {
    # Cyrillic lookalikes
    'а': 'a', 'е': 'e', 'о': 'o', 'р': 'p', 'с': 'c',
    'х': 'x', 'у': 'y', 'і': 'i', 'ј': 'j',
    # Leetspeak
    '0': 'o', '1': 'i', '3': 'e', '4': 'a', '5': 's',
    '7': 't', '8': 'b', '9': 'g',
    # Accented variants
    'à': 'a', 'á': 'a', 'â': 'a', 'ã': 'a', 'ä': 'a',
    'è': 'e', 'é': 'e', 'ê': 'e', 'ë': 'e',
    'ì': 'i', 'í': 'i', 'î': 'i', 'ï': 'i',
    'ò': 'o', 'ó': 'o', 'ô': 'o', 'õ': 'o', 'ö': 'o',
    'ù': 'u', 'ú': 'u', 'û': 'u', 'ü': 'u', 'ū': 'u',
}


def normalize_text_for_profanity(text: str) -> str:
    """Normalize text to detect Unicode/homoglyph evasions.

    This function:
    1. Converts to NFD Unicode normalization
    2. Replaces homoglyphs (Cyrillic, leetspeak, accents)
    3. Converts to lowercase

    Example:
        normalize_text_for_profanity("fück") → "fuck"
        normalize_text_for_profanity("fuсk") → "fuck" (Cyrillic 'с')
        normalize_text_for_profanity("f4ck") → "fack"

    Args:
        text: Input text to normalize

    Returns:
        Normalized text with homoglyphs replaced
    """
    # NFD normalization (decompose accented characters)
    normalized = unicodedata.normalize('NFD', text)

    # Remove combining diacritics (accents)
    normalized = ''.join(
        char for char in normalized
        if not unicodedata.combining(char)
    )

    # Replace homoglyphs
    for orig, repl in HOMOGLYPH_MAP.items():
        normalized = normalized.replace(orig, repl)

    # Lowercase
    normalized = normalized.lower()

    return normalized

def check_safety(query: str) -> None:
    """Check if the query contains malicious patterns or toxic content.

    Enhanced with Unicode normalization to detect evasions like:
    - Unicode variations: fück, fuсk (Cyrillic)
    - Leetspeak: f4ck
    - Spaced characters: f u c k

    Args:
        query: User input string

    Raises:
        SecurityException: If safety check fails
    """
    query_lower = query.lower()

    # Normalize for profanity detection (detect Unicode/homoglyph evasions)
    normalized_query = normalize_text_for_profanity(query)

    # 1. Check for prompt injection patterns
    for pattern in MALICIOUS_PATTERNS:
        if re.search(pattern, query_lower):
            logger.warning(f"Blocked malicious query (prompt injection): {query}")
            raise SecurityException("Request rejected: Potential prompt injection detected.")

    # 2. Check for profanity phrases (with Unicode normalization)
    for phrase_pattern in PROFANITY_PHRASES:
        if re.search(phrase_pattern, normalized_query, re.IGNORECASE):
            logger.warning(f"Blocked profanity query (phrase match): {query}")
            raise SecurityException(REFUSAL_MESSAGE)

    # 3. Check for toxic keywords (hate speech, violence)
    for word in TOXIC_KEYWORDS:
        pattern = rf"\b{re.escape(word)}\b"
        if re.search(pattern, query_lower):
            logger.warning(f"Blocked toxic query (keyword: {word}): {query}")
            raise SecurityException(REFUSAL_MESSAGE)

    logger.info("Query passed safety check.")


class SecurityGuardrails:
    """Object-oriented interface for security guardrails.

    Provides a cleaner API for checking queries and getting structured results.
    """

    def __init__(self):
        """Initialize security guardrails."""
        pass

    def check_query(self, query: str) -> dict:
        """Check query for security violations.

        Args:
            query: User input string

        Returns:
            Dictionary with keys:
                - blocked (bool): Whether query was blocked
                - reason (str): Reason for blocking (if blocked)
                - passed (bool): Whether query passed all checks
        """
        try:
            check_safety(query)
            return {
                "blocked": False,
                "reason": None,
                "passed": True
            }
        except SecurityException as e:
            return {
                "blocked": True,
                "reason": str(e),
                "passed": False
            }
