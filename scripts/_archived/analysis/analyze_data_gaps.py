"""Analyze data gaps affecting metrics."""

import logging
from src.data.storage import EventStorage

logging.basicConfig(level=logging.WARNING)

storage = EventStorage()
all_events = storage.get_all_events()

print("="*80)
print("DATA QUALITY ANALYSIS - Identifying Gaps")
print("="*80)
print(f"\nTotal Events: {len(all_events)}")

# Analyze metadata completeness
has_price = sum(1 for e in all_events if e.conditions and ('gratuit' in e.conditions.lower() or 'free' in e.conditions.lower() or 'tarif' in e.conditions.lower() or 'price' in e.conditions.lower()))
has_accessibility = sum(1 for e in all_events if e.accessibility)
has_age_info = sum(1 for e in all_events if e.description and any(age in e.description.lower() for age in ['enfant', 'children', 'ans', 'years old', 'âge', 'age']))
has_tags = sum(1 for e in all_events if e.tags and len(e.tags) > 0)

print("\n" + "-"*80)
print("METADATA COMPLETENESS")
print("-"*80)
print(f"Price information: {has_price}/{len(all_events)} ({has_price/len(all_events)*100:.1f}%)")
print(f"Accessibility info: {has_accessibility}/{len(all_events)} ({has_accessibility/len(all_events)*100:.1f}%)")
print(f"Age information: {has_age_info}/{len(all_events)} ({has_age_info/len(all_events)*100:.1f}%)")
print(f"Tags present: {has_tags}/{len(all_events)} ({has_tags/len(all_events)*100:.1f}%)")

# Category distribution
from collections import Counter
categories = Counter(e.category for e in all_events if e.category)
print("\n" + "-"*80)
print("CATEGORY DISTRIBUTION (Top 10)")
print("-"*80)
for cat, count in categories.most_common(10):
    print(f"{cat}: {count} ({count/len(all_events)*100:.1f}%)")

# City distribution
cities = Counter(e.location.city for e in all_events if e.location and e.location.city)
print("\n" + "-"*80)
print("CITY DISTRIBUTION (Top 10)")
print("-"*80)
for city, count in cities.most_common(10):
    print(f"{city}: {count} ({count/len(all_events)*100:.1f}%)")

# Genre analysis (from tags)
all_tags = []
for e in all_events:
    if e.tags:
        all_tags.extend(e.tags)

genre_keywords = ['Jazz', 'Classique', 'Classical', 'Rock', 'Pop', 'Electronic', 'Electro',
                  'Hip-hop', 'Rap', 'World', 'Folk', 'Blues', 'Soul', 'Reggae', 'Metal']
genre_counts = Counter()
for tag in all_tags:
    for genre in genre_keywords:
        if genre.lower() in tag.lower():
            genre_counts[genre] += 1

print("\n" + "-"*80)
print("GENRE DISTRIBUTION (from tags)")
print("-"*80)
for genre, count in genre_counts.most_common(15):
    print(f"{genre}: {count}")

# Free events analysis
free_events = [e for e in all_events if e.conditions and ('gratuit' in e.conditions.lower() or 'free' in e.conditions.lower())]
print("\n" + "-"*80)
print("FREE EVENTS ANALYSIS")
print("-"*80)
print(f"Events marked as free: {len(free_events)}/{len(all_events)} ({len(free_events)/len(all_events)*100:.1f}%)")

if len(free_events) > 0:
    free_categories = Counter(e.category for e in free_events if e.category)
    print("\nFree events by category (Top 5):")
    for cat, count in free_categories.most_common(5):
        print(f"  {cat}: {count}")

# Accessibility analysis
accessible_events = [e for e in all_events if e.accessibility]
print("\n" + "-"*80)
print("ACCESSIBILITY ANALYSIS")
print("-"*80)
print(f"Events with accessibility info: {len(accessible_events)}/{len(all_events)} ({len(accessible_events)/len(all_events)*100:.1f}%)")

if len(accessible_events) > 0:
    accessibility_features = []
    for e in accessible_events:
        if 'fauteuil' in e.accessibility.lower() or 'wheelchair' in e.accessibility.lower():
            accessibility_features.append('wheelchair')
        if 'malentendant' in e.accessibility.lower() or 'hearing' in e.accessibility.lower():
            accessibility_features.append('hearing_impaired')
        if 'malvoyant' in e.accessibility.lower() or 'visually' in e.accessibility.lower():
            accessibility_features.append('visually_impaired')

    feature_counts = Counter(accessibility_features)
    print("\nAccessibility features mentioned:")
    for feature, count in feature_counts.most_common():
        print(f"  {feature}: {count}")

# Language diversity
multilingual_events = [e for e in all_events if e.description and any(lang in e.description.lower() for lang in ['english', 'anglais', 'spanish', 'espagnol', 'german', 'allemand'])]
print("\n" + "-"*80)
print("LANGUAGE DIVERSITY")
print("-"*80)
print(f"Events mentioning other languages: {len(multilingual_events)}/{len(all_events)} ({len(multilingual_events)/len(all_events)*100:.1f}%)")

# Recommendations
print("\n" + "="*80)
print("RECOMMENDATIONS TO IMPROVE METRICS")
print("="*80)

print("\n1. CRITICAL DATA GAPS (affecting Relevancy):")
print(f"   - Only {has_price/len(all_events)*100:.1f}% have price info → Add price metadata")
print(f"   - Only {has_accessibility/len(all_events)*100:.1f}% have accessibility → Add accessibility features")
print(f"   - Only {has_age_info/len(all_events)*100:.1f}% mention age ranges → Extract/infer age suitability")

print("\n2. DIVERSITY IMPROVEMENTS:")
print("   - Add more free events (currently {:.1f}%)".format(len(free_events)/len(all_events)*100))
print("   - Expand genre coverage beyond Jazz/Classical")
print("   - Add more events in suburbs (Paris dominates)")
print("   - Add more multilingual/international events")

print("\n3. IMMEDIATE ACTIONS:")
print("   - Enrich existing events with inferred metadata")
print("   - Improve prompts to handle missing metadata gracefully")
print("   - Add diverse test queries to evaluation dataset")

print("\n" + "="*80)
