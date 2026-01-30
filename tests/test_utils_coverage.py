"""Tests for geospatial and keyword detection utilities."""

import pytest
import sqlite3
import json
from unittest.mock import MagicMock, patch
from src.utils.geo import CityLocator, haversine_distance
from src.utils.keywords import KeywordLocator, KeywordMatch

@pytest.fixture
def mock_db_data():
    """Create a temporary in-memory database for testing utilities."""
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()
    
    # 1. Setup events table for CityLocator
    cursor.execute("CREATE TABLE events (city TEXT, coordinates_json TEXT, raw_data_json TEXT)")
    cursor.execute("INSERT INTO events VALUES ('Paris', '{\"lat\": 48.8566, \"lon\": 2.3522}', NULL)")
    cursor.execute("INSERT INTO events VALUES ('Poissy', NULL, '{\"location_coordinates\": {\"lat\": 48.9298, \"lon\": 2.0441}}')")
    
    # 2. Setup search_keywords table for KeywordLocator
    cursor.execute("""
        CREATE TABLE search_keywords (
            keyword TEXT, 
            keyword_type TEXT, 
            language TEXT, 
            canonical TEXT, 
            implied_category TEXT, 
            typos TEXT
        )
    """ 
    )
    # Date Keywords
    cursor.execute("INSERT INTO search_keywords VALUES ('janvier', 'date', 'fr', 'january', NULL, '[\"janv\", \"janveir\"]')")
    cursor.execute("INSERT INTO search_keywords VALUES ('this weekend', 'date', 'en', 'weekend', NULL, '[]')")
    
    # Event Keywords
    cursor.execute("INSERT INTO search_keywords VALUES ('concert', 'event', 'fr', 'concert', 'Musique', '[\"concer\"]')")
    cursor.execute("INSERT INTO search_keywords VALUES ('jazz', 'event', 'en', 'jazz', 'Musique', '[]')")
    
    # Special Keywords
    cursor.execute("INSERT INTO search_keywords VALUES ('bonjour', 'greeting', 'fr', 'hello', NULL, '[]')")
    cursor.execute("INSERT INTO search_keywords VALUES ('how many', 'statistical', 'en', 'count', NULL, '[]')")
    
    conn.commit()
    yield conn
    conn.close()

class TestGeoUtils:
    """Tests for geo.py."""

    def test_city_locator_loading(self, mock_db_data):
        with patch("sqlite3.connect", return_value=mock_db_data):
            locator = CityLocator(db_path="dummy.db")
            assert "paris" in locator.city_cache
            assert "poissy" in locator.city_cache
            assert locator.city_cache["paris"] == (48.8566, 2.3522)

    def test_is_in_scope(self, mock_db_data):
        with patch("sqlite3.connect", return_value=mock_db_data):
            locator = CityLocator(db_path="dummy.db")
            assert locator.is_in_scope("Paris") is True
            assert locator.is_in_scope("Paris 15") is True  # Partial match
            assert locator.is_in_scope("London") is False

    def test_find_closest_city_fuzzy(self, mock_db_data):
        with patch("sqlite3.connect", return_value=mock_db_data):
            locator = CityLocator(db_path="dummy.db")
            assert locator.find_closest_city("Pari") == "paris"
            assert locator.find_closest_city("Possy") == "poissy"
            # "Xyz" should not match anything
            assert locator.find_closest_city("Xyz") is None

    def test_haversine_distance(self):
        # Paris to Poissy is approx 20km
        dist = haversine_distance(48.8566, 2.3522, 48.9298, 2.0441)
        assert 15 < dist < 25

class TestKeywordUtils:
    """Tests for keywords.py."""

    def test_keyword_locator_loading(self, mock_db_data):
        with patch("sqlite3.connect", return_value=mock_db_data):
            locator = KeywordLocator(db_path="dummy.db")
            assert "janvier" in locator.date_keywords
            assert "concert" in locator.event_keywords
            assert "bonjour" in locator.greeting_keywords
            assert "janv" in locator.typo_to_keyword

    def test_detect_date_exact_and_pattern(self, mock_db_data):
        with patch("sqlite3.connect", return_value=mock_db_data):
            locator = KeywordLocator(db_path="dummy.db")
            
            # Exact Multi-word
            match = locator.detect_date("events this weekend")
            assert match.canonical == "weekend"
            assert match.match_type == "exact"
            
            # Pattern (Regex)
            match = locator.detect_date("on 15/01/2026")
            assert match.canonical == "date_dmy"
            assert match.match_type == "pattern"

    def test_detect_event_typo_and_fuzzy(self, mock_db_data):
        with patch("sqlite3.connect", return_value=mock_db_data):
            locator = KeywordLocator(db_path="dummy.db")
            
            # Known Typo
            match = locator.detect_event_type("un concer de rock")
            assert match.matched == "concert"
            assert match.match_type == "typo"
            assert match.implied_category == "Musique"
            
            # Fuzzy Match (Levenshtein)
            match = locator.detect_event_type("i like jaz")
            assert match.matched == "jazz"
            assert match.match_type == "fuzzy"

    def test_detect_special_queries(self, mock_db_data):
        with patch("sqlite3.connect", return_value=mock_db_data):
            locator = KeywordLocator(db_path="dummy.db")
            
            # Greeting
            match = locator.detect_special_query("bonjour")
            assert match.keyword_type == "greeting"
            
            # Statistical
            match = locator.detect_special_query("how many events?")
            assert match.keyword_type == "statistical"

    def test_has_indicators(self, mock_db_data):
        with patch("sqlite3.connect", return_value=mock_db_data):
            locator = KeywordLocator(db_path="dummy.db")
            assert locator.has_date_indicator("en janvier") is True
            assert locator.has_event_indicator("un concert") is True
            assert locator.has_greeting_indicator("salut") is False # not in mock
            assert locator.has_greeting_indicator("bonjour") is True
