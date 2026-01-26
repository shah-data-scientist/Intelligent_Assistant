"""Language detection and normalization utilities for bilingual support.

This module provides language detection and text normalization for
French and English queries, enabling bilingual consistency in the RAG system.

Dependencies:
    - langdetect: For language detection (pip install langdetect)
    - nltk: For stopwords and stemming (pip install nltk)
"""

import logging
import unicodedata
from typing import Literal

logger = logging.getLogger(__name__)

# Type alias for supported languages
LanguageCode = Literal["fr", "en"]

# French stopwords (common words to remove)
FRENCH_STOPWORDS = {
    'le', 'la', 'les', 'un', 'une', 'des', 'de', 'du', 'à', 'au', 'aux',
    'et', 'ou', 'mais', 'donc', 'or', 'ni', 'car', 'dans', 'sur', 'sous',
    'avec', 'sans', 'pour', 'par', 'en', 'vers', 'chez', 'entre', 'parmi',
    'ce', 'cet', 'cette', 'ces', 'mon', 'ton', 'son', 'ma', 'ta', 'sa',
    'mes', 'tes', 'ses', 'notre', 'votre', 'leur', 'nos', 'vos', 'leurs',
    'je', 'tu', 'il', 'elle', 'on', 'nous', 'vous', 'ils', 'elles',
    'me', 'te', 'se', 'lui', 'leur', 'y', 'en',
    'que', 'qui', 'quoi', 'dont', 'où', 'quand', 'comment', 'pourquoi',
    'est', 'ai', 'as', 'a', 'avons', 'avez', 'ont', 'être', 'avoir',
    'suis', 'es', 'sommes', 'êtes', 'sont', 'été', 'étant', 'ayant', 'eu',
    'très', 'plus', 'moins', 'assez', 'trop', 'bien', 'mal', 'peu', 'beaucoup',
    'tout', 'tous', 'toute', 'toutes', 'même', 'autre', 'autres', 'certain', 'certains',
    'ne', 'pas', 'point', 'jamais', 'rien', 'personne', 'aucun', 'nul',
}

# English stopwords (common words to remove)
ENGLISH_STOPWORDS = {
    'the', 'a', 'an', 'and', 'or', 'but', 'if', 'then', 'else', 'when',
    'at', 'by', 'for', 'with', 'about', 'against', 'between', 'into', 'through',
    'during', 'before', 'after', 'above', 'below', 'to', 'from', 'up', 'down',
    'in', 'out', 'on', 'off', 'over', 'under', 'again', 'further', 'once',
    'here', 'there', 'all', 'both', 'each', 'few', 'more', 'most', 'other',
    'some', 'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so', 'than',
    'too', 'very', 'can', 'will', 'just', 'should', 'now',
    'i', 'you', 'he', 'she', 'it', 'we', 'they', 'them', 'their', 'what',
    'which', 'who', 'whom', 'this', 'that', 'these', 'those', 'am', 'is', 'are',
    'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'having',
    'do', 'does', 'did', 'doing',
}


def detect_language(text: str, default: LanguageCode = "fr") -> LanguageCode:
    """Detect language of input text (French or English).

    Uses langdetect library if available, otherwise falls back to
    simple heuristic detection.

    Args:
        text: Input text to analyze
        default: Default language if detection fails (default: "fr")

    Returns:
        Language code: "fr" or "en"

    Example:
        >>> detect_language("Concerts de jazz à Paris")
        'fr'
        >>> detect_language("Jazz concerts in Paris")
        'en'
    """
    if not text or not text.strip():
        return default

    try:
        # Try langdetect if available
        from langdetect import detect, LangDetectException

        detected = detect(text)
        if detected in ['fr', 'en']:
            logger.debug(f"Detected language: {detected} for text: {text[:50]}...")
            return detected
        else:
            logger.debug(f"Unsupported language detected: {detected}, using default: {default}")
            return default

    except (ImportError, Exception) as e:
        # Fallback to simple heuristic if langdetect not available
        logger.debug(f"langdetect not available or failed: {e}, using heuristic")
        return _heuristic_language_detection(text, default)


def _heuristic_language_detection(text: str, default: LanguageCode = "fr") -> LanguageCode:
    """Simple heuristic language detection based on character frequency.

    Args:
        text: Input text to analyze
        default: Default language if uncertain

    Returns:
        Language code: "fr" or "en"
    """
    text_lower = text.lower()

    # French indicators (accented characters, common words)
    french_indicators = {
        'à', 'â', 'ç', 'é', 'è', 'ê', 'ë', 'î', 'ï', 'ô', 'ù', 'û', 'ü', 'ÿ'
    }
    french_words = {'le', 'la', 'les', 'de', 'du', 'des', 'à', 'et', 'pour', 'dans', 'avec'}

    # English indicators (common words unique to English)
    english_words = {'the', 'is', 'are', 'this', 'that', 'with', 'from'}

    # Count indicators
    french_score = sum(1 for char in text_lower if char in french_indicators)
    french_score += sum(3 for word in french_words if f' {word} ' in f' {text_lower} ')

    english_score = sum(3 for word in english_words if f' {word} ' in f' {text_lower} ')

    # Decide based on scores
    if french_score > english_score:
        return "fr"
    elif english_score > french_score:
        return "en"
    else:
        return default


def normalize_for_search(text: str, language: LanguageCode) -> str:
    """Normalize text for search (remove accents, lowercase).

    This normalization:
    1. Removes accents (café → cafe)
    2. Converts to lowercase
    3. Preserves spaces and alphanumerics

    Args:
        text: Input text to normalize
        language: Language code (used for language-specific rules)

    Returns:
        Normalized text

    Example:
        >>> normalize_for_search("Événements culturels à Paris", "fr")
        'evenements culturels a paris'
        >>> normalize_for_search("Jazz Concert in Paris", "en")
        'jazz concert in paris'
    """
    # NFD normalization (decompose accented characters)
    normalized = unicodedata.normalize('NFD', text)

    # Remove combining diacritics (accents)
    normalized = ''.join(
        char for char in normalized
        if not unicodedata.combining(char)
    )

    # Lowercase
    normalized = normalized.lower()

    return normalized


def remove_stopwords(tokens: list[str], language: LanguageCode) -> list[str]:
    """Remove language-specific stopwords from token list.

    Args:
        tokens: List of word tokens
        language: Language code ("fr" or "en")

    Returns:
        Filtered list of tokens with stopwords removed

    Example:
        >>> remove_stopwords(["les", "concerts", "de", "jazz"], "fr")
        ['concerts', 'jazz']
        >>> remove_stopwords(["the", "jazz", "concerts"], "en")
        ['jazz', 'concerts']
    """
    stopwords = FRENCH_STOPWORDS if language == "fr" else ENGLISH_STOPWORDS
    return [token for token in tokens if token.lower() not in stopwords]


def stem_tokens(tokens: list[str], language: LanguageCode) -> list[str]:
    """Apply language-specific stemming to tokens.

    Reduces words to their root form (concerts → concert).

    Args:
        tokens: List of word tokens
        language: Language code ("fr" or "en")

    Returns:
        List of stemmed tokens

    Example:
        >>> stem_tokens(["concerts", "musicaux"], "fr")
        ['concert', 'music']
        >>> stem_tokens(["concerts", "musical"], "en")
        ['concert', 'music']

    Note:
        Requires nltk library. If not available, returns tokens unchanged.
    """
    try:
        from nltk.stem import SnowballStemmer

        stemmer_lang = 'french' if language == 'fr' else 'english'
        stemmer = SnowballStemmer(stemmer_lang)

        stemmed = [stemmer.stem(token) for token in tokens]
        logger.debug(f"Stemmed {len(tokens)} tokens ({language})")
        return stemmed

    except ImportError:
        logger.warning("NLTK not available, skipping stemming")
        return tokens
    except Exception as e:
        logger.warning(f"Stemming failed: {e}, returning original tokens")
        return tokens


def tokenize_for_bm25(text: str, language: LanguageCode) -> list[str]:
    """Tokenize and process text for BM25 search.

    Pipeline:
    1. Normalize (remove accents, lowercase)
    2. Split into tokens
    3. Remove stopwords
    4. Stem tokens

    Args:
        text: Input text to tokenize
        language: Language code ("fr" or "en")

    Returns:
        List of processed tokens ready for BM25 indexing

    Example:
        >>> tokenize_for_bm25("Les concerts de jazz à Paris", "fr")
        ['concert', 'jazz', 'paris']
        >>> tokenize_for_bm25("The jazz concerts in Paris", "en")
        ['jazz', 'concert', 'paris']
    """
    # Step 1: Normalize
    normalized = normalize_for_search(text, language)

    # Step 2: Tokenize (simple whitespace split)
    tokens = normalized.split()

    # Step 3: Remove stopwords
    tokens = remove_stopwords(tokens, language)

    # Step 4: Stem
    tokens = stem_tokens(tokens, language)

    return tokens


def get_language_aware_config(language: LanguageCode) -> dict:
    """Get language-specific configuration for RAG system.

    Args:
        language: Language code ("fr" or "en")

    Returns:
        Dictionary with language-specific settings:
            - stopwords (set): Stopword set
            - stemmer_name (str): NLTK stemmer name
            - default_prompt_lang (str): Default system prompt language

    Example:
        >>> config = get_language_aware_config("fr")
        >>> print(len(config["stopwords"]))
        85
    """
    if language == "fr":
        return {
            "stopwords": FRENCH_STOPWORDS,
            "stemmer_name": "french",
            "default_prompt_lang": "fr",
        }
    else:  # "en"
        return {
            "stopwords": ENGLISH_STOPWORDS,
            "stemmer_name": "english",
            "default_prompt_lang": "en",
        }
