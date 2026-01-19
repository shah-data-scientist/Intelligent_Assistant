"""LLM-powered metadata extraction for events."""

import json
import logging
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.data.storage import EventStorage
from src.data.models import Event
from src.config import settings
from langchain_mistralai import ChatMistralAI

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Mistral client
llm = ChatMistralAI(
    model="mistral-small-latest",
    mistral_api_key=settings.mistral_api_key,
    temperature=0.0
)

EXTRACTION_PROMPT = """Extract structured metadata from this cultural event description.

Event Information:
Title: {title}
Category: {category}
Description: {description}

Extract the following in JSON format:
{{
  "price_category": "free" | "paid" | "unknown",
  "price_min": null or number (in euros),
  "price_max": null or number (in euros),
  "age_min": null or number,
  "age_max": null or number,
  "age_description": null or string (e.g., "tout public", "enfants", "adultes"),
  "accessibility_features": [],  // list of: "wheelchair", "hearing_impaired", "visually_impaired"
  "time_of_day": "morning" | "afternoon" | "evening" | "night" | "unknown",
  "is_outdoor": true | false | null
}}

Rules:
- Only extract information explicitly stated in the description
- Use null if information is not mentioned
- Be conservative - don't guess or infer beyond what's stated
- For accessibility, only mark as true if explicitly mentioned
- For prices, look for keywords: "gratuit", "free", "€", "euros", "tarif"
- For ages, look for: "ans", "years", "enfants", "children", "adultes", "adults", "tout public"

Return ONLY the JSON object, no explanation.
"""

def extract_metadata_with_llm(event: Event) -> dict:
    """Use LLM to extract metadata from event description."""

    # Prepare event text
    description = event.description or ""
    if event.scraped_content:
        description += "\n" + event.scraped_content

    # Limit description length to avoid token limits
    if len(description) > 2000:
        description = description[:2000] + "..."

    prompt = EXTRACTION_PROMPT.format(
        title=event.title,
        category=event.category or "Unknown",
        description=description
    )

    try:
        # Call Mistral API via LangChain
        response = llm.invoke(prompt)

        # Parse response
        content = response.content.strip()

        # Extract JSON from response (handle markdown code blocks)
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()

        metadata = json.loads(content)
        return metadata

    except Exception as e:
        logger.error(f"Failed to extract metadata for {event.title}: {e}")
        return None


def apply_extracted_metadata(event: Event, metadata: dict) -> bool:
    """Apply extracted metadata to event object."""

    if not metadata:
        return False

    updated = False

    # Update price information
    if metadata.get("price_category") == "free" and not event.conditions:
        event.conditions = "Gratuit"
        updated = True
    elif metadata.get("price_min") and not event.conditions:
        price_min = metadata["price_min"]
        price_max = metadata.get("price_max")
        if price_max and price_max != price_min:
            event.conditions = f"Payant (de {price_min}€ à {price_max}€)"
        else:
            event.conditions = f"Payant (à partir de {price_min}€)"
        updated = True

    # Update accessibility (append to existing if present)
    accessibility_features = metadata.get("accessibility_features", [])
    if accessibility_features:
        features_text = []
        if "wheelchair" in accessibility_features:
            features_text.append("Accessible en fauteuil roulant")
        if "hearing_impaired" in accessibility_features:
            features_text.append("Adapté aux malentendants")
        if "visually_impaired" in accessibility_features:
            features_text.append("Adapté aux malvoyants")

        if features_text:
            if event.accessibility:
                # Append if not already present
                existing = event.accessibility.lower()
                new_features = [f for f in features_text if f.lower() not in existing]
                if new_features:
                    event.accessibility = event.accessibility + " | " + " | ".join(new_features)
                    updated = True
            else:
                event.accessibility = " | ".join(features_text)
                updated = True

    # Update age description in tags
    age_description = metadata.get("age_description")
    if age_description:
        # Add to tags if not present
        if event.tags is None:
            event.tags = []

        age_tag = f"Public: {age_description}"
        if age_tag not in event.tags:
            event.tags.append(age_tag)
            updated = True

    # Age range in tags
    age_min = metadata.get("age_min")
    age_max = metadata.get("age_max")
    if age_min is not None or age_max is not None:
        if event.tags is None:
            event.tags = []

        if age_min and age_max:
            age_tag = f"Âge: {age_min}-{age_max} ans"
        elif age_min:
            age_tag = f"Âge: à partir de {age_min} ans"
        elif age_max:
            age_tag = f"Âge: jusqu'à {age_max} ans"

        if age_tag not in event.tags:
            event.tags.append(age_tag)
            updated = True

    # Time of day in tags
    time_of_day = metadata.get("time_of_day")
    if time_of_day and time_of_day != "unknown":
        if event.tags is None:
            event.tags = []

        time_tag = f"Horaire: {time_of_day}"
        if time_tag not in event.tags:
            event.tags.append(time_tag)
            updated = True

    # Outdoor event in tags
    is_outdoor = metadata.get("is_outdoor")
    if is_outdoor is True:
        if event.tags is None:
            event.tags = []

        if "Plein air" not in event.tags and "Outdoor" not in event.tags:
            event.tags.append("Plein air")
            updated = True

    return updated


def main():
    """Main extraction pipeline."""

    logger.info("="*80)
    logger.info("LLM-POWERED METADATA EXTRACTION")
    logger.info("="*80)

    # Load events
    storage = EventStorage()
    all_events = storage.get_all_events()

    logger.info(f"\nTotal events: {len(all_events)}")

    # Filter events that need metadata extraction
    # Focus on events with missing metadata
    events_to_process = []
    for event in all_events:
        needs_extraction = False

        # Missing price
        if not event.conditions:
            needs_extraction = True

        # Missing accessibility
        if not event.accessibility:
            needs_extraction = True

        # Has description to work with
        if (event.description or event.scraped_content) and needs_extraction:
            events_to_process.append(event)

    logger.info(f"Events needing metadata extraction: {len(events_to_process)}")

    # Process in batches to show progress
    batch_size = 10
    total_updated = 0
    price_added = 0
    accessibility_added = 0
    age_added = 0
    time_added = 0
    outdoor_added = 0

    logger.info(f"\nProcessing {len(events_to_process)} events...")
    logger.info("This will take approximately 2-3 hours due to API rate limits.\n")

    for i, event in enumerate(events_to_process):
        logger.info(f"[{i+1}/{len(events_to_process)}] Extracting metadata for: {event.title[:60]}...")

        # Extract metadata
        metadata = extract_metadata_with_llm(event)

        if metadata:
            # Track what was added
            had_price = bool(event.conditions)
            had_accessibility = bool(event.accessibility)
            had_age_tags = any("Âge:" in (t or "") for t in (event.tags or []))
            had_time_tags = any("Horaire:" in (t or "") for t in (event.tags or []))
            had_outdoor = any(t in ["Plein air", "Outdoor"] for t in (event.tags or []))

            # Apply metadata
            if apply_extracted_metadata(event, metadata):
                total_updated += 1

                # Update event in storage
                storage.update_event(event)

                # Count what was added
                if not had_price and event.conditions:
                    price_added += 1
                if not had_accessibility and event.accessibility:
                    accessibility_added += 1
                if not had_age_tags and any("Âge:" in (t or "") for t in (event.tags or [])):
                    age_added += 1
                if not had_time_tags and any("Horaire:" in (t or "") for t in (event.tags or [])):
                    time_added += 1
                if not had_outdoor and any(t in ["Plein air", "Outdoor"] for t in (event.tags or [])):
                    outdoor_added += 1

                logger.info(f"  ✓ Updated event with new metadata")
            else:
                logger.info(f"  - No updates needed")

        # Progress checkpoint every batch
        if (i + 1) % batch_size == 0:
            logger.info(f"\n--- Progress: {i+1}/{len(events_to_process)} ---")
            logger.info(f"Events updated: {total_updated}")
            logger.info(f"Price added: {price_added}")
            logger.info(f"Accessibility added: {accessibility_added}")
            logger.info(f"Age info added: {age_added}")
            logger.info(f"Time of day added: {time_added}")
            logger.info(f"Outdoor flag added: {outdoor_added}\n")

    # Final summary
    logger.info("\n" + "="*80)
    logger.info("EXTRACTION COMPLETE")
    logger.info("="*80)
    logger.info(f"\nTotal events processed: {len(events_to_process)}")
    logger.info(f"Events updated: {total_updated} ({total_updated/len(events_to_process)*100:.1f}%)")
    logger.info(f"\nMetadata added:")
    logger.info(f"  - Price information: {price_added}")
    logger.info(f"  - Accessibility features: {accessibility_added}")
    logger.info(f"  - Age information: {age_added}")
    logger.info(f"  - Time of day: {time_added}")
    logger.info(f"  - Outdoor events: {outdoor_added}")
    logger.info(f"\nTotal new metadata entries: {price_added + accessibility_added + age_added + time_added + outdoor_added}")
    logger.info("="*80)

    logger.info("\nNext steps:")
    logger.info("1. Rebuild FAISS index: poetry run python -m src.models.vector_store")
    logger.info("2. Re-evaluate metrics: poetry run python check_metrics.py")


if __name__ == "__main__":
    main()
