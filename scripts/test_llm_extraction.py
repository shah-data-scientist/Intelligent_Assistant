"""Test LLM metadata extraction on a small sample."""

import logging
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.llm_metadata_extraction import extract_metadata_with_llm, apply_extracted_metadata
from src.data.storage import EventStorage

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Test extraction on 5 sample events."""

    logger.info("="*80)
    logger.info("LLM METADATA EXTRACTION - TEST RUN (5 events)")
    logger.info("="*80)

    # Load events
    storage = EventStorage()
    all_events = storage.get_all_events()

    # Get 5 events with missing metadata
    test_events = []
    for event in all_events:
        if (not event.conditions or not event.accessibility) and (event.description or event.scraped_content):
            test_events.append(event)
            if len(test_events) >= 5:
                break

    logger.info(f"\nTesting on {len(test_events)} events:\n")

    for i, event in enumerate(test_events, 1):
        logger.info(f"[{i}/{len(test_events)}] Event: {event.title}")
        logger.info(f"  Category: {event.category}")
        logger.info(f"  Current conditions: {event.conditions or 'None'}")
        logger.info(f"  Current accessibility: {event.accessibility or 'None'}")

        # Extract metadata
        metadata = extract_metadata_with_llm(event)

        if metadata:
            logger.info(f"\n  Extracted metadata:")
            logger.info(f"    Price category: {metadata.get('price_category')}")
            logger.info(f"    Price range: {metadata.get('price_min')} - {metadata.get('price_max')} EUR")
            logger.info(f"    Age range: {metadata.get('age_min')} - {metadata.get('age_max')}")
            logger.info(f"    Age description: {metadata.get('age_description')}")
            logger.info(f"    Accessibility: {metadata.get('accessibility_features')}")
            logger.info(f"    Time of day: {metadata.get('time_of_day')}")
            logger.info(f"    Outdoor: {metadata.get('is_outdoor')}")

            # Test application (don't save)
            if apply_extracted_metadata(event, metadata):
                logger.info(f"\n  Would update:")
                logger.info(f"    New conditions: {event.conditions}")
                logger.info(f"    New accessibility: {event.accessibility}")
                logger.info(f"    New tags: {event.tags}")
            else:
                logger.info(f"\n  No updates would be made")
        else:
            logger.info(f"  Failed to extract metadata")

        logger.info("\n" + "-"*80 + "\n")

    logger.info("="*80)
    logger.info("TEST COMPLETE")
    logger.info("="*80)
    logger.info("\nIf results look good, run full extraction:")
    logger.info("  poetry run python scripts/llm_metadata_extraction.py")


if __name__ == "__main__":
    main()
