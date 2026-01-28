"""Shared constants for filter logic.

This module provides constants used across the retrieval system.
The actual filter parsing and application happens in:
- RetrievalManager.parse_intent() → creates SearchIntent
- EventVectorStore._matches_filter() → applies filters to events
"""

# ========================================
# SHARED CONSTANTS - Single Source of Truth
# ========================================
# Used by vector_store.py to identify regional terms (not specific cities)

IDF_REGIONAL_TERMS = frozenset([
    "ile de france",
    "ile-de-france",
    "île-de-france",
    "idf",
    "paris region",
])
