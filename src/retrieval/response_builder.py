"""Response composition utilities for clean, maintainable response building."""

import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from src.retrieval.unified_analyzer import UnifiedAnalysisResult

logger = logging.getLogger(__name__)


# ========================================
# RESPONSE BUILDING CONSTANTS
# ========================================

# Filter description templates
FILTER_DESC_TEMPLATES = {
    "fr": {
        "city": " à **{value}**",
        "month": " en **{value}**",
        "category": " dans la catégorie **{value}**",
    },
    "en": {
        "city": " in **{value}**",
        "month": " in **{value}**",
        "category": " in category **{value}**",
    }
}

MONTH_NAMES = {
    "fr": ["", "janvier", "février", "mars", "avril", "mai", "juin",
           "juillet", "août", "septembre", "octobre", "novembre", "décembre"],
    "en": ["", "January", "February", "March", "April", "May", "June",
           "July", "August", "September", "October", "November", "December"]
}

# Statistical response templates (used when statistical dimension detected)
STATISTICAL_TEMPLATES = {
    "fr": """J'ai trouvé **{count} événement(s)** correspondant à votre recherche{filters_desc}.

{event_breakdown}""",
    "en": """I found **{count} event(s)** matching your search{filters_desc}.

{event_breakdown}"""
}

# Default timeframe configuration
DEFAULT_TIMEFRAME_DAYS = 30  # Default to next 30 days when no timeframe specified

# Default timeframe notice (added when we auto-apply the default)
DEFAULT_TIMEFRAME_NOTICE = {
    "fr": "\n\n📅 *Résultats filtrés sur les **30 prochains jours**.*",
    "en": "\n\n📅 *Results filtered to the **next 30 days**.*"
}

# Refinement suggestions (invite user to refine their search)
REFINEMENT_SUGGESTIONS = {
    "fr": """

---
💡 **Affiner votre recherche ?** Vous pouvez préciser :
- 📆 Une **date** ou **période** (ex: "ce week-end", "en février")
- 🎫 **Événements gratuits** (ex: "gratuit", "entrée libre")
- 👨‍👩‍👧 **Public cible** (ex: "pour enfants", "en famille")
- 🎭 **Type d'événement** (ex: "concerts", "expositions", "théâtre")""",
    "en": """

---
💡 **Want to refine your search?** You can specify:
- 📆 A **date** or **period** (e.g., "this weekend", "in February")
- 🎫 **Free events** (e.g., "free", "no charge")
- 👨‍👩‍👧 **Target audience** (e.g., "for kids", "family-friendly")
- 🎭 **Event type** (e.g., "concerts", "exhibitions", "theater")"""
}

# Shorter refinement hint for when results are found (less intrusive)
REFINEMENT_HINT = {
    "fr": "\n\n💡 *Précisez une date, un type d'événement, ou \"gratuit\" pour affiner.*",
    "en": "\n\n💡 *Specify a date, event type, or \"free\" to refine your search.*"
}

# Broadening suggestion when < 8 results
BROADENING_SUGGESTION = {
    "fr": "\n\n💡 *Peu de résultats ? Essayez d'élargir votre recherche : changez la date, la ville, ou simplifiez vos critères.*",
    "en": "\n\n💡 *Few results? Try broadening your search: change the date, city, or simplify your criteria.*"
}

# Markers used to detect and strip existing suffixes (avoid duplication)
SUFFIX_MARKERS = [
    "📅 *Results filtered",
    "💡 *Specify",
    "💡 **Want to refine",
    "**Applied filters:**",
    "---\n**Applied"
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
    templates = FILTER_DESC_TEMPLATES.get(language, FILTER_DESC_TEMPLATES["en"])
    parts = []

    if filters.get("city"):
        parts.append(templates["city"].format(value=filters["city"]))

    if filters.get("month"):
        month_num = filters["month"]
        month_names = MONTH_NAMES.get(language, MONTH_NAMES["en"])
        if 1 <= month_num <= 12:
            parts.append(templates["month"].format(value=month_names[month_num]))

    if filters.get("category"):
        parts.append(templates["category"].format(value=filters["category"]))

    return "".join(parts)


def build_statistical_response(
    count: int,
    filters: Dict[str, Any],
    category_breakdown: Dict[str, int],
    language: str
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
    template = STATISTICAL_TEMPLATES.get(language, STATISTICAL_TEMPLATES["en"])
    filters_desc = build_filter_description(filters, language)

    # Build category breakdown
    breakdown_lines = []
    for category, cat_count in sorted(category_breakdown.items(), key=lambda x: -x[1]):
        if cat_count > 0:
            breakdown_lines.append(f"- **{category}**: {cat_count}")

    event_breakdown = "\n".join(breakdown_lines) if breakdown_lines else ""

    return template.format(
        count=count,
        filters_desc=filters_desc,
        event_breakdown=event_breakdown
    )


def build_filter_echo(filters: Dict[str, Any], search_terms: List[str], language: str) -> str:
    """Build a summary of applied filters and search terms for transparency.

    Args:
        filters: Applied filters (city, month, day, category, audience, etc.)
        search_terms: Accumulated search query terms
        language: Target language (fr/en)

    Returns:
        Formatted string showing what filters were used
    """
    parts = []

    # Structured filters
    filter_items = []
    if filters.get("city"):
        filter_items.append(f"📍 {filters['city']}")
    if filters.get("month"):
        month_names_en = ["", "January", "February", "March", "April", "May", "June",
                         "July", "August", "September", "October", "November", "December"]
        month_names_fr = ["", "janvier", "février", "mars", "avril", "mai", "juin",
                         "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
        month_num = filters["month"]
        if 1 <= month_num <= 12:
            month_name = month_names_fr[month_num] if language == "fr" else month_names_en[month_num]
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
        filter_items.append("🎫 " + ("gratuit" if language == "fr" else "free"))

    # Search terms (accumulated text queries)
    if search_terms:
        terms_str = " + ".join([f'"{t}"' for t in search_terms])
        filter_items.append(f"🔍 {terms_str}")

    if filter_items:
        header = "**Filtres appliqués:**" if language == "fr" else "**Applied filters:**"
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


def build_refinement_suffix(
    filters: Dict[str, Any],
    has_results: bool,
    language: str
) -> str:
    """Build refinement suggestion suffix based on what filters are already applied.

    Args:
        filters: Applied filters
        has_results: Whether the search returned results
        language: Target language

    Returns:
        Refinement suggestion string
    """
    suffix_parts = []

    # Add default timeframe notice if it was applied
    if filters.get("_default_timeframe_applied"):
        suffix_parts.append(DEFAULT_TIMEFRAME_NOTICE.get(language, DEFAULT_TIMEFRAME_NOTICE["en"]))

    # Add refinement suggestions
    # Use shorter hint if results found, full suggestions if no results
    if has_results:
        suffix_parts.append(REFINEMENT_HINT.get(language, REFINEMENT_HINT["en"]))
    else:
        suffix_parts.append(REFINEMENT_SUGGESTIONS.get(language, REFINEMENT_SUGGESTIONS["en"]))

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
        parts = [
            self.prefix,
            self.main_content,
            self.refinement_suffix,
            self.broadening_suggestion,
            self.filter_echo
        ]
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
        self,
        result_count: int,
        threshold: int = 8,
        suggestion_template: Optional[str] = None
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
            suggestion = suggestion_template or BROADENING_SUGGESTION.get(
                self.language,
                BROADENING_SUGGESTION["en"]
            )
            self.components.broadening_suggestion = suggestion
            logger.info(f"[BROADENING] Added suggestion ({result_count} < {threshold})")
        return self

    def add_filter_echo(
        self,
        filters: Dict[str, Any],
        search_terms: List[str]
    ) -> "ResponseBuilder":
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
    count: int,
    filters: Dict[str, Any],
    category_breakdown: Dict[str, int],
    language: str
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


def build_error_response(
    error_type: str,
    language: str = "fr",
    **context
) -> str:
    """Build user-friendly error response based on error type.

    Args:
        error_type: Type of error (model_loading, rate_limit, timeout, generic)
        language: Target language
        **context: Additional context for error message

    Returns:
        Error message string
    """
    ERROR_TEMPLATES = {
        "model_loading": {
            "fr": (
                "**Modele en cours de chargement**\n\n"
                "Le modele IA demarre (cela peut prendre 20-30 secondes). "
                "Veuillez reessayer dans un moment."
            ),
            "en": (
                "**Model Loading**\n\n"
                "The AI model is starting up (this may take 20-30 seconds). "
                "Please try again in a moment."
            )
        },
        "rate_limit": {
            "fr": (
                "**Limite de requetes atteinte**\n\n"
                "Trop de requetes en meme temps. "
                "Veuillez reessayer dans quelques secondes."
            ),
            "en": (
                "**Rate Limit Reached**\n\n"
                "Too many requests at once. "
                "Please try again in a few seconds."
            )
        },
        "timeout": {
            "fr": (
                "**Delai depasse**\n\n"
                "La requete a pris trop de temps. "
                "Veuillez reessayer ou simplifier votre recherche."
            ),
            "en": (
                "**Request Timeout**\n\n"
                "The request took too long. "
                "Please try again or simplify your search."
            )
        },
        "generic": {
            "fr": (
                "**Erreur de traitement**\n\n"
                "Une erreur s'est produite lors du traitement de votre requete. "
                "Veuillez reessayer ou reformuler votre question."
            ),
            "en": (
                "**Processing Error**\n\n"
                "An error occurred while processing your request. "
                "Please try again or rephrase your question."
            )
        }
    }

    template = ERROR_TEMPLATES.get(error_type, ERROR_TEMPLATES["generic"])
    return template.get(language, template["en"])
