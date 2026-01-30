"""Enrich existing events by scraping their URLs."""

import asyncio
import logging
import argparse
from src.data.storage import EventStorage
from src.data.scraper import EventScraper
from src.data.processor import EventProcessor
from src.models.vector_store import EventVectorStore

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger(__name__)

async def enrich_events(limit=None):
    storage = EventStorage()
    scraper = EventScraper()
    processor = EventProcessor()
    
    events = storage.get_all_events()
    logger.info(f"Found {len(events)} events in storage.")
    
    # Filter events that need scraping
    to_scrape = [
        e for e in events 
        if e.url and (not e.scraped_content or len(e.scraped_content) < 500)
    ]
    
    if limit:
        to_scrape = to_scrape[:limit]
        
    logger.info(f"{len(to_scrape)} events will be processed.")
    
    if not to_scrape:
        logger.info("No events to scrape.")
        return

    BATCH_SIZE = 5  # Reduced batch size for stability
    total_updated = 0
    
    for i in range(0, len(to_scrape), BATCH_SIZE):
        batch = to_scrape[i:i+BATCH_SIZE]
        logger.info(f"Batch {i//BATCH_SIZE + 1}: Processing {len(batch)} URLs...")
        
        try:
            tasks = [scraper.scrape_url(e.url) for e in batch]
            results = await asyncio.gather(*tasks)
            
            for event, content in zip(batch, results):
                if content and len(content) > 100:
                    # Clean the content using processor rules
                    cleaned_content = processor.remove_boilerplate(content)
                    cleaned_content = processor.safe_normalize(cleaned_content)
                    
                    event.scraped_content = cleaned_content
                    storage.update_event(event)
                    total_updated += 1
        except Exception as e:
            logger.error(f"Error in batch: {e}")
                
    logger.info(f"Enrichment complete. Updated {total_updated}/{len(to_scrape)} events.")
    
    if total_updated > 0:
        logger.info("Rebuilding FAISS index with enriched content...")
        with EventVectorStore(storage=storage) as vector_store:
            all_events = storage.get_all_events()
            vector_store.build_index(all_events)
            vector_store.save_index()
        logger.info("Index rebuilt.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()
    asyncio.run(enrich_events(limit=args.limit))
