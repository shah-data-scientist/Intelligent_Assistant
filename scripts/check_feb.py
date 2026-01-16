from src.data.storage import EventStorage
from datetime import datetime

def check_feb_events():
    storage = EventStorage()
    start = datetime(2026, 2, 1)
    end = datetime(2026, 2, 28)
    events = storage.get_events_by_date_range(start_date=start, end_date=end)
    
    print(f"Total events found in February 2026: {len(events)}")
    for i, e in enumerate(events, 1):
        print(f"{i}. [{e.category}] {e.title} - {e.start_date.strftime('%Y-%m-%d')}")
        if i >= 20: # Show top 20
            break

if __name__ == "__main__":
    check_feb_events()
