"""One-shot script to sync text fields with database dates to avoid discrepancies."""

import re
import logging
from src.data.storage import EventStorage

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MONTHS_FR = [
    "janvier", "février", "mars", "avril", "mai", "juin", 
    "juillet", "août", "septembre", "octobre", "novembre", "décembre"
]
MONTHS_EN = [
    "january", "february", "march", "april", "may", "june",
    "july", "august", "september", "october", "november", "december"
]

def sync_event_text(event):
    if not event.start_date:
        return False
    
    dt = event.start_date
    day = dt.day
    month_fr = MONTHS_FR[dt.month - 1]
    month_en = MONTHS_EN[dt.month - 1]
    year = str(dt.year)
    
    # Replacement patterns
    # 1. Years (Replace any 2017-2025 with the DB year)
    year_pattern = r"\b20(1[7-9]|2[0-5])\b"
    
    # 2. Day + Month (e.g., "15 mai" or "mai 15")
    # This is a broad brush to catch most discrepancies
    month_pattern_fr = r"\b\d{1,2}\s+(" + "|".join(MONTHS_FR) + r")\b"
    month_pattern_en = r"\b(" + "|".join(MONTHS_EN) + r")\s+\d{1,2}\b"

    fields_to_fix = ['title', 'description', 'scraped_content']
    modified = False

    for field in fields_to_fix:
        val = getattr(event, field)
        if not val:
            continue
        
        orig = val
        # Fix Year
        val = re.sub(year_pattern, year, val)
        
        # Fix Day/Month mentions
        val = re.sub(month_pattern_fr, f"{day} {month_fr}", val, flags=re.IGNORECASE)
        val = re.sub(month_pattern_en, f"{month_en} {day}", val, flags=re.IGNORECASE)
        
        if val != orig:
            setattr(event, field, val)
            modified = True
            
    return modified

def run_sync():
    storage = EventStorage()
    events = storage.get_all_events()
    count = 0
    
    print(f"Syncing text for {len(events)} events...")
    
    for e in events:
        if sync_event_text(e):
            storage.update_event(e)
            count += 1
            
    print(f"Successfully synchronized {count} events with their database dates.")

if __name__ == "__main__":
    run_sync()
