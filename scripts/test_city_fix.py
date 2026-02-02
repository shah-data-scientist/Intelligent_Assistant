"""Test city normalization fix."""
import sys
import os
import io
import logging

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Enable debug logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(name)s - %(message)s')

from dotenv import load_dotenv
load_dotenv()

from src.retrieval.unified_analyzer import unified_analyze
from src.retrieval.chain import get_city_locator

# Get known cities
locator = get_city_locator()
known_cities = list(locator.city_cache.keys())
print(f"Loaded {len(known_cities)} known cities")
print(f"Sample: {known_cities[:5]}")

# Test query
query = "Jazz concerts in Paris"
print(f"\n\nTesting query: '{query}'")
print("-" * 50)

result = unified_analyze(query, known_cities=known_cities)

print(f"\nResult:")
print(f"  city (raw): {getattr(result, 'city', None)}")
print(f"  city_normalized: {getattr(result, 'city_normalized', None)}")
print(f"  intent: {result.intent}")
print(f"  filters: {result.filters}")
print(f"  raw_response entities: {result.raw_response.get('entities', {})}")
