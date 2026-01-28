"""Keyword detection utilities for dates, event types, and special queries.

This module provides database-backed keyword lookup with fuzzy matching for:
1. Date keywords (months, days, relative dates) - detects timeframes in queries
2. Event descriptors (genres, styles, activities) - detects event types and maps to categories
3. Greeting keywords (bonjour, hello, salut) - detects greetings
4. Capability keywords (help, aide, what can you do) - detects capability questions
5. Off-topic keywords (weather, recipe, translate) - detects off-topic queries
6. Statistical keywords (how many, combien, count) - detects statistical queries

Similar to CityLocator in geo.py, but for dates, events, and special queries.
"""

import json
import logging
import re
import sqlite3
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


@dataclass
class KeywordMatch:
    """Result of a keyword match."""
    original: str           # The word from the query
    matched: str            # The matched keyword
    canonical: str          # Canonical form
    keyword_type: str       # "date", "event", "greeting", "capability", "off_topic", "statistical"
    implied_category: Optional[str]  # For events: "Musique", "Art", etc. For off_topic: subcategory
    match_type: str         # "exact", "typo", "fuzzy", "pattern"
    confidence: float       # 0.0 to 1.0


class KeywordLocator:
    """Database-backed keyword locator with fuzzy matching.

    Loads keywords from the search_keywords table and provides:
    - Exact matching
    - Typo detection (from pre-defined typo lists)
    - Fuzzy matching (Levenshtein distance)
    - Specific date format detection (regex patterns)
    """

    def __init__(self, db_path: str = "data/events.db"):
        self.db_path = db_path

        # Caches for core search keywords
        self.date_keywords: Dict[str, dict] = {}      # keyword -> {canonical, typos, language}
        self.event_keywords: Dict[str, dict] = {}     # keyword -> {canonical, category, typos, language}

        # Caches for special query keywords
        self.greeting_keywords: Dict[str, dict] = {}      # keyword -> {canonical, typos, language}
        self.capability_keywords: Dict[str, dict] = {}    # keyword -> {canonical, typos, language}
        self.off_topic_keywords: Dict[str, dict] = {}     # keyword -> {canonical (subcategory), typos, language}
        self.statistical_keywords: Dict[str, dict] = {}   # keyword -> {canonical, typos, language}

        # Global typo mapping (all keyword types)
        self.typo_to_keyword: Dict[str, Tuple[str, str]] = {}  # typo -> (correct_keyword, keyword_type)

        # Pre-compiled regex patterns for specific date formats
        self.date_patterns = self._compile_date_patterns()

        # Load from database
        self._load_keywords()

    def _compile_date_patterns(self) -> List[Tuple[re.Pattern, str]]:
        """Compile regex patterns for specific date formats.

        Returns list of (pattern, description) tuples.
        """
        patterns = [
            # DD/MM/YYYY or DD-MM-YYYY
            (re.compile(r'\b(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})\b'), "date_dmy"),

            # YYYY-MM-DD (ISO format)
            (re.compile(r'\b(\d{4})[/\-](\d{1,2})[/\-](\d{1,2})\b'), "date_iso"),

            # DD month or DD month YYYY (e.g., "15 janvier", "15 January 2026")
            (re.compile(
                r'\b(\d{1,2})(?:st|nd|rd|th)?\s+'
                r'(january|february|march|april|may|june|july|august|september|october|november|december|'
                r'janvier|février|fevrier|mars|avril|mai|juin|juillet|août|aout|septembre|octobre|novembre|décembre|decembre)'
                r'(?:\s+(\d{4}))?\b',
                re.IGNORECASE
            ), "date_day_month"),

            # month DD or month DD, YYYY (e.g., "January 15", "January 15, 2026")
            (re.compile(
                r'\b(january|february|march|april|may|june|july|august|september|october|november|december|'
                r'janvier|février|fevrier|mars|avril|mai|juin|juillet|août|aout|septembre|octobre|novembre|décembre|decembre)'
                r'\s+(\d{1,2})(?:st|nd|rd|th)?(?:,?\s+(\d{4}))?\b',
                re.IGNORECASE
            ), "date_month_day"),

            # "le DD" (French: "le 15")
            (re.compile(r'\ble\s+(\d{1,2})\b', re.IGNORECASE), "date_le_dd"),

            # "on the DDth" or "the DDth"
            (re.compile(r'\b(?:on\s+)?the\s+(\d{1,2})(?:st|nd|rd|th)\b', re.IGNORECASE), "date_the_dd"),

            # Year only (2025, 2026, 2027, etc.) - common for "events in 2026"
            (re.compile(r'\b(202[4-9]|203[0-9])\b'), "date_year"),

            # "next year" / "this year" - English
            (re.compile(r'\b(next\s+year|this\s+year|coming\s+year)\b', re.IGNORECASE), "date_relative_year_en"),

            # "l'année prochaine" / "cette année" - French (with/without accents)
            (re.compile(
                r"\b(l'ann[ée]e\s+prochaine|l'annee\s+prochaine|cette\s+ann[ée]e|cette\s+annee|"
                r"ann[ée]e\s+prochaine|annee\s+prochaine)\b",
                re.IGNORECASE
            ), "date_relative_year_fr"),
        ]
        return patterns

    def _load_keywords(self):
        """Load keywords from database into memory cache."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Check if table exists
            cursor.execute("""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name='search_keywords'
            """)
            if not cursor.fetchone():
                logger.warning("search_keywords table not found. Run migrate_search_keywords.py first.")
                conn.close()
                return

            # Load all keywords
            cursor.execute("""
                SELECT keyword, keyword_type, language, canonical, implied_category, typos
                FROM search_keywords
            """)

            counts = {
                "date": 0,
                "event": 0,
                "greeting": 0,
                "capability": 0,
                "off_topic": 0,
                "statistical": 0,
            }

            for row in cursor.fetchall():
                keyword, ktype, language, canonical, category, typos_json = row
                typos = json.loads(typos_json) if typos_json else []

                entry = {
                    "canonical": canonical,
                    "language": language,
                    "typos": typos,
                }

                keyword_lower = keyword.lower()

                if ktype == "date":
                    self.date_keywords[keyword_lower] = entry
                    counts["date"] += 1
                elif ktype == "event":
                    entry["category"] = category
                    self.event_keywords[keyword_lower] = entry
                    counts["event"] += 1
                elif ktype == "greeting":
                    self.greeting_keywords[keyword_lower] = entry
                    counts["greeting"] += 1
                elif ktype == "capability":
                    self.capability_keywords[keyword_lower] = entry
                    counts["capability"] += 1
                elif ktype == "off_topic":
                    # For off_topic, canonical contains the subcategory (e.g., "off_topic_weather")
                    entry["subcategory"] = canonical
                    self.off_topic_keywords[keyword_lower] = entry
                    counts["off_topic"] += 1
                elif ktype == "statistical":
                    self.statistical_keywords[keyword_lower] = entry
                    counts["statistical"] += 1

                # Build typo -> (keyword, type) mapping
                for typo in typos:
                    self.typo_to_keyword[typo.lower()] = (keyword_lower, ktype)

            conn.close()
            logger.info(
                f"Loaded keywords from database: "
                f"date={counts['date']}, event={counts['event']}, "
                f"greeting={counts['greeting']}, capability={counts['capability']}, "
                f"off_topic={counts['off_topic']}, statistical={counts['statistical']}"
            )

        except Exception as e:
            logger.error(f"Failed to load keywords from database: {e}")

    def detect_date(self, query: str, threshold: float = 0.80) -> Optional[KeywordMatch]:
        """Detect date/timeframe in query.

        Checks in order:
        1. Specific date format patterns (DD/MM/YYYY, etc.)
        2. Exact keyword match
        3. Known typo match
        4. Fuzzy match

        Args:
            query: The user query
            threshold: Minimum similarity for fuzzy matching

        Returns:
            KeywordMatch if date detected, None otherwise
        """
        query_lower = query.lower()
        words = query_lower.split()

        # 1. Check specific date format patterns
        for pattern, pattern_type in self.date_patterns:
            match = pattern.search(query_lower)
            if match:
                return KeywordMatch(
                    original=match.group(0),
                    matched=match.group(0),
                    canonical=pattern_type,
                    keyword_type="date",
                    implied_category=None,
                    match_type="pattern",
                    confidence=1.0
                )

        # 2. Check for exact keyword matches (including multi-word)
        # First check multi-word phrases
        for keyword, data in self.date_keywords.items():
            if ' ' in keyword:  # Multi-word keyword
                if keyword in query_lower:
                    return KeywordMatch(
                        original=keyword,
                        matched=keyword,
                        canonical=data["canonical"],
                        keyword_type="date",
                        implied_category=None,
                        match_type="exact",
                        confidence=1.0
                    )

        # Then check single words
        for word in words:
            # Exact match
            if word in self.date_keywords:
                data = self.date_keywords[word]
                return KeywordMatch(
                    original=word,
                    matched=word,
                    canonical=data["canonical"],
                    keyword_type="date",
                    implied_category=None,
                    match_type="exact",
                    confidence=1.0
                )

            # 3. Known typo match
            if word in self.typo_to_keyword:
                correct, ktype = self.typo_to_keyword[word]
                if ktype == "date" and correct in self.date_keywords:
                    data = self.date_keywords[correct]
                    return KeywordMatch(
                        original=word,
                        matched=correct,
                        canonical=data["canonical"],
                        keyword_type="date",
                        implied_category=None,
                        match_type="typo",
                        confidence=0.95
                    )

        # 4. Fuzzy matching for words not found
        for word in words:
            if len(word) < 3:
                continue

            best_match = None
            best_ratio = 0.0

            for keyword in self.date_keywords.keys():
                # Skip multi-word keywords for fuzzy matching
                if ' ' in keyword:
                    continue

                ratio = SequenceMatcher(None, word, keyword).ratio()
                if ratio > best_ratio and ratio >= threshold:
                    best_ratio = ratio
                    best_match = keyword

            if best_match:
                data = self.date_keywords[best_match]
                logger.info(f"[KEYWORD-FUZZY] Date typo: '{word}' -> '{best_match}' ({best_ratio:.2f})")
                return KeywordMatch(
                    original=word,
                    matched=best_match,
                    canonical=data["canonical"],
                    keyword_type="date",
                    implied_category=None,
                    match_type="fuzzy",
                    confidence=best_ratio
                )

        return None

    def detect_event_type(self, query: str, threshold: float = 0.80) -> Optional[KeywordMatch]:
        """Detect event type/genre in query.

        Checks in order:
        1. Exact keyword match
        2. Known typo match
        3. Fuzzy match

        Args:
            query: The user query
            threshold: Minimum similarity for fuzzy matching

        Returns:
            KeywordMatch if event type detected, None otherwise
        """
        query_lower = query.lower()
        words = query_lower.split()

        # 1. Check for exact matches (multi-word first)
        for keyword, data in self.event_keywords.items():
            if ' ' in keyword:  # Multi-word keyword
                if keyword in query_lower:
                    return KeywordMatch(
                        original=keyword,
                        matched=keyword,
                        canonical=data["canonical"],
                        keyword_type="event",
                        implied_category=data.get("category"),
                        match_type="exact",
                        confidence=1.0
                    )

        # Then single words
        for word in words:
            # Exact match
            if word in self.event_keywords:
                data = self.event_keywords[word]
                return KeywordMatch(
                    original=word,
                    matched=word,
                    canonical=data["canonical"],
                    keyword_type="event",
                    implied_category=data.get("category"),
                    match_type="exact",
                    confidence=1.0
                )

            # 2. Known typo match
            if word in self.typo_to_keyword:
                correct, ktype = self.typo_to_keyword[word]
                if ktype == "event" and correct in self.event_keywords:
                    data = self.event_keywords[correct]
                    return KeywordMatch(
                        original=word,
                        matched=correct,
                        canonical=data["canonical"],
                        keyword_type="event",
                        implied_category=data.get("category"),
                        match_type="typo",
                        confidence=0.95
                    )

        # 3. Fuzzy matching
        for word in words:
            if len(word) < 3:
                continue

            best_match = None
            best_ratio = 0.0
            best_data = None

            for keyword, data in self.event_keywords.items():
                # Skip multi-word for fuzzy
                if ' ' in keyword:
                    continue

                ratio = SequenceMatcher(None, word, keyword).ratio()
                if ratio > best_ratio and ratio >= threshold:
                    best_ratio = ratio
                    best_match = keyword
                    best_data = data

            if best_match and best_data:
                logger.info(f"[KEYWORD-FUZZY] Event typo: '{word}' -> '{best_match}' ({best_ratio:.2f})")
                return KeywordMatch(
                    original=word,
                    matched=best_match,
                    canonical=best_data["canonical"],
                    keyword_type="event",
                    implied_category=best_data.get("category"),
                    match_type="fuzzy",
                    confidence=best_ratio
                )

        return None

    def _detect_generic(
        self,
        query: str,
        keywords_dict: Dict[str, dict],
        keyword_type: str,
        threshold: float = 0.80
    ) -> Optional[KeywordMatch]:
        """Generic detection method for any keyword type.

        Args:
            query: The user query
            keywords_dict: The keyword dictionary to search in
            keyword_type: The type of keyword (greeting, capability, etc.)
            threshold: Minimum similarity for fuzzy matching

        Returns:
            KeywordMatch if detected, None otherwise
        """
        query_lower = query.lower()
        words = query_lower.split()

        # 1. Check for exact matches (multi-word first)
        for keyword, data in keywords_dict.items():
            if ' ' in keyword:  # Multi-word keyword
                if keyword in query_lower:
                    return KeywordMatch(
                        original=keyword,
                        matched=keyword,
                        canonical=data["canonical"],
                        keyword_type=keyword_type,
                        implied_category=data.get("subcategory"),
                        match_type="exact",
                        confidence=1.0
                    )

        # Then single words
        for word in words:
            # Exact match
            if word in keywords_dict:
                data = keywords_dict[word]
                return KeywordMatch(
                    original=word,
                    matched=word,
                    canonical=data["canonical"],
                    keyword_type=keyword_type,
                    implied_category=data.get("subcategory"),
                    match_type="exact",
                    confidence=1.0
                )

            # 2. Known typo match
            if word in self.typo_to_keyword:
                correct, ktype = self.typo_to_keyword[word]
                if ktype == keyword_type and correct in keywords_dict:
                    data = keywords_dict[correct]
                    logger.info(f"[KEYWORD-TYPO] {keyword_type}: '{word}' -> '{correct}'")
                    return KeywordMatch(
                        original=word,
                        matched=correct,
                        canonical=data["canonical"],
                        keyword_type=keyword_type,
                        implied_category=data.get("subcategory"),
                        match_type="typo",
                        confidence=0.95
                    )

        # 3. Fuzzy matching
        for word in words:
            if len(word) < 3:
                continue

            best_match = None
            best_ratio = 0.0
            best_data = None

            for keyword, data in keywords_dict.items():
                # Skip multi-word for fuzzy
                if ' ' in keyword:
                    continue

                ratio = SequenceMatcher(None, word, keyword).ratio()
                if ratio > best_ratio and ratio >= threshold:
                    best_ratio = ratio
                    best_match = keyword
                    best_data = data

            if best_match and best_data:
                logger.info(f"[KEYWORD-FUZZY] {keyword_type}: '{word}' -> '{best_match}' ({best_ratio:.2f})")
                return KeywordMatch(
                    original=word,
                    matched=best_match,
                    canonical=best_data["canonical"],
                    keyword_type=keyword_type,
                    implied_category=best_data.get("subcategory"),
                    match_type="fuzzy",
                    confidence=best_ratio
                )

        return None

    def detect_greeting(self, query: str, threshold: float = 0.80) -> Optional[KeywordMatch]:
        """Detect greeting in query (bonjour, hello, salut, etc.).

        Args:
            query: The user query
            threshold: Minimum similarity for fuzzy matching

        Returns:
            KeywordMatch if greeting detected, None otherwise
        """
        return self._detect_generic(query, self.greeting_keywords, "greeting", threshold)

    def detect_capability(self, query: str, threshold: float = 0.80) -> Optional[KeywordMatch]:
        """Detect capability/help question in query.

        Args:
            query: The user query
            threshold: Minimum similarity for fuzzy matching

        Returns:
            KeywordMatch if capability question detected, None otherwise
        """
        return self._detect_generic(query, self.capability_keywords, "capability", threshold)

    def detect_off_topic(self, query: str, threshold: float = 0.80) -> Optional[KeywordMatch]:
        """Detect off-topic query (weather, recipe, translate, etc.).

        Args:
            query: The user query
            threshold: Minimum similarity for fuzzy matching

        Returns:
            KeywordMatch if off-topic detected, None otherwise
        """
        return self._detect_generic(query, self.off_topic_keywords, "off_topic", threshold)

    def detect_statistical(self, query: str, threshold: float = 0.80) -> Optional[KeywordMatch]:
        """Detect statistical query (how many, combien, count, etc.).

        Args:
            query: The user query
            threshold: Minimum similarity for fuzzy matching

        Returns:
            KeywordMatch if statistical query detected, None otherwise
        """
        return self._detect_generic(query, self.statistical_keywords, "statistical", threshold)

    def detect_all(self, query: str, threshold: float = 0.80) -> Dict[str, Optional[KeywordMatch]]:
        """Detect all keyword types in query.

        Args:
            query: The user query
            threshold: Minimum similarity for fuzzy matching

        Returns:
            Dict with all keyword type keys, values are KeywordMatch or None
        """
        return {
            "date": self.detect_date(query, threshold),
            "event_type": self.detect_event_type(query, threshold),
            "greeting": self.detect_greeting(query, threshold),
            "capability": self.detect_capability(query, threshold),
            "off_topic": self.detect_off_topic(query, threshold),
            "statistical": self.detect_statistical(query, threshold),
        }

    def detect_special_query(self, query: str, threshold: float = 0.80) -> Optional[KeywordMatch]:
        """Detect if query is a special query (greeting, capability, off_topic, statistical).

        Checks in priority order:
        1. Greeting (bonjour, hello)
        2. Capability question (help, what can you do)
        3. Statistical query (how many events)
        4. Off-topic query (weather, recipe, translate)

        Args:
            query: The user query
            threshold: Minimum similarity for fuzzy matching

        Returns:
            KeywordMatch if special query detected, None otherwise
        """
        # Check in priority order
        greeting = self.detect_greeting(query, threshold)
        if greeting:
            return greeting

        capability = self.detect_capability(query, threshold)
        if capability:
            return capability

        statistical = self.detect_statistical(query, threshold)
        if statistical:
            return statistical

        off_topic = self.detect_off_topic(query, threshold)
        if off_topic:
            return off_topic

        return None

    # ========================================
    # INDICATOR HELPER METHODS
    # ========================================

    def has_date_indicator(self, query: str) -> bool:
        """Quick check if query has ANY date indicator."""
        return self.detect_date(query) is not None

    def has_event_indicator(self, query: str) -> bool:
        """Quick check if query has ANY event type indicator."""
        return self.detect_event_type(query) is not None

    def has_greeting_indicator(self, query: str) -> bool:
        """Quick check if query is a greeting."""
        return self.detect_greeting(query) is not None

    def has_capability_indicator(self, query: str) -> bool:
        """Quick check if query is asking about capabilities."""
        return self.detect_capability(query) is not None

    def has_off_topic_indicator(self, query: str) -> bool:
        """Quick check if query is off-topic."""
        return self.detect_off_topic(query) is not None

    def has_statistical_indicator(self, query: str) -> bool:
        """Quick check if query is a statistical question."""
        return self.detect_statistical(query) is not None

    def get_all_event_keywords(self) -> Set[str]:
        """Return all known event keywords."""
        return set(self.event_keywords.keys())

    def get_all_date_keywords(self) -> Set[str]:
        """Return all known date keywords."""
        return set(self.date_keywords.keys())

    def get_category_for_keyword(self, keyword: str) -> Optional[str]:
        """Get the implied category for an event keyword."""
        keyword_lower = keyword.lower()
        if keyword_lower in self.event_keywords:
            return self.event_keywords[keyword_lower].get("category")
        return None


# Global instance (singleton pattern)
_keyword_locator = None


def get_keyword_locator() -> KeywordLocator:
    """Get or create the global KeywordLocator instance."""
    global _keyword_locator
    if _keyword_locator is None:
        _keyword_locator = KeywordLocator()
    return _keyword_locator
