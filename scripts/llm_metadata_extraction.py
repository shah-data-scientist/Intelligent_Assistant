"""LLM-based metadata extraction from scraped content with rate-limiting."""

import asyncio
import logging
import json
import time
import random
from typing import List

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_mistralai import ChatMistralAI

from src.data.storage import EventStorage
from src.data.models import Event
from src.config import settings

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger(__name__)

# Prompt for extraction
EXTRACTION_SYSTEM_PROMPT = """You are a strict data extraction assistant.
Your task is to extract specific metadata from the provided event description.

FIELDS TO EXTRACT:
1. "age_min" (integer or null): Minimum age recommended. Look for "dès X ans", "à partir de X ans".
2. "age_max" (integer or null): Maximum age if specified (rare).
3. "accessibility" (list of strings): Tags like "wheelchair" (fauteuil roulant), "sign_language" (LSF), "audio_description", "mental_disability". ONLY if explicitly mentioned.
4. "price_type" (string): "free" (gratuit, entrée libre), "paid" (payant, billetterie, tarifs), or "unknown".
5. "category" (string): Best fit from [Musique, Théâtre, Art, Sport, Enfant, Conférence, Autre].

STRICT RULES:
- ONLY extract information explicitly present in the text.
- If information is missing, return null (for integers) or "unknown" (for strings) or empty list.
- DO NOT GUESS. If no price is mentioned, it is "unknown", NOT "free".
- Return ONLY valid JSON.

Text to analyze:
{text}
"""

class MetadataExtractor:
    def __init__(self):
        self.llm = ChatMistralAI(
            model="mistral-small-latest",
            temperature=0.0, # Deterministic for extraction
            api_key=settings.mistral_api_key
        )
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", EXTRACTION_SYSTEM_PROMPT)
        ])
        self.chain = self.prompt | self.llm | JsonOutputParser()

    async def extract_metadata(self, text: str) -> dict:
        """Extract metadata from text using LLM with retry logic."""
        if not text or len(text) < 50:
            return {}
            
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Truncate text to avoid token limits
                truncated_text = text[:3000]
                result = await self.chain.ainvoke({"text": truncated_text})
                return result
            except Exception as e:
                err_msg = str(e).lower()
                if "429" in err_msg or "rate_limited" in err_msg:
                    wait_time = (2 ** attempt) + random.random() * 2
                    logger.warning(f"Rate limited. Waiting {wait_time:.2f}s before retry {attempt+1}...")
                    await asyncio.sleep(wait_time)
                    continue
                logger.warning(f"Extraction failed: {e}")
                return {}
        return {}

async def process_batch(events: List[Event], extractor: MetadataExtractor, storage: EventStorage):
    """Process a batch of events."""
    tasks = []
    events_to_update = []
    
    for event in events:
        # Use scraped_content if available, otherwise description
        content = event.scraped_content or event.description
        if content:
            tasks.append(extractor.extract_metadata(content))
            events_to_update.append(event)
    
    if not tasks:
        return 0

    results = await asyncio.gather(*tasks)
    updated_count = 0
    
    for event, meta in zip(events_to_update, results):
        if not meta: continue
        
        changed = False
        
        # Update Age
        if meta.get("age_min") is not None and isinstance(meta["age_min"], int):
            event.age_min = meta["age_min"]
            changed = True
        if meta.get("age_max") is not None and isinstance(meta["age_max"], int):
            event.age_max = meta["age_max"]
            changed = True
            
        # Update Accessibility
        if meta.get("accessibility") and isinstance(meta["accessibility"], list):
            acc_str = ", ".join(meta["accessibility"])
            if event.accessibility != acc_str:
                event.accessibility = acc_str
                changed = True
                
        # Update Price Conditions
        if meta.get("price_type") in ["free", "paid"]:
            # Only update if current is missing or very generic
            if not event.conditions or event.conditions in ["Gratuit", "Payant", "unknown"]:
                new_cond = "Gratuit" if meta["price_type"] == "free" else "Payant"
                if event.conditions != new_cond:
                    event.conditions = new_cond
                    changed = True
        
        # Update Category if explicit
        if meta.get("category") and meta["category"] != "Autre":
             # Only update if current is generic/unknown
             if not event.category or event.category in ["Vie associative", "Autre", "Loisirs"]:
                 event.category = meta["category"]
                 changed = True

        if changed:
            storage.update_event(event)
            updated_count += 1
            
    return updated_count

async def main(limit=None):
    storage = EventStorage()
    extractor = MetadataExtractor()
    
    logger.info("Fetching events...")
    events = storage.get_all_events()
    
    # Filter targets: have scraped content but missing age OR price
    targets = [
        e for e in events 
        if e.scraped_content and (e.age_min is None or not e.conditions or e.conditions == "unknown")
    ]
    
    if limit:
        targets = targets[:limit]
        
    logger.info(f"Targeting {len(targets)} events for metadata optimization.")
    
    if not targets:
        logger.info("All events already optimized.")
        return

    BATCH_SIZE = 5  # Smaller batches for stability
    total_updated = 0
    
    for i in range(0, len(targets), BATCH_SIZE):
        batch = targets[i:i+BATCH_SIZE]
        logger.info(f"Processing batch {i} to {i+len(batch)}...")
        count = await process_batch(batch, extractor, storage)
        total_updated += count
        
        # Mandatory delay between batches to respect rate limits
        await asyncio.sleep(2.0)
        
    logger.info(f"Optimization complete. Updated {total_updated} events.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()
    
    asyncio.run(main(limit=args.limit))
