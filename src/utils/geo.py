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
            cursor.execute('''
                SELECT city, coordinates_json, raw_data_json 
                FROM events 
                WHERE (coordinates_json IS NOT NULL OR raw_data_json IS NOT NULL)
                GROUP BY city
            ''')
            
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
                "villeparisis": (48.9439, 2.6178)
            }
            for city_key, coords in overrides.items():
                if city_key not in self.city_cache:
                    self.city_cache[city_key] = coords

            logger.info(f"Loaded {len(self.city_cache)} city locations from database.")
                
        except Exception as e:
            logger.error(f"Failed to load city cache: {e}")

    def get_coords(self, city_name: str) -> Optional[Tuple[float, float]]:
        """Get coordinates for a city name (case-insensitive)."""
        if not city_name:
            return None
        return self.city_cache.get(city_name.lower().strip())

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance in km between two points."""
    R = 6371  # Earth radius in km

    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    
    a = (math.sin(dlat / 2) * math.sin(dlat / 2) +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) * math.sin(dlon / 2))
    
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c
