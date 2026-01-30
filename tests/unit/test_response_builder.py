"""
FILE: test_response_builder.py
STATUS: Active
RESPONSIBILITY: Unit tests for response building and JSON formatting.

DEPENDENCIES (Who uses this file):
- pytest test runner
- Response format validation

IMPORTS (What this file needs):
- pytest: Test framework
- src.generation.response_builder: Response building functions

LAST MAJOR UPDATE: 2026-01-31
MAINTAINER: QA Team
"""

import pytest
from src.retrieval.response_builder import (
    ResponseBuilder,
    build_filter_description,
    build_statistical_response,
    build_filter_echo,
    build_refinement_suffix,
    should_apply_default_timeframe,
    apply_default_timeframe,
    BROADENING_SUGGESTION,
    REFINEMENT_HINT,
    SUFFIX_MARKERS,
)


class TestResponseBuilder:
    """Test the ResponseBuilder class for clean response composition."""

    def test_builder_basic_composition(self):
        """Test basic builder pattern composition."""
        builder = ResponseBuilder(language="fr")
        result = builder.set_main_content("Voici 5 événements").build()

        assert result == "Voici 5 événements"

    def test_builder_with_prefix(self):
        """Test adding prefix to response."""
        builder = ResponseBuilder(language="fr")
        result = builder.add_prefix("Bonjour ! ").set_main_content("Voici 5 événements").build()

        assert result == "Bonjour ! Voici 5 événements"

    def test_builder_with_all_components(self):
        """Test builder with all components (prefix, main, suffix, broadening, filter echo)."""
        builder = ResponseBuilder(language="fr")
        filters = {"city": "Paris"}
        search_terms = ["jazz"]

        result = (
            builder.add_prefix("Bonjour ! ")
            .set_main_content("Voici 5 événements")
            .add_refinement_suffix("\n\nAffinez votre recherche")
            .add_broadening_suggestion(result_count=3, threshold=8)
            .add_filter_echo(filters, search_terms)
            .build()
        )

        assert "Bonjour ! " in result
        assert "Voici 5 événements" in result
        assert "Affinez votre recherche" in result
        assert BROADENING_SUGGESTION["fr"] in result
        assert "Paris" in result

    def test_builder_strips_existing_suffixes(self):
        """Test that existing suffix markers are stripped to avoid duplication."""
        builder = ResponseBuilder(language="fr")

        # LLM response might include these markers
        content_with_marker = "Voici 5 événements\n\n💡 *Specify a date*"
        result = builder.set_main_content(content_with_marker).build()

        # Should strip the marker
        assert result == "Voici 5 événements"
        assert "💡" not in result

    def test_builder_broadening_only_below_threshold(self):
        """Test broadening suggestion only added when results < threshold."""
        builder = ResponseBuilder(language="fr")

        # Below threshold
        builder.add_broadening_suggestion(result_count=5, threshold=8)
        assert builder.components.broadening_suggestion == BROADENING_SUGGESTION["fr"]

        # Above threshold - reset builder
        builder = ResponseBuilder(language="fr")
        builder.add_broadening_suggestion(result_count=10, threshold=8)
        assert builder.components.broadening_suggestion == ""

    def test_builder_no_broadening_for_zero_results(self):
        """Test no broadening suggestion for 0 results."""
        builder = ResponseBuilder(language="fr")
        builder.add_broadening_suggestion(result_count=0, threshold=8)
        assert builder.components.broadening_suggestion == ""

    def test_builder_method_chaining(self):
        """Test method chaining returns self."""
        builder = ResponseBuilder(language="fr")

        result = builder.set_main_content("test")
        assert result is builder

        result = builder.add_prefix("prefix")
        assert result is builder


class TestBuildFilterDescription:
    """Test build_filter_description helper function."""

    def test_filter_description_city_only(self):
        """Test filter description with city only."""
        filters = {"city": "Paris"}
        result = build_filter_description(filters, "fr")

        assert "Paris" in result
        assert "à" in result

    def test_filter_description_month_only(self):
        """Test filter description with month only."""
        filters = {"month": 2}
        result = build_filter_description(filters, "fr")

        assert "février" in result
        assert "en" in result

    def test_filter_description_category_only(self):
        """Test filter description with category only."""
        filters = {"category": "Musique"}
        result = build_filter_description(filters, "fr")

        assert "Musique" in result
        assert "catégorie" in result

    def test_filter_description_combined(self):
        """Test filter description with multiple filters."""
        filters = {"city": "Paris", "month": 2, "category": "Musique"}
        result = build_filter_description(filters, "fr")

        assert "Paris" in result
        assert "février" in result
        assert "Musique" in result

    def test_filter_description_english(self):
        """Test filter description in English."""
        filters = {"city": "Paris", "month": 2}
        result = build_filter_description(filters, "en")

        assert "Paris" in result
        assert "February" in result
        assert "in" in result  # "in Paris", "in February"


class TestBuildStatisticalResponse:
    """Test build_statistical_response function."""

    def test_statistical_response_basic(self):
        """Test basic statistical response."""
        category_breakdown = {"Musique": 5, "Théâtre": 3}
        filters = {"city": "Paris"}

        result = build_statistical_response(
            count=8, filters=filters, category_breakdown=category_breakdown, language="fr"
        )

        assert "8 événement(s)" in result
        assert "Paris" in result
        assert "Musique" in result
        assert "Théâtre" in result

    def test_statistical_response_sorted_by_count(self):
        """Test category breakdown sorted by count descending."""
        category_breakdown = {"Théâtre": 3, "Musique": 10, "Art": 1}

        result = build_statistical_response(count=14, filters={}, category_breakdown=category_breakdown, language="fr")

        # Check Musique appears before Théâtre (sorted by count)
        musique_idx = result.index("Musique")
        theatre_idx = result.index("Théâtre")
        assert musique_idx < theatre_idx

    def test_statistical_response_english(self):
        """Test statistical response in English."""
        category_breakdown = {"Music": 5}
        filters = {"city": "Paris"}

        result = build_statistical_response(
            count=5, filters=filters, category_breakdown=category_breakdown, language="en"
        )

        assert "I found" in result
        assert "event(s)" in result


class TestBuildFilterEcho:
    """Test build_filter_echo function."""

    def test_filter_echo_city(self):
        """Test filter echo with city."""
        filters = {"city": "Paris"}
        result = build_filter_echo(filters, [], "fr")

        assert "Paris" in result
        assert "📍" in result
        assert "Filtres appliqués" in result

    def test_filter_echo_month_and_day(self):
        """Test filter echo with month and day."""
        filters = {"month": 2, "day": [14, 15]}
        result = build_filter_echo(filters, [], "fr")

        assert "14-15" in result
        assert "février" in result or "fevrier" in result

    def test_filter_echo_category(self):
        """Test filter echo with category."""
        filters = {"category": "Musique"}
        result = build_filter_echo(filters, [], "fr")

        assert "Musique" in result
        assert "🎭" in result

    def test_filter_echo_is_free(self):
        """Test filter echo with is_free flag."""
        filters = {"is_free": True}
        result = build_filter_echo(filters, [], "fr")

        assert "gratuit" in result
        assert "🎫" in result

    def test_filter_echo_search_terms(self):
        """Test filter echo with search terms."""
        filters = {}
        search_terms = ["jazz", "rock"]
        result = build_filter_echo(filters, search_terms, "fr")

        assert '"jazz"' in result
        assert '"rock"' in result
        assert "🔍" in result

    def test_filter_echo_empty(self):
        """Test filter echo with no filters."""
        result = build_filter_echo({}, [], "fr")
        assert result == ""

    def test_filter_echo_english(self):
        """Test filter echo in English."""
        filters = {"city": "Paris", "is_free": True}
        result = build_filter_echo(filters, [], "en")

        assert "Applied filters" in result
        assert "free" in result


class TestBuildRefinementSuffix:
    """Test build_refinement_suffix function."""

    def test_refinement_suffix_with_results(self):
        """Test refinement suffix when results found (shorter hint)."""
        filters = {}
        result = build_refinement_suffix(filters, has_results=True, language="fr")

        assert REFINEMENT_HINT["fr"] in result
        assert len(result) < 200  # Shorter hint

    def test_refinement_suffix_without_results(self):
        """Test refinement suffix when no results (full suggestions)."""
        filters = {}
        result = build_refinement_suffix(filters, has_results=False, language="fr")

        # Should include full suggestions (longer)
        assert "Affiner votre recherche" in result or "Want to refine" in result
        assert len(result) > 200  # Full suggestions are longer

    def test_refinement_suffix_with_default_timeframe(self):
        """Test refinement suffix includes timeframe notice when applied."""
        filters = {"_default_timeframe_applied": True}
        result = build_refinement_suffix(filters, has_results=True, language="fr")

        assert "30 prochains jours" in result


class TestDefaultTimeframe:
    """Test default timeframe helper functions."""

    def test_should_apply_default_timeframe_true(self):
        """Test should apply default when no timeframe specified."""
        filters = {"city": "Paris"}
        assert should_apply_default_timeframe(filters) is True

    def test_should_apply_default_timeframe_false_month(self):
        """Test should NOT apply when month specified."""
        filters = {"month": 2}
        assert should_apply_default_timeframe(filters) is False

    def test_should_apply_default_timeframe_false_day(self):
        """Test should NOT apply when day specified."""
        filters = {"day": 15}
        assert should_apply_default_timeframe(filters) is False

    def test_apply_default_timeframe_adds_metadata(self):
        """Test apply_default_timeframe adds metadata fields."""
        filters = {"city": "Paris"}
        result = apply_default_timeframe(filters)

        assert result["_default_timeframe_applied"] is True
        assert "_timeframe_start" in result
        assert "_timeframe_end" in result

    def test_apply_default_timeframe_no_change_when_month_present(self):
        """Test apply_default_timeframe doesn't modify when month specified."""
        filters = {"month": 2}
        result = apply_default_timeframe(filters)

        assert "_default_timeframe_applied" not in result
        assert result == filters


class TestSuffixMarkerStripping:
    """Test that suffix markers are properly detected and stripped."""

    def test_suffix_marker_list_completeness(self):
        """Test SUFFIX_MARKERS list contains expected markers."""
        expected_markers = [
            "📅 *Results filtered",
            "💡 *Specify",
            "💡 **Want to refine",
            "**Applied filters:**",
            "---\n**Applied",
        ]

        for marker in expected_markers:
            assert marker in SUFFIX_MARKERS

    def test_builder_strips_all_known_markers(self):
        """Test builder strips all known suffix markers."""
        for marker in SUFFIX_MARKERS:
            builder = ResponseBuilder(language="fr")
            content_with_marker = f"Main content\n\n{marker} extra content"
            result = builder.set_main_content(content_with_marker).build()

            # Should strip everything after marker
            assert result == "Main content"
            assert marker not in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
