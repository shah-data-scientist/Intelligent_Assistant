"""Check API latency for cold start vs warm request."""

import requests
import time

URL = "http://localhost:8000/api/v1/chat"
PAYLOAD = {"question": "Are there any jazz concerts in Paris?"}

def time_request(label):
    print(f"\n--- {label} ---")
    start = time.time()
    try:
        response = requests.post(URL, json=PAYLOAD)
        duration = time.time() - start
        
        if response.status_code == 200:
            print(f"Status: {response.status_code}")
            print(f"Time: {duration:.2f} seconds")
        else:
            print(f"Failed: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    # 1. First Request (Cold Start?)
    time_request("Request 1 (Potential Cold Start)")
    
    # 2. Second Request (Warm)
    time_request("Request 2 (Warm)")

