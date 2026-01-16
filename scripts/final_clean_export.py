"""Final cleaned export of 100 refined records."""

import pandas as pd
import os
import re
import json
from src.data.storage import EventStorage
from unicodedata import category as unicodedata_category

def clean_value(val):
    """Deep clean a value: remove JSON artifacts, HTML, and illegal XML chars."""
    if val is None:
        return ""
    
    # If it's a list or dict, join it
    if isinstance(val, (list, dict)):
        return str(val)
    
    s_val = str(val).strip()
    
    # If it looks like a JSON array/object string, try to parse and flatten it
    if (s_val.startswith('[') and s_val.endswith(']')) or (s_val.startswith('{') and s_val.endswith('}')):
        try:
            parsed = json.loads(s_val)
            if isinstance(parsed, list):
                s_val = ", ".join(str(x) for x in parsed)
            elif isinstance(parsed, dict):
                s_val = ", ".join([f"{k}: {v}" for k, v in parsed.items()])
        except:
            pass

    # Strip HTML
    s_val = re.sub(r'<[^>]*>', '', s_val)
    
    # Remove illegal XML characters
    return "".join(ch for ch in s_val if unicodedata_category(ch)[0] != "C" or ch in "\t\n\r")

def export_final_table(limit=100, output_file="data/REFINED_TABLE_100.xlsx"):
    storage = EventStorage()
    # Get events that have been fully processed
    all_events = storage.get_all_events(limit=500)
    
    # Prioritize those with rich content
    events = [e for e in all_events if e.scraped_content and len(e.scraped_content) > 500][:limit]
    if len(events) < limit:
        events = all_events[:limit]

    data = []
    for e in events:
        data.append({
            "EVENT_NAME": clean_value(e.title),
            "CATEGORY": clean_value(e.category),
            "CITY": clean_value(e.location.city if e.location else ""),
            "DATE": e.start_date.strftime("%Y-%m-%d") if e.start_date else "",
            "ORGANIZER": clean_value(e.organizer),
            "PRICE_CONDITIONS": clean_value(e.conditions),
            "ACCESSIBILITY": clean_value(e.accessibility),
            "AGE_RANGE": f"{e.age_min or 'All'} - {e.age_max or 'All'}",
            "DESCRIPTION_CLEAN": clean_value(e.description),
            "FULL_CONTENT_CLEAN": clean_value(e.scraped_content),
            "URL": e.url
        })
    
    df = pd.DataFrame(data)
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    df.to_excel(output_file, index=False)
    print(f"\nSUCCESS: Exported to {output_file}")
    print(f"Please open THIS SPECIFIC FILE to see the refined tabular data.\n")

if __name__ == "__main__":
    export_final_table()
