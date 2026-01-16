"""Script to visualize database content in a tabular format."""

import pandas as pd
from src.data.storage import EventStorage

def visualize_events(limit=5):
    storage = EventStorage()
    events = storage.get_all_events(limit=limit)
    
    data = []
    for e in events:
        data.append({
            "Title": e.title,
            "City": e.location.city if e.location else "N/A",
            "Category": e.category,
            "Date": e.start_date.strftime("%Y-%m-%d") if e.start_date else "N/A",
            "Scraped Preview": (e.scraped_content[:50] + "...") if e.scraped_content else "[EMPTY]",
            "URL": e.url[:30] + "..." if e.url else "N/A"
        })
    
    df = pd.DataFrame(data)
    
    # Adjust pandas display options
    pd.set_option('display.max_colwidth', 60)
    pd.set_option('display.width', 1000)
    
    print("\n--- DATABASE PREVIEW (Top 5 Events) ---\n")
    print(df.to_string(index=False))
    print("\n")

if __name__ == "__main__":
    visualize_events()