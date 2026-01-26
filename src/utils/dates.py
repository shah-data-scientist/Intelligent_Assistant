"""Date parsing utilities for natural language queries."""

import datetime
from typing import Optional, Tuple, Dict, Any

def parse_natural_date(query: str) -> Dict[str, Any]:
    """Parse natural language date expressions into filter criteria."""
    today = datetime.date.today()
    query = query.lower()
    filters = {}

    # "This Weekend"
    # Logic: Next Saturday/Sunday. If today is Sunday, it means today.
    if "this weekend" in query or "ce week-end" in query or "ce weekend" in query or "weekend" in query or "week-end" in query:
        # Find next Saturday (5)
        # If today is Thu (3), days_until_sat = 2
        days_until_sat = (5 - today.weekday()) % 7
        
        # If today is Saturday or Sunday, we might be asking for THIS one or the NEXT one.
        # Usually "this weekend" on a Sunday means "today".
        
        next_saturday = today + datetime.timedelta(days=days_until_sat)
        next_sunday = next_saturday + datetime.timedelta(days=1)
        
        filters["date_min"] = next_saturday
        filters["date_max"] = next_sunday
        return filters

    # "Next Weekend"
    if "next weekend" in query or "prochain week-end" in query:
        # Find Saturday of next week
        days_until_sat = (5 - today.weekday()) % 7
        next_saturday = today + datetime.timedelta(days=days_until_sat + 7)
        next_sunday = next_saturday + datetime.timedelta(days=1)
        
        filters["date_min"] = next_saturday
        filters["date_max"] = next_sunday
        return filters

    # "This Week"
    if "this week" in query or "cette semaine" in query:
        # Until next Sunday
        days_until_sun = (6 - today.weekday()) % 7
        next_sunday = today + datetime.timedelta(days=days_until_sun)
        
        filters["date_min"] = today
        filters["date_max"] = next_sunday
        return filters

    return filters
