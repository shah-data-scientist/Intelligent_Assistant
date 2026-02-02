"""Quick Gemini API test using new google.genai SDK."""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from google import genai

api_key = os.getenv('GOOGLE_API_KEY')
if not api_key:
    print("ERROR: No GOOGLE_API_KEY found")
    sys.exit(1)

print(f"API Key: {api_key[:15]}...")
client = genai.Client(api_key=api_key)
print("Calling Gemini API...")

try:
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents="Say OK"
    )
    print(f"SUCCESS: {response.text}")
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")
