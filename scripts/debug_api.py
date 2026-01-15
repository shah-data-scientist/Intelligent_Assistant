"""Debug script to reproduce API 422 errors."""

import requests
import json

URL = "http://localhost:8000/api/v1/chat"

def test_request(name, payload, headers=None):
    print(f"\n--- Testing: {name} ---")
    print(f"Payload: {payload}")
    try:
        if headers:
            response = requests.post(URL, data=payload, headers=headers)
        else:
            response = requests.post(URL, json=payload)
            
        print(f"Status: {response.status_code}")
        if response.status_code == 422:
            print(f"Error Detail: {json.dumps(response.json(), indent=2)}")
        else:
            print("Success!")
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    # 1. Correct Request
    test_request("Correct Request", {"question": "HI, hiw are you ?"})

    # 2. Wrong Key (Common mistake)
    test_request("Wrong Key ('text' instead of 'question')", {"text": "HI, hiw are you ?"})

    # 3. Plain Text (Not JSON)
    test_request("Plain Text Body", "HI, hiw are you ?", headers={"Content-Type": "text/plain"})
