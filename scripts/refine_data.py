"""Refine existing event data with normalization and category inference."""

import logging
from datetime import datetime

from src.data.storage import EventStorage
from src.data.processor import EventProcessor
from src.models.vector_store import EventVectorStore

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

def refine_data():
    storage = EventStorage()
    processor = EventProcessor()
    
    logger.info("Fetching events for refinement...")
    events = storage.get_all_events()
    logger.info(f"Retrieved {len(events)} events.")

    refined_events = []
    
    logger.info("Applying normalization and category inference...")
    for event in events:
        if not event.raw_data:
            logger.warning(f"No raw data for event {event.event_id}, skipping.")
            continue
            
        # Re-process from raw data to get clean fields
        clean_event = processor.process_record(event.raw_data)
        if clean_event:
            refined_events.append(clean_event)

    logger.info(f"Successfully cleaned {len(refined_events)} events.")

    # Re-apply seasonal redistribution to maintain the 1-year window
    # Using a fixed date for consistency if needed, but 'now' is fine.
    logger.info("Re-applying seasonal redistribution...")
    final_events = processor.redistribute_events_seasonally(
        refined_events, 
        start_date=datetime(2026, 1, 15)  # Today's date from prompt
    )

    logger.info("Updating database...")
    updated_count = 0
    for event in final_events:
        if storage.update_event(event):
            updated_count += 1
            
    logger.info(f"Updated {updated_count} events in database.")

    # Rebuild FAISS index because metadata (categories, titles) changed
    # and we want the index to be perfectly in sync.
    logger.info("Rebuilding FAISS index...")
    with EventVectorStore(storage=storage) as vector_store:
        stats = vector_store.build_index(final_events)
        vector_store.save_index()
        logger.info(f"FAISS index rebuilt with {stats['events_indexed']} events.")

    storage.close()
    logger.info("Refinement complete.")

if __name__ == "__main__":
    refine_data()
