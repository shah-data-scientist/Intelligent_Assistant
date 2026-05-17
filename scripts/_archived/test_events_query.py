"""
FILE: test_events_query.py
STATUS: Active
RESPONSIBILITY: Test script for validating events query handling.
DEPENDENCIES: None (standalone script)
IMPORTS: requests
LAST MAJOR UPDATE: 2026-02-02
MAINTAINER: Development Team
"""

import requests

API_URL = "http://localhost:8001/api/v1"
API_KEY = "dev-secret-key"  # pragma: allowlist secret


def test_events_query():
    """Test the problematic 'events' query."""
    headers = {"Content-Type": "application/json", "X-API-Key": API_KEY}
    payload = {"question": "events", "session_id": "test_events_001"}

    print("Testing 'events' query...")
    try:
        resp = requests.post(f"{API_URL}/chat", headers=headers, json=payload, timeout=120)
        print(f"Status: {resp.status_code}")

        if resp.status_code == 200:
            data = resp.json()
            answer = data.get("answer", "")[:500]
            events_count = len(data.get("structured_events", []))
            sources_count = len(data.get("sources", []))
            print(f"Structured Events: {events_count}")
            print(f"Sources: {sources_count}")
            print(f"Answer preview:\n{answer}")
        else:
            print(f"Error: {resp.text[:500]}")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    test_events_query()
