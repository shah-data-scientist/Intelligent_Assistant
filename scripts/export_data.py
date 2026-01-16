"""Script to export event data to Excel."""

import pandas as pd
import os
from src.data.storage import EventStorage

def export_events_to_excel(limit=5, output_file="data/events_export_v3.xlsx"):
    storage = EventStorage()
    # Fetch more events to ensure we find some with scraped content
    all_events = storage.get_all_events(limit=100)
    
    # Filter for events that actually have scraped content
    events = [e for e in all_events if e.scraped_content][:limit]
    
    if not events:
        print("Warning: No events with scraped content found in the first 100.")
        events = all_events[:limit]

    data = []
    for e in events:
        # Base fields from Event model
        row = {
            "ID": e.event_id,
            "Title": e.title,
            "Description": e.description,
            "Category": e.category,
            "City": e.location.city if e.location else None,
            "Address": e.location.address if e.location else None,
            "Postal Code": e.location.postal_code if e.location else None,
            "Latitude": e.location.coordinates.get("lat") if e.location and e.location.coordinates else None,
            "Longitude": e.location.coordinates.get("lon") if e.location and e.location.coordinates else None,
            "Start Date": e.start_date.isoformat() if e.start_date else None,
            "End Date": e.end_date.isoformat() if e.end_date else None,
            "Organizer": e.organizer,
            "URL": e.url,
            "Scraped Content": e.scraped_content,
            "Image URL": e.image_url,
            "Tags": ", ".join(e.tags) if e.tags else ""
        }
        
        # Flatten specific useful fields from raw_data if available
        if e.raw_data:
            row["Accessibility"] = e.raw_data.get("accessibility_label_fr") or e.raw_data.get("accessibility")
            row["Age Min"] = e.raw_data.get("age_min")
            row["Age Max"] = e.raw_data.get("age_max")
            row["Conditions"] = e.raw_data.get("conditions_fr") or e.raw_data.get("conditions")
            row["Registration"] = str(e.raw_data.get("registration")) if e.raw_data.get("registration") else None
            # Add any other specific raw fields you might want here
            
        data.append(row)
    
    df = pd.DataFrame(data)
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    df.to_excel(output_file, index=False)
    print(f"Successfully exported {len(events)} events to {output_file}")

if __name__ == "__main__":
    export_events_to_excel()
