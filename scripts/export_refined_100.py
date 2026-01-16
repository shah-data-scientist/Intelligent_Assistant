"""Export 100 refined records for quality verification."""

import pandas as pd
import os
import re
from src.data.storage import EventStorage

def sanitize_text(text):
    """Remove illegal characters and HTML tags for Excel safety."""
    if not text:
        return ""
    # Strip HTML tags
    text = re.sub(r'<[^>]*>', '', str(text))
    # Remove characters that are illegal in XML/Excel
    return "".join(ch for i, ch in enumerate(text) if unicodedata_category(ch)[0] != "C" or ch in "\t\n\r")

# We need this for sanitize_text
from unicodedata import category as unicodedata_category

def export_refined_data(limit=100, output_file="data/refined_events_100.xlsx"):
    storage = EventStorage()
    all_events = storage.get_all_events(limit=500)
    events = [e for e in all_events if e.scraped_content and len(e.scraped_content) > 500][:limit]
    
    if len(events) < limit:
        events = all_events[:limit]

    data = []
    for e in events:
        row = {
            "Event_ID": e.event_id,
            "Title": sanitize_text(e.title),
            "Category": e.category,
            "City": e.location.city if e.location else None,
            "Start_Date": e.start_date.strftime("%Y-%m-%d") if e.start_date else None,
            "Organizer": sanitize_text(e.organizer),
            "Conditions_Tarifs": sanitize_text(e.conditions),
            "Accessibility": sanitize_text(e.accessibility),
            "Age_Min": e.age_min,
            "Age_Max": e.age_max,
            "Short_Description": sanitize_text(e.description),
            "Full_Scraped_Content": sanitize_text(e.scraped_content),
            "URL": e.url,
            "Vector_Ready_Text": sanitize_text(e.to_text())
        }
        data.append(row)
    
    df = pd.DataFrame(data)
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    df.to_excel(output_file, index=False)
    print(f"Successfully exported {len(events)} refined records to {output_file}")

if __name__ == "__main__":
    export_refined_data()
