"""Enrich event metadata by inferring missing information."""

import logging
import re
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.data.storage import EventStorage
from src.data.models import Event

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def infer_price_info(event: Event) -> str:
    """Infer if event is free based on description/title."""
    text = f"{event.title} {event.description or ''} {event.scraped_content or ''}".lower()

    # Free indicators
    free_keywords = [
        "gratuit",
        "free",
        "entrée libre",
        "accès libre",
        "admission free",
        "sans frais",
        "gratuité",
        "free admission",
        "free entry",
    ]

    if any(keyword in text for keyword in free_keywords):
        return "Gratuit"

    # Paid indicators with price extraction
    price_patterns = [
        r"(\d+)\s*€",
        r"(\d+)\s*euros?",
        r"tarif\s*:\s*(\d+)",
        r"prix\s*:\s*(\d+)",
    ]

    for pattern in price_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            price = match.group(1)
            return f"Payant (à partir de {price}€)"

    return None  # Cannot infer


def infer_accessibility(event: Event) -> str:
    """Infer accessibility features from description."""
    if event.accessibility:
        return event.accessibility  # Already has info

    text = f"{event.title} {event.description or ''} {event.scraped_content or ''}".lower()

    features = []

    # Wheelchair access
    wheelchair_keywords = [
        "fauteuil roulant",
        "wheelchair",
        "pmr",
        "personnes à mobilité réduite",
        "accessible handicap",
        "handicap accessible",
        "rampe d'accès",
        "ascenseur",
    ]
    if any(kw in text for kw in wheelchair_keywords):
        features.append("Accessible en fauteuil roulant")

    # Hearing impaired
    hearing_keywords = [
        "surtitres",
        "subtitles",
        "langue des signes",
        "sign language",
        "malentendant",
        "hearing impaired",
        "boucle magnétique",
    ]
    if any(kw in text for kw in hearing_keywords):
        features.append("Adapté aux malentendants")

    # Visually impaired
    vision_keywords = ["audiodescription", "audio description", "malvoyant", "visually impaired", "braille", "tactile"]
    if any(kw in text for kw in vision_keywords):
        features.append("Adapté aux malvoyants")

    if features:
        return " | ".join(features)

    return None


def infer_age_suitability(event: Event) -> str:
    """Infer age suitability from description."""
    text = f"{event.title} {event.description or ''} {event.scraped_content or ''}".lower()

    age_indicators = {
        "tout public": "Tout public",
        "family": "Tout public",
        "famille": "Tout public",
        "enfants": "Enfants et famille",
        "children": "Enfants et famille",
        "jeune public": "Jeune public",
        "kids": "Enfants et famille",
        "adultes": "Adultes",
        "adults only": "Adultes",
        "18+": "Adultes (18+)",
        "16+": "Adolescents et adultes (16+)",
    }

    for keyword, label in age_indicators.items():
        if keyword in text:
            return label

    # Check for specific age ranges
    age_range_patterns = [
        r"(\d+)\s*-\s*(\d+)\s*ans",
        r"(\d+)\s*to\s*(\d+)\s*years",
        r"à partir de\s*(\d+)\s*ans",
        r"from\s*(\d+)\s*years",
    ]

    for pattern in age_range_patterns:
        match = re.search(pattern, text)
        if match:
            if len(match.groups()) == 2:
                return f"{match.group(1)}-{match.group(2)} ans"
            else:
                return f"À partir de {match.group(1)} ans"

    return None


def backfill_tags_from_category(event: Event) -> bool:
    """Add category to tags if tags are empty."""
    if not event.tags and event.category:
        event.tags = [event.category]
        return True
    return False


def clean_conditions(event: Event) -> bool:
    """Deduplicate and clean conditions string."""
    if not event.conditions:
        return False

    parts = [p.strip() for p in event.conditions.split("|") if p.strip()]
    # Use dict to deduplicate while preserving order
    unique_parts = list(dict.fromkeys(parts))

    new_conditions = " | ".join(unique_parts)
    if new_conditions != event.conditions:
        event.conditions = new_conditions
        return True
    return False


def enrich_events(limit: int = None) -> dict:
    """Enrich events with inferred metadata.

    Args:
        limit: Maximum number of events to process (None = all)

    Returns:
        Statistics about enrichment
    """
    storage = EventStorage()
    all_events = storage.get_all_events()

    if limit:
        all_events = all_events[:limit]

    stats = {
        "total_processed": len(all_events),
        "price_added": 0,
        "accessibility_added": 0,
        "age_added": 0,
        "tags_backfilled": 0,
        "conditions_cleaned": 0,
        "multiple_enrichments": 0,
    }

    logger.info(f"Processing {len(all_events)} events...")

    for event in all_events:
        enrichments = 0

        # Infer price if missing
        if not event.conditions or "gratuit" not in event.conditions.lower():
            inferred_price = infer_price_info(event)
            if inferred_price:
                # Avoid duplication: only add if not already present
                current = event.conditions or ""
                if inferred_price not in current:
                    event.conditions = f"{current} | {inferred_price}".strip(" |")
                    stats["price_added"] += 1
                    enrichments += 1

        # Clean HTML from description if present
        if event.description and ("<p>" in event.description or "<br>" in event.description):
            clean_desc = re.sub(r"<[^>]+>", "", event.description)
            event.description = clean_desc.strip()
            enrichments += 1

        # Clean/Deduplicate Conditions
        if clean_conditions(event):
            stats["conditions_cleaned"] += 1
            enrichments += 1

        # Backfill Tags
        if backfill_tags_from_category(event):
            stats["tags_backfilled"] += 1
            enrichments += 1

        # Infer accessibility
        inferred_accessibility = infer_accessibility(event)
        if inferred_accessibility:
            event.accessibility = inferred_accessibility
            stats["accessibility_added"] += 1
            enrichments += 1

        # Infer age suitability (store in tags for now)
        age_info = infer_age_suitability(event)
        if age_info and event.tags:
            if age_info not in event.tags:
                event.tags.append(age_info)
                stats["age_added"] += 1
                enrichments += 1

        if enrichments > 1:
            stats["multiple_enrichments"] += 1

        # Update event in storage
        if enrichments > 0:
            storage.update_event(event)

    return stats


def main():
    """Run metadata enrichment."""
    logger.info("=" * 80)
    logger.info("METADATA ENRICHMENT - Inferring Missing Information")
    logger.info("=" * 80)

    # Run enrichment
    stats = enrich_events()

    # Print results
    logger.info("\n" + "=" * 80)
    logger.info("ENRICHMENT RESULTS")
    logger.info("=" * 80)
    logger.info(f"Total events processed: {stats['total_processed']}")
    logger.info(
        f"Price information added: {stats['price_added']} ({stats['price_added']/stats['total_processed']*100:.1f}%)"
    )
    logger.info(
        f"Accessibility information added: {stats['accessibility_added']} ({stats['accessibility_added']/stats['total_processed']*100:.1f}%)"
    )
    logger.info(f"Age suitability added: {stats['age_added']} ({stats['age_added']/stats['total_processed']*100:.1f}%)")
    logger.info(f"Tags backfilled: {stats['tags_backfilled']}")
    logger.info(f"Conditions deduplicated: {stats['conditions_cleaned']}")
    logger.info(f"Events with multiple enrichments: {stats['multiple_enrichments']}")

    logger.info("\n" + "=" * 80)
    logger.info("Next steps:")
    logger.info("1. Re-build FAISS index: poetry run python -m src.models.vector_store")
    logger.info("2. Run evaluation: poetry run python check_metrics.py")
    logger.info("=" * 80)


if __name__ == "__main__":
    main()
