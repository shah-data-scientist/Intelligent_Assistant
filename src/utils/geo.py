"""Geospatial utilities for distance calculation and city lookup."""

import math
import sqlite3
import json
import logging
from typing import Dict, Tuple, Optional

logger = logging.getLogger(__name__)


class CityLocator:
    def __init__(self, db_path: str = "data/events.db"):
        self.db_path = db_path
        self.city_cache: Dict[str, Tuple[float, float]] = {}
        self._load_cities()

    def _load_cities(self):
        """Build a lookup table of cities -> (lat, lon) from existing events."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Get one coordinate sample per normalized city
            # Check both coordinates_json and raw_data_json (as backup)
            cursor.execute(
                """
                SELECT city, coordinates_json, raw_data_json
                FROM events
                WHERE (coordinates_json IS NOT NULL OR raw_data_json IS NOT NULL)
                GROUP BY city
            """
            )

            for city, coords_str, raw_json in cursor.fetchall():
                if not city:
                    continue

                # Try coordinates_json first
                try:
                    if coords_str:
                        coords = json.loads(coords_str)
                        if "lat" in coords and "lon" in coords:
                            key = city.lower().strip()
                            self.city_cache[key] = (float(coords["lat"]), float(coords["lon"]))
                            continue
                except (json.JSONDecodeError, ValueError):
                    pass

                # Try raw_data_json as fallback
                try:
                    if raw_json:
                        raw_data = json.loads(raw_json)
                        # Opendatasoft format often has location_coordinates
                        coords = raw_data.get("location_coordinates")
                        if coords and isinstance(coords, dict) and "lat" in coords and "lon" in coords:
                            key = city.lower().strip()
                            self.city_cache[key] = (float(coords["lat"]), float(coords["lon"]))
                except (json.JSONDecodeError, ValueError):
                    continue

            conn.close()

            # Manual overrides for major centers and test cities
            overrides = {
                "paris": (48.8566, 2.3522),
                "poissy": (48.9298, 2.0441),
                "bondy": (48.9022, 2.4828),
                "versailles": (48.8049, 2.1204),
                "saint-germain-en-laye": (48.8989, 2.0938),
                "villeparisis": (48.9439, 2.6178),
            }
            for city_key, coords in overrides.items():
                if city_key not in self.city_cache:
                    self.city_cache[city_key] = coords

            # City aliases: short names → full official names
            # Maps common short forms to their official IDF city names
            # This handles compound French city names where users use short forms
            aliases = {
                # Saint-Ouen variants
                "saint-ouen": "saint-ouen-sur-seine",
                "st-ouen": "saint-ouen-sur-seine",
                "st ouen": "saint-ouen-sur-seine",
                "saintouen": "saint-ouen-sur-seine",
                "saint ouen": "saint-ouen-sur-seine",
                # Sainte-Geneviève variants
                "sainte-genevieve": "sainte-geneviève-des-bois",
                "ste-genevieve": "sainte-geneviève-des-bois",
                "sainte genevieve": "sainte-geneviève-des-bois",
                # Saint-Maur variants
                "saint-maur": "saint-maur-des-fossés",
                "st-maur": "saint-maur-des-fossés",
                "saint maur": "saint-maur-des-fossés",
                # Saint-Germain variants
                "saint-germain": "saint-germain-en-laye",
                "st-germain": "saint-germain-en-laye",
                "saint germain": "saint-germain-en-laye",
                # Plessis-Robinson variants (FIXES: "Plessis" not matching)
                "plessis": "le plessis-robinson",
                "le plessis": "le plessis-robinson",
                "plessis robinson": "le plessis-robinson",
                "plessis-robinson": "le plessis-robinson",
                # Boulogne-Billancourt variants
                "boulogne": "boulogne-billancourt",
                "boulogne billancourt": "boulogne-billancourt",
                # Issy-les-Moulineaux variants
                "issy": "issy-les-moulineaux",
                "issy les moulineaux": "issy-les-moulineaux",
                # Neuilly-sur-Seine variants
                "neuilly": "neuilly-sur-seine",
                "neuilly sur seine": "neuilly-sur-seine",
                # Levallois-Perret variants
                "levallois": "levallois-perret",
                "levallois perret": "levallois-perret",
                # Fontenay-sous-Bois variants
                "fontenay": "fontenay-sous-bois",
                "fontenay sous bois": "fontenay-sous-bois",
                # Vincennes and surroundings
                "nogent": "nogent-sur-marne",
                "nogent sur marne": "nogent-sur-marne",
                # Clichy variants
                "clichy": "clichy-la-garenne",
                "clichy la garenne": "clichy-la-garenne",
            }
            for alias, official in aliases.items():
                if official in self.city_cache and alias not in self.city_cache:
                    self.city_cache[alias] = self.city_cache[official]

            logger.info(f"Loaded {len(self.city_cache)} city locations from database.")

        except Exception as e:
            logger.error(f"Failed to load city cache: {e}")

    def get_coords(self, city_name: str) -> Optional[Tuple[float, float]]:
        """Get coordinates for a city name (case-insensitive)."""
        if not city_name:
            return None
        return self.city_cache.get(city_name.lower().strip())

    def is_in_scope(self, city_name: str) -> bool:
        """Check if a city is within the Île-de-France region scope.

        Simple logic: If the city is in our database, it's in scope.
        Everything else is out of scope. The database IS the source of truth.
        """
        if not city_name:
            return True  # No city specified = search all IDF

        city_key = city_name.lower().strip()

        # Known cities in our database are in scope
        if city_key in self.city_cache:
            return True

        # Check for partial matches (e.g., "Paris 15" matches "paris")
        for known_city in self.city_cache.keys():
            if city_key in known_city or known_city in city_key:
                return True

        # Not in database = out of scope
        logger.debug(f"City '{city_name}' not found in database - out of scope")
        return False

    def get_known_cities(self) -> list:
        """Return list of all known cities in the database."""
        return list(self.city_cache.keys())

    def find_closest_city(self, city_name: str, threshold: float = 0.75) -> Optional[str]:
        """Find closest matching city using Levenshtein distance (fuzzy matching).

        This helps handle typos like "Possy" → "Poissy", "Pari" → "Paris".

        Args:
            city_name: The city name to match (possibly misspelled)
            threshold: Minimum similarity ratio (0.0 to 1.0). Default 0.75.

        Returns:
            The closest matching known city name, or None if no match above threshold.
        """
        from difflib import SequenceMatcher

        if not city_name:
            return None

        city_key = city_name.lower().strip()

        # Skip if exact match exists
        if city_key in self.city_cache:
            return city_key

        best_match = None
        best_ratio = 0.0

        for known_city in self.city_cache.keys():
            # Calculate similarity ratio
            ratio = SequenceMatcher(None, city_key, known_city).ratio()

            if ratio > best_ratio and ratio >= threshold:
                best_ratio = ratio
                best_match = known_city

        if best_match:
            logger.info(f"Fuzzy matched '{city_name}' -> '{best_match}' (similarity: {best_ratio:.2f})")

        return best_match


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance in km between two points."""
    R = 6371  # Earth radius in km

    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)

    a = math.sin(dlat / 2) * math.sin(dlat / 2) + math.cos(math.radians(lat1)) * math.cos(
        math.radians(lat2)
    ) * math.sin(dlon / 2) * math.sin(dlon / 2)

    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c
