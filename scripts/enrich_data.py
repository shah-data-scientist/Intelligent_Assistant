"""Enrich existing events by scraping their URLs."""

import asyncio
import logging
from src.data.storage import EventStorage
from src.data.scraper import EventScraper
from src.models.vector_store import EventVectorStore

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger(__name__)

async def enrich_events():
    storage = EventStorage()
    scraper = EventScraper()
    
    events = storage.get_all_events()
    logger.info(f"Found {len(events)} events in storage.")
    
    # Filter events that need scraping (missing or too short/garbage content)
    to_scrape = [
        e for e in events 
        if e.url and (not e.scraped_content or len(e.scraped_content) < 500)
    ]
    logger.info(f"{len(to_scrape)} events need scraping (missing or < 500 chars).")
    
    if not to_scrape:
        logger.info("No events to scrape.")
        return

    # Process in batches to avoid overwhelming resources
    BATCH_SIZE = 10
    total_updated = 0
    
    for i in range(0, len(to_scrape), BATCH_SIZE):
        batch = to_scrape[i:i+BATCH_SIZE]
        logger.info(f"Processing batch {i} to {i+len(batch)}...")
        
        tasks = [scraper.scrape_url(e.url) for e in batch]
        results = await asyncio.gather(*tasks)
        
        for event, content in zip(batch, results):
            if content:
                event.scraped_content = content
                storage.update_event(event)
                total_updated += 1
                
    logger.info(f"Enrichment complete. Updated {total_updated} events.")
    
    # Rebuild index
    logger.info("Rebuilding FAISS index with enriched content...")
    with EventVectorStore(storage=storage) as vector_store:
        # Fetch fresh from DB to get updated fields
        all_events = storage.get_all_events()
        vector_store.build_index(all_events)
        vector_store.save_index()
    logger.info("Index rebuilt.")

if __name__ == "__main__":
    asyncio.run(enrich_events())
