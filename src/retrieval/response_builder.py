"""Response composition utilities for clean, maintainable response building."""

import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from src.utils.i18n import get_translator

logger = logging.getLogger(__name__)


# ========================================
# RESPONSE BUILDING CONSTANTS
# ========================================

# Default timeframe configuration
DEFAULT_TIMEFRAME_DAYS = 30  # Default to next 30 days when no timeframe specified

# Markers used to detect and strip existing suffixes (avoid duplication)
SUFFIX_MARKERS = [
    "📅 *Results filtered",
    "💡 *Specify",
    "💡 **Want to refine",
    "**Applied filters:**",
    "---\n**Applied",
]


# ========================================
# HELPER FUNCTIONS FOR RESPONSE BUILDING
# ========================================


def build_filter_description(filters: Dict[str, Any], language: str) -> str:
    """Build human-readable filter description.

    Args:
        filters: Applied filters dict
        language: Target language

    Returns:
        Filter description string
    """
    t = get_translator(language)
    parts = []

    if filters.get("city"):
        parts.append(t.get("filters.city", value=filters["city"]))

    if filters.get("month"):
        month_num = filters["month"]
        month_names = t.get_list("months")
        if 1 <= month_num <= 12:
            parts.append(t.get("filters.month", value=month_names[month_num]))

    if filters.get("category"):
        parts.append(t.get("filters.category", value=filters["category"]))

    return "".join(parts)


def build_statistical_response(
    count: int, filters: Dict[str, Any], category_breakdown: Dict[str, int], language: str
) -> str:
    """Build statistical response when count/how many dimension detected.

    Args:
        count: Total event count
        filters: Applied filters
        category_breakdown: Event counts by category
        language: Target language

    Returns:
        Complete statistical response
    """
    t = get_translator(language)
    filters_desc = build_filter_description(filters, language)

    # Build category breakdown
    breakdown_lines = []
    for category, cat_count in sorted(category_breakdown.items(), key=lambda x: -x[1]):
        if cat_count > 0:
            breakdown_lines.append(f"- **{category}**: {cat_count}")

    event_breakdown = "\n".join(breakdown_lines) if breakdown_lines else ""

    return t.get("responses.statistical", count=count, filters_desc=filters_desc, event_breakdown=event_breakdown)


def build_filter_echo(filters: Dict[str, Any], search_terms: List[str], language: str) -> str:
    """Build a summary of applied filters and search terms for transparency.

    Args:
        filters: Applied filters (city, month, day, category, audience, etc.)
        search_terms: Accumulated search query terms
        language: Target language (fr/en)

    Returns:
        Formatted string showing what filters were used
    """
    t = get_translator(language)
    parts = []

    # Structured filters
    filter_items = []
    if filters.get("city"):
        filter_items.append(f"📍 {filters['city']}")
    if filters.get("month"):
        month_names = t.get_list("months")
        month_num = filters["month"]
        if 1 <= month_num <= 12:
            month_name = month_names[month_num]
            if filters.get("day"):
                days = filters["day"]
                if isinstance(days, list):
                    filter_items.append(f"📅 {days[0]}-{days[-1]} {month_name}")
                else:
                    filter_items.append(f"📅 {days} {month_name}")
            else:
                filter_items.append(f"📅 {month_name}")
    if filters.get("category"):
        filter_items.append(f"🎭 {filters['category']}")
    if filters.get("audience"):
        filter_items.append(f"👥 {filters['audience']}")
    if filters.get("is_free"):
        filter_items.append(f"🎫 {t.get('filters.free')}")

    # Search terms (accumulated text queries)
    if search_terms:
        terms_str = " + ".join([f'"{t}"' for t in search_terms])
        filter_items.append(f"🔍 {terms_str}")

    if filter_items:
        header = t.get("filters.applied_filters")
        parts.append(f"\n\n---\n{header} {' | '.join(filter_items)}")

    return "".join(parts)


def should_apply_default_timeframe(filters: Dict[str, Any]) -> bool:
    """Check if we should apply the default timeframe.

    Returns True if no timeframe was specified by the user.
    """
    has_month = filters.get("month") is not None
    has_day = filters.get("day") is not None
    has_year = filters.get("year") is not None
    return not (has_month or has_day or has_year)


def apply_default_timeframe(filters: Dict[str, Any]) -> Dict[str, Any]:
    """Apply default timeframe (next 30 days) if none specified.

    Args:
        filters: Current filters dict

    Returns:
        Updated filters with default timeframe applied
    """
    from datetime import date, timedelta

    if should_apply_default_timeframe(filters):
        today = date.today()
        # Set filter to current month (as a simple approach)
        # The retrieval will handle date-based filtering
        filters = filters.copy()
        filters["_default_timeframe_applied"] = True
        filters["_timeframe_start"] = today.isoformat()
        filters["_timeframe_end"] = (today + timedelta(days=DEFAULT_TIMEFRAME_DAYS)).isoformat()
        logger.info(f"[DEFAULT-TIMEFRAME] Applied default: {today} to {today + timedelta(days=DEFAULT_TIMEFRAME_DAYS)}")
    return filters


def build_refinement_suffix(filters: Dict[str, Any], has_results: bool, language: str) -> str:
    """Build refinement suggestion suffix based on what filters are already applied.

    Args:
        filters: Applied filters
        has_results: Whether the search returned results
        language: Target language

    Returns:
        Refinement suggestion string
    """
    t = get_translator(language)
    suffix_parts = []

    # Add default timeframe notice if it was applied
    if filters.get("_default_timeframe_applied"):
        suffix_parts.append(t.get("responses.default_timeframe_notice"))

    # Add refinement suggestions
    # Use shorter hint if results found, full suggestions if no results
    if has_results:
        suffix_parts.append(t.get("responses.refinement_hint"))
    else:
        suffix_parts.append(t.get("responses.refinement_suggestions"))

    return "".join(suffix_parts)


@dataclass
class ResponseComponents:
    """Components of a composed response."""

    prefix: str = ""
    main_content: str = ""
    refinement_suffix: str = ""
    broadening_suggestion: str = ""
    filter_echo: str = ""

    def compose(self) -> str:
        """Compose all components into final response."""
        parts = [self.prefix, self.main_content, self.refinement_suffix, self.broadening_suggestion, self.filter_echo]
        return "".join(p for p in parts if p)


class ResponseBuilder:
    """Builder for composing chatbot responses with prefixes, suffixes, and formatting."""

    def __init__(self, language: str = "fr"):
        """Initialize response builder.

        Args:
            language: Target language (fr/en)
        """
        self.language = language
        self.components = ResponseComponents()

    def set_main_content(self, content: str) -> "ResponseBuilder":
        """Set the main response content (from LLM generation).

        Args:
            content: Main response text

        Returns:
            Self for method chaining
        """
        # Strip any existing suffixes to avoid duplication
        cleaned = self._strip_existing_suffixes(content)
        self.components.main_content = cleaned
        return self

    def add_prefix(self, prefix: str) -> "ResponseBuilder":
        """Add prefix to response (e.g., greeting, typo acknowledgment).

        Args:
            prefix: Prefix text

        Returns:
            Self for method chaining
        """
        self.components.prefix = prefix
        return self

    def add_refinement_suffix(self, suffix: str) -> "ResponseBuilder":
        """Add refinement suggestions suffix.

        Args:
            suffix: Refinement text

        Returns:
            Self for method chaining
        """
        self.components.refinement_suffix = suffix
        return self

    def add_broadening_suggestion(
        self, result_count: int, threshold: int = 8, suggestion_template: Optional[str] = None
    ) -> "ResponseBuilder":
        """Add broadening suggestion if results are below threshold.

        Args:
            result_count: Number of results found
            threshold: Minimum results before suggesting broadening
            suggestion_template: Optional custom template

        Returns:
            Self for method chaining
        """
        if 0 < result_count < threshold:
            t = get_translator(self.language)
            suggestion = suggestion_template or t.get("responses.broadening_suggestion")
            self.components.broadening_suggestion = suggestion
            logger.info(f"[BROADENING] Added suggestion ({result_count} < {threshold})")
        return self

    def add_filter_echo(self, filters: Dict[str, Any], search_terms: List[str]) -> "ResponseBuilder":
        """Add filter echo for transparency.

        Args:
            filters: Applied filters
            search_terms: Search terms used

        Returns:
            Self for method chaining
        """
        echo = build_filter_echo(filters, search_terms, self.language)
        self.components.filter_echo = echo
        return self

    def build(self) -> str:
        """Build final composed response.

        Returns:
            Complete response string
        """
        return self.components.compose()

    def _strip_existing_suffixes(self, text: str) -> str:
        """Strip existing suffix markers to avoid duplication.

        Args:
            text: Text to clean

        Returns:
            Cleaned text
        """
        for marker in SUFFIX_MARKERS:
            if marker in text:
                text = text.split(marker)[0].rstrip()
                logger.debug(f"[STRIP-SUFFIX] Removed existing '{marker}' marker")
                break
        return text


def build_statistical_response_text(
    count: int, filters: Dict[str, Any], category_breakdown: Dict[str, int], language: str
) -> str:
    """Build statistical response text.

    This is a wrapper for the existing build_statistical_response function
    to maintain compatibility while providing a cleaner interface.

    Args:
        count: Total event count
        filters: Applied filters
        category_breakdown: Category distribution
        language: Target language

    Returns:
        Statistical response text
    """
    return build_statistical_response(count, filters, category_breakdown, language)


def build_error_response(error_type: str, language: str = "fr", **context) -> str:
    """Build user-friendly error response based on error type.

    Args:
        error_type: Type of error (model_loading, rate_limit, timeout, generic)
        language: Target language
        **context: Additional context for error message

    Returns:
        Error message string
    """
    t = get_translator(language)
    return t.get(f"errors.{error_type}")
