"""Optimized LLM metadata extraction - processes only high-value events."""

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
    """Run extraction on optimized subset of events."""

    logger.info("="*80)
    logger.info("LLM METADATA EXTRACTION - OPTIMIZED RUN")
    logger.info("="*80)

    # Load events
    storage = EventStorage()
    all_events = storage.get_all_events()

    logger.info(f"\nTotal events: {len(all_events)}")

    # Filter for high-value candidates:
    # 1. Has substantial description (>100 chars)
    # 2. Missing price OR accessibility
    # 3. Not already processed
    candidates = []
    for event in all_events:
        description = (event.description or "") + (event.scraped_content or "")

        # Need substantial description
        if len(description) < 100:
            continue

        # Missing metadata
        if not event.conditions or not event.accessibility:
            candidates.append(event)

    logger.info(f"High-value candidates: {len(candidates)}")
    logger.info(f"Estimated time: {len(candidates) * 2 / 60:.1f} minutes (2 sec/event)")

    # Process candidates
    total_updated = 0
    price_added = 0
    accessibility_added = 0
    age_added = 0
    time_added = 0
    outdoor_added = 0

    logger.info(f"\nProcessing {len(candidates)} events...\n")

    for i, event in enumerate(candidates):
        if (i + 1) % 10 == 0:
            logger.info(f"[{i+1}/{len(candidates)}] Progress...")

        # Extract metadata
        metadata = extract_metadata_with_llm(event)

        if metadata:
            # Track before
            had_price = bool(event.conditions)
            had_accessibility = bool(event.accessibility)
            had_age = any("Âge:" in str(t) for t in (event.tags or []))
            had_time = any("Horaire:" in str(t) for t in (event.tags or []))
            had_outdoor = any(t in ["Plein air", "Outdoor"] for t in (event.tags or []))

            # Apply
            if apply_extracted_metadata(event, metadata):
                total_updated += 1
                storage.update_event(event)

                # Count additions
                if not had_price and event.conditions:
                    price_added += 1
                if not had_accessibility and event.accessibility:
                    accessibility_added += 1
                if not had_age and any("Âge:" in str(t) for t in (event.tags or [])):
                    age_added += 1
                if not had_time and any("Horaire:" in str(t) for t in (event.tags or [])):
                    time_added += 1
                if not had_outdoor and any(t in ["Plein air", "Outdoor"] for t in (event.tags or [])):
                    outdoor_added += 1

    # Summary
    logger.info("\n" + "="*80)
    logger.info("EXTRACTION COMPLETE")
    logger.info("="*80)
    logger.info(f"\nProcessed: {len(candidates)} events")
    logger.info(f"Updated: {total_updated} ({total_updated/max(len(candidates),1)*100:.1f}%)")
    logger.info(f"\nMetadata added:")
    logger.info(f"  Price: {price_added}")
    logger.info(f"  Accessibility: {accessibility_added}")
    logger.info(f"  Age: {age_added}")
    logger.info(f"  Time of day: {time_added}")
    logger.info(f"  Outdoor: {outdoor_added}")
    logger.info(f"  Total: {price_added + accessibility_added + age_added + time_added + outdoor_added}")
    logger.info("="*80)

    logger.info("\nNext steps:")
    logger.info("1. Rebuild FAISS index: poetry run python -m src.models.vector_store")
    logger.info("2. Re-evaluate: poetry run python check_metrics.py")


if __name__ == "__main__":
    main()
