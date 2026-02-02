"""
FILE: test_geo_integration.py
STATUS: Active
RESPONSIBILITY: Integration tests for geospatial utilities.
LAST MAJOR UPDATE: 2026-01-31
MAINTAINER: QA Team
"""

import pytest
import sqlite3

from src.utils.geo import CityLocator, haversine_distance


class TestHaversineDistance:
    """Test haversine distance calculation."""

    def test_same_point(self):
        """Test distance between same point is zero."""
        dist = haversine_distance(48.8566, 2.3522, 48.8566, 2.3522)
        assert dist == 0.0

    def test_paris_to_versailles(self):
        """Test distance from Paris to Versailles (~18km)."""
        # Paris: 48.8566, 2.3522
        # Versailles: 48.8049, 2.1204
        dist = haversine_distance(48.8566, 2.3522, 48.8049, 2.1204)
        assert 15 < dist < 25  # ~18km

    def test_paris_to_poissy(self):
        """Test distance from Paris to Poissy (~25km)."""
        # Paris: 48.8566, 2.3522
        # Poissy: 48.9298, 2.0441
        dist = haversine_distance(48.8566, 2.3522, 48.9298, 2.0441)
        assert 20 < dist < 30  # ~25km

    def test_symmetry(self):
        """Test that distance is symmetric (A->B == B->A)."""
        dist_ab = haversine_distance(48.8566, 2.3522, 48.9298, 2.0441)
        dist_ba = haversine_distance(48.9298, 2.0441, 48.8566, 2.3522)
        assert abs(dist_ab - dist_ba) < 0.01

    def test_large_distance(self):
        """Test distance across larger area (Paris to Fontainebleau ~60km)."""
        # Paris: 48.8566, 2.3522
        # Fontainebleau: 48.4046, 2.7016
        dist = haversine_distance(48.8566, 2.3522, 48.4046, 2.7016)
        assert 50 < dist < 70


class TestCityLocatorWithMockDB:
    """Test CityLocator with mock database."""

    @pytest.fixture
    def mock_db_connection(self, tmp_path):
        """Create a temporary in-memory database for testing."""
        db_path = str(tmp_path / "test_events.db")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Create events table
        cursor.execute(
            """
            CREATE TABLE events (
                city TEXT,
                coordinates_json TEXT,
                raw_data_json TEXT
            )
        """
        )

        # Insert test data
        test_data = [
            ("Paris", '{"lat": 48.8566, "lon": 2.3522}', None),
            ("Versailles", '{"lat": 48.8049, "lon": 2.1204}', None),
            ("Poissy", None, '{"location_coordinates": {"lat": 48.9298, "lon": 2.0441}}'),
            ("Lyon", None, None),  # No coordinates - should be skipped
        ]

        cursor.executemany("INSERT INTO events VALUES (?, ?, ?)", test_data)

        conn.commit()
        conn.close()
        return db_path

    def test_load_cities_from_db(self, mock_db_connection):
        """Test that cities are loaded from database."""
        locator = CityLocator(db_path=mock_db_connection)

        assert "paris" in locator.city_cache
        assert "versailles" in locator.city_cache
        assert "poissy" in locator.city_cache

    def test_get_coords(self, mock_db_connection):
        """Test getting coordinates for a city."""
        locator = CityLocator(db_path=mock_db_connection)

        coords = locator.get_coords("Paris")
        assert coords is not None
        assert coords == (48.8566, 2.3522)

    def test_get_coords_case_insensitive(self, mock_db_connection):
        """Test that get_coords is case insensitive."""
        locator = CityLocator(db_path=mock_db_connection)

        assert locator.get_coords("PARIS") == locator.get_coords("paris")
        assert locator.get_coords("Paris") == locator.get_coords("paris")

    def test_get_coords_unknown_city(self, mock_db_connection):
        """Test getting coords for unknown city returns None."""
        locator = CityLocator(db_path=mock_db_connection)

        coords = locator.get_coords("UnknownCity")
        assert coords is None

    def test_is_in_scope_known_city(self, mock_db_connection):
        """Test is_in_scope for known city."""
        locator = CityLocator(db_path=mock_db_connection)

        assert locator.is_in_scope("Paris") is True
        assert locator.is_in_scope("Versailles") is True

    def test_is_in_scope_unknown_city(self, mock_db_connection):
        """Test is_in_scope for unknown city."""
        locator = CityLocator(db_path=mock_db_connection)

        assert locator.is_in_scope("London") is False
        assert locator.is_in_scope("Berlin") is False

    def test_is_in_scope_empty_returns_true(self, mock_db_connection):
        """Test that empty city name returns True (search all)."""
        locator = CityLocator(db_path=mock_db_connection)

        assert locator.is_in_scope("") is True
        assert locator.is_in_scope(None) is True

    def test_is_in_scope_partial_match(self, mock_db_connection):
        """Test partial match (e.g., 'Paris 15' matches 'paris')."""
        locator = CityLocator(db_path=mock_db_connection)

        # Paris 15 contains "paris" so should match
        # This tests the substring matching logic
        assert locator.is_in_scope("Paris 15") is True

    def test_get_known_cities(self, mock_db_connection):
        """Test getting list of known cities."""
        locator = CityLocator(db_path=mock_db_connection)

        cities = locator.get_known_cities()
        assert isinstance(cities, list)
        assert "paris" in cities
        assert len(cities) >= 3

    def test_find_closest_city_exact_match(self, mock_db_connection):
        """Test fuzzy match with exact match."""
        locator = CityLocator(db_path=mock_db_connection)

        result = locator.find_closest_city("Paris")
        assert result == "paris"

    def test_find_closest_city_fuzzy_match(self, mock_db_connection):
        """Test fuzzy match with typo."""
        locator = CityLocator(db_path=mock_db_connection)

        # "Pari" should match "paris"
        result = locator.find_closest_city("Pari")
        assert result == "paris"

    def test_find_closest_city_no_match(self, mock_db_connection):
        """Test fuzzy match with no close match."""
        locator = CityLocator(db_path=mock_db_connection)

        result = locator.find_closest_city("xyz")
        assert result is None


class TestCityLocatorOverrides:
    """Test CityLocator with manual overrides."""

    @pytest.fixture
    def empty_db(self, tmp_path):
        """Create empty database."""
        db_path = str(tmp_path / "empty.db")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE events (
                city TEXT,
                coordinates_json TEXT,
                raw_data_json TEXT
            )
        """
        )
        conn.commit()
        conn.close()
        return db_path

    def test_manual_overrides_added(self, empty_db):
        """Test that manual overrides are added even with empty DB."""
        locator = CityLocator(db_path=empty_db)

        # These are the manual overrides from the code
        assert "paris" in locator.city_cache
        assert "poissy" in locator.city_cache
        assert "versailles" in locator.city_cache

    def test_override_coordinates_correct(self, empty_db):
        """Test that override coordinates are correct."""
        locator = CityLocator(db_path=empty_db)

        paris_coords = locator.get_coords("paris")
        assert paris_coords == (48.8566, 2.3522)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
