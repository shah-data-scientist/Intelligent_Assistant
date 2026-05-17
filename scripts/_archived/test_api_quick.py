"""
FILE: test_api_quick.py
STATUS: Active
RESPONSIBILITY: Quick API endpoint test script for development validation.
DEPENDENCIES: None (standalone script)
IMPORTS: requests
LAST MAJOR UPDATE: 2026-02-02
MAINTAINER: Development Team
"""

import requests

API_URL = "http://localhost:8001/api/v1"
API_KEY = "dev-secret-key"  # pragma: allowlist secret


def test_chat():
    """Test chat endpoint."""
    headers = {"Content-Type": "application/json", "X-API-Key": API_KEY}
    payload = {"question": "Jazz concerts in Paris", "session_id": "quick_test_001"}

    print("Testing chat endpoint...")
    try:
        resp = requests.post(f"{API_URL}/chat", headers=headers, json=payload, timeout=120)
        print(f"Status: {resp.status_code}")

        if resp.status_code == 200:
            data = resp.json()
            answer = data.get("answer", "")[:800]
            events_count = len(data.get("sources", []))
            print(f"Events: {events_count}")
            print(f"Answer preview:\n{answer}")
        else:
            print(f"Error: {resp.text[:500]}")

    except requests.exceptions.Timeout:
        print("Request timed out after 120 seconds")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    test_chat()
