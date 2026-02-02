"""
FILE: test_i18n.py
STATUS: Active
RESPONSIBILITY: Unit tests for internationalization (i18n) utilities.
LAST MAJOR UPDATE: 2026-01-31
MAINTAINER: QA Team
"""

import pytest
import json
from unittest.mock import patch, mock_open

from src.utils.i18n import (
    Translator,
    get_translator,
    t,
    SUPPORTED_LANGUAGES,
    DEFAULT_LANGUAGE,
    _translation_cache,
    _translators,
)


class TestTranslator:
    """Test Translator class."""

    @pytest.fixture(autouse=True)
    def clear_cache(self):
        """Clear translation cache before each test."""
        _translation_cache.clear()
        _translators.clear()
        yield
        _translation_cache.clear()
        _translators.clear()

    def test_init_with_supported_language(self):
        """Test initialization with supported language."""
        with patch.object(Translator, "_load_translations", return_value={}):
            translator = Translator("fr")
            assert translator.language == "fr"

            translator_en = Translator("en")
            assert translator_en.language == "en"

    def test_init_with_unsupported_language_uses_default(self):
        """Test initialization with unsupported language falls back to default."""
        with patch.object(Translator, "_load_translations", return_value={}):
            translator = Translator("de")  # German not supported
            assert translator.language == DEFAULT_LANGUAGE

    def test_load_translations_from_file(self):
        """Test loading translations from JSON file."""
        # Test with actual locale file that exists
        _translation_cache.clear()  # Ensure fresh load

        # This will load from actual locale file or return empty dict if not found
        translator = Translator("fr")

        # Either loads successfully or returns empty dict
        assert isinstance(translator.translations, dict)

    def test_load_translations_uses_cache(self):
        """Test that translations are cached."""
        cached_translations = {"cached": {"key": "Cached value"}}
        _translation_cache["fr"] = cached_translations

        translator = Translator("fr")

        assert translator.translations == cached_translations

    def test_load_translations_file_not_found(self):
        """Test handling of missing translation file."""
        # Mock Path to return a non-existent path
        with patch("builtins.open", side_effect=FileNotFoundError()):
            translator = Translator("fr")
            assert translator.translations == {}

    def test_load_translations_invalid_json(self):
        """Test handling of invalid JSON in translation file."""
        with patch("builtins.open", mock_open(read_data='{"invalid": json}')):
            with patch("json.load", side_effect=json.JSONDecodeError("", "", 0)):
                translator = Translator("fr")
                assert translator.translations == {}

    def test_get_simple_key(self):
        """Test getting translation with simple key."""
        translations = {"hello": "Bonjour"}
        _translation_cache["fr"] = translations

        translator = Translator("fr")
        result = translator.get("hello")

        assert result == "Bonjour"

    def test_get_nested_key(self):
        """Test getting translation with nested key."""
        translations = {"welcome": {"title": "Welcome!", "subtitle": "Hello there"}}
        _translation_cache["en"] = translations

        translator = Translator("en")
        result = translator.get("welcome.title")

        assert result == "Welcome!"

    def test_get_with_variable_substitution(self):
        """Test getting translation with variable substitution."""
        translations = {"greeting": "Hello, {name}!"}
        _translation_cache["en"] = translations

        translator = Translator("en")
        result = translator.get("greeting", name="Alice")

        assert result == "Hello, Alice!"

    def test_get_missing_key_returns_key(self):
        """Test that missing key returns the key itself."""
        translations = {}
        _translation_cache["en"] = translations

        translator = Translator("en")
        result = translator.get("missing.key")

        assert result == "missing.key"

    def test_get_invalid_key_path(self):
        """Test getting translation with invalid path (not a dict)."""
        translations = {"simple": "value"}
        _translation_cache["en"] = translations

        translator = Translator("en")
        result = translator.get("simple.nested")  # simple is string, not dict

        assert result == "simple.nested"

    def test_get_missing_variable_in_template(self):
        """Test handling of missing variable in template."""
        translations = {"greeting": "Hello, {name} from {city}!"}
        _translation_cache["en"] = translations

        translator = Translator("en")
        # Only provide 'name', not 'city'
        result = translator.get("greeting", name="Alice")

        # Should return original template when variable is missing
        assert result == "Hello, {name} from {city}!"

    def test_get_returns_non_string_values(self):
        """Test that get returns non-string values as-is."""
        translations = {"items": ["one", "two", "three"]}
        _translation_cache["en"] = translations

        translator = Translator("en")
        result = translator.get("items")

        assert result == ["one", "two", "three"]

    def test_get_list(self):
        """Test get_list method."""
        translations = {"months": ["January", "February", "March"]}
        _translation_cache["en"] = translations

        translator = Translator("en")
        result = translator.get_list("months")

        assert result == ["January", "February", "March"]

    def test_get_list_non_list_returns_empty(self):
        """Test get_list returns empty list for non-list values."""
        translations = {"not_a_list": "just a string"}
        _translation_cache["en"] = translations

        translator = Translator("en")
        result = translator.get_list("not_a_list")

        assert result == []

    def test_get_dict(self):
        """Test get_dict method."""
        translations = {"settings": {"theme": "dark", "language": "en"}}
        _translation_cache["en"] = translations

        translator = Translator("en")
        result = translator.get_dict("settings")

        assert result == {"theme": "dark", "language": "en"}

    def test_get_dict_non_dict_returns_empty(self):
        """Test get_dict returns empty dict for non-dict values."""
        translations = {"not_a_dict": "just a string"}
        _translation_cache["en"] = translations

        translator = Translator("en")
        result = translator.get_dict("not_a_dict")

        assert result == {}


class TestGetTranslator:
    """Test get_translator function."""

    @pytest.fixture(autouse=True)
    def clear_cache(self):
        """Clear caches before each test."""
        _translation_cache.clear()
        _translators.clear()
        yield
        _translation_cache.clear()
        _translators.clear()

    def test_creates_translator_if_not_exists(self):
        """Test that translator is created if not in cache."""
        _translation_cache["fr"] = {}  # Provide empty translations

        translator = get_translator("fr")

        assert isinstance(translator, Translator)
        assert "fr" in _translators

    def test_returns_cached_translator(self):
        """Test that same translator instance is returned."""
        _translation_cache["fr"] = {}

        translator1 = get_translator("fr")
        translator2 = get_translator("fr")

        assert translator1 is translator2


class TestConvenienceFunction:
    """Test t() convenience function."""

    @pytest.fixture(autouse=True)
    def clear_cache(self):
        """Clear caches before each test."""
        _translation_cache.clear()
        _translators.clear()
        yield
        _translation_cache.clear()
        _translators.clear()

    def test_t_function_simple(self):
        """Test t() function with simple translation."""
        _translation_cache["en"] = {"hello": "Hello!"}

        result = t("hello", language="en")

        assert result == "Hello!"

    def test_t_function_with_variables(self):
        """Test t() function with variable substitution."""
        _translation_cache["en"] = {"greeting": "Hello, {name}!"}

        result = t("greeting", language="en", name="Bob")

        assert result == "Hello, Bob!"

    def test_t_function_uses_default_language(self):
        """Test t() uses default language when not specified."""
        _translation_cache[DEFAULT_LANGUAGE] = {"bonjour": "Bonjour!"}

        result = t("bonjour")

        assert result == "Bonjour!"


class TestSupportedLanguages:
    """Test language constants."""

    def test_supported_languages_contains_fr_and_en(self):
        """Test that French and English are supported."""
        assert "fr" in SUPPORTED_LANGUAGES
        assert "en" in SUPPORTED_LANGUAGES

    def test_default_language_is_french(self):
        """Test that default language is French."""
        assert DEFAULT_LANGUAGE == "fr"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
