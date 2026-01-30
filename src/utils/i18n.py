"""
FILE: i18n.py
STATUS: Active
RESPONSIBILITY: Internationalization (i18n) utilities for bilingual support.

DEPENDENCIES (Who uses this file):
- src/generation/prompts.py: RAG system prompts
- src/retrieval/response_builder.py: Response templates
- src/frontend/app.py: UI text
- src/retrieval/clarifications.py: Clarification questions

IMPORTS (What this file needs):
- json: Load locale files
- pathlib: File path handling
- typing: Type hints

LAST MAJOR UPDATE: 2026-01-31 (v1.10.0 - initial i18n framework)
MAINTAINER: Core Team
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger(__name__)

# Supported languages
SUPPORTED_LANGUAGES = {"fr", "en"}
DEFAULT_LANGUAGE = "fr"

# Cache for loaded translations
_translation_cache: Dict[str, Dict[str, Any]] = {}


class Translator:
    """Translator for bilingual support using JSON locale files.

    Usage:
        t = Translator(language="fr")
        welcome = t.get("welcome.title", name="Lumi")
        # Returns: "Salut ! Moi c'est **Lumi** 🎭 — Votre guide culturel"
    """

    def __init__(self, language: str = DEFAULT_LANGUAGE):
        """Initialize translator with specified language.

        Args:
            language: Language code (fr/en)
        """
        self.language = language if language in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE
        self.translations = self._load_translations()

    def _load_translations(self) -> Dict[str, Any]:
        """Load translations from JSON file.

        Returns:
            Translation dictionary
        """
        # Check cache first
        if self.language in _translation_cache:
            logger.debug(f"[I18N] Using cached translations for {self.language}")
            return _translation_cache[self.language]

        # Load from file
        locale_path = Path(__file__).parent.parent.parent / "data" / "locales" / f"{self.language}.json"

        try:
            with open(locale_path, "r", encoding="utf-8") as f:
                translations = json.load(f)
                _translation_cache[self.language] = translations
                logger.info(f"[I18N] Loaded translations for {self.language} from {locale_path}")
                return translations
        except FileNotFoundError:
            logger.error(f"[I18N] Translation file not found: {locale_path}")
            # Fallback to empty dict
            return {}
        except json.JSONDecodeError as e:
            logger.error(f"[I18N] Invalid JSON in {locale_path}: {e}")
            return {}

    def get(self, key: str, **kwargs) -> str:
        """Get translation by key with variable substitution.

        Args:
            key: Translation key (dot-separated path, e.g., "welcome.title")
            **kwargs: Variables for substitution

        Returns:
            Translated text with variables substituted

        Examples:
            >>> t = Translator("fr")
            >>> t.get("welcome.title", name="Lumi")
            'Salut ! Moi c'est **Lumi** 🎭 — Votre guide culturel'

            >>> t.get("filters.city", value="Paris")
            ' à **Paris**'
        """
        # Navigate nested dictionary using dot notation
        value = self.translations
        for part in key.split("."):
            if isinstance(value, dict):
                value = value.get(part)
            else:
                logger.warning(f"[I18N] Invalid key path: {key}")
                return key  # Return key itself as fallback

        # If key not found, return the key itself
        if value is None:
            logger.warning(f"[I18N] Translation not found: {key}")
            return key

        # If value is a string, apply variable substitution
        if isinstance(value, str):
            try:
                return value.format(**kwargs) if kwargs else value
            except KeyError as e:
                logger.error(f"[I18N] Missing variable in template {key}: {e}")
                return value

        # If value is not a string, return as-is (for lists, dicts)
        return value

    def get_list(self, key: str) -> list:
        """Get translation list (e.g., month names).

        Args:
            key: Translation key

        Returns:
            List of strings
        """
        value = self.get(key)
        if isinstance(value, list):
            return value
        else:
            logger.warning(f"[I18N] Expected list for {key}, got {type(value)}")
            return []

    def get_dict(self, key: str) -> dict:
        """Get translation dictionary (e.g., clarification questions).

        Args:
            key: Translation key

        Returns:
            Dictionary
        """
        value = self.get(key)
        if isinstance(value, dict):
            return value
        else:
            logger.warning(f"[I18N] Expected dict for {key}, got {type(value)}")
            return {}


# Global translator instances (lazy-loaded)
_translators: Dict[str, Translator] = {}


def get_translator(language: str = DEFAULT_LANGUAGE) -> Translator:
    """Get or create a translator instance for the specified language.

    Args:
        language: Language code (fr/en)

    Returns:
        Translator instance
    """
    if language not in _translators:
        _translators[language] = Translator(language)
    return _translators[language]


# Convenience function for quick translation
def t(key: str, language: str = DEFAULT_LANGUAGE, **kwargs) -> str:
    """Quick translation function.

    Args:
        key: Translation key
        language: Language code
        **kwargs: Variables for substitution

    Returns:
        Translated text

    Example:
        >>> t("welcome.title", language="fr", name="Lumi")
        'Salut ! Moi c'est **Lumi** 🎭 — Votre guide culturel'
    """
    translator = get_translator(language)
    return translator.get(key, **kwargs)
