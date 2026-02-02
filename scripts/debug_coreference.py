"""Debug coreference resolution for 'Parle-moi du premier'."""
import os
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from src.retrieval.unified_analyzer import unified_analyze
from datetime import date

# Simulate previous events (what would be in chat history)
previous_events = [
    {"title": "Zoot Sundays! Sessions Jazz du dimanche", "city": "Paris", "category": "Musique"},
    {"title": "Jorge Vistel Quartet", "city": "Paris", "category": "Musique"},
    {"title": "Laurent Coulondre Concert", "city": "Paris", "category": "Musique"},
]

# Known cities
known_cities = ["Paris", "Versailles", "Poissy", "Montreuil"]

# Test queries that reference previous results
test_queries = [
    "Parle-moi du premier",
    "Tell me about the first one",
    "Le deuxieme",
    "What about the second one",
    "More info on Zoot Sundays",
]

print("=" * 70)
print("DEBUG: Coreference Resolution")
print("=" * 70)

for query in test_queries:
    print(f"\nQuery: '{query}'")
    print("-" * 50)

    result = unified_analyze(
        query=query,
        chat_history=None,
        known_cities=known_cities,
        previous_events=previous_events
    )

    print(f"  Intent: {result.intent.value}")
    print(f"  Coreference in raw_response: {result.raw_response.get('coreference', {})}")

    coref = result.raw_response.get('coreference', {})
    if coref.get('references_previous'):
        print(f"  [OK] references_previous = True")
        print(f"  [OK] event_name = {coref.get('event_name')}")
        print(f"  [OK] reference_type = {coref.get('reference_type')}")
    else:
        print(f"  [FAIL] references_previous = False or missing")
        print(f"  Full coreference: {coref}")

print("\n" + "=" * 70)
