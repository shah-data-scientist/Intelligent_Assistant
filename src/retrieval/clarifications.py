"""Centralized clarification question templates.

This module provides a SINGLE SOURCE OF TRUTH for clarification questions
used when queries are too broad.

STRICT 3-CRITERIA SYSTEM:
Every search requires: City + Event Type + Date/Timeframe
If any criterion is missing, we ask for clarification.
"""

from typing import List, Optional, Tuple
from src.utils.i18n import get_translator


def get_clarification_response(reason: str, language: str = "en") -> Tuple[Optional[str], Optional[List[str]]]:
    """Get clarification prefix and questions for a given reason.

    Args:
        reason: The reason string from UnifiedAnalyzer (e.g., "missing_city+event_type")
        language: Language code ("fr" or "en")

    Returns:
        Tuple of (prefix, questions_list) or (None, None) if reason unknown
    """
    t = get_translator(language)

    # Get clarification data from i18n
    clarification_data = t.get_dict(f"clarifications.{reason}")

    if not clarification_data:
        return None, None

    return clarification_data.get("prefix"), clarification_data.get("questions")
