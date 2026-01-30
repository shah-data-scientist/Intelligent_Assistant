"""Response composition utilities for clean, maintainable response building."""

import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from src.retrieval.unified_analyzer import UnifiedAnalysisResult

logger = logging.getLogger(__name__)


# Markers used to detect and strip existing suffixes (avoid duplication)
SUFFIX_MARKERS = [
    "📅 *Results filtered",
    "💡 *Specify",
    "💡 **Want to refine",
    "**Applied filters:**",
    "---\n**Applied"
]


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
            from src.retrieval.chain import BROADENING_SUGGESTION
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
        from src.retrieval.chain import build_filter_echo
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
    from src.retrieval.chain import build_statistical_response
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
