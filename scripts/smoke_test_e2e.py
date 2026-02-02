"""
FILE: smoke_test_e2e.py
STATUS: Active
RESPONSIBILITY: Quick smoke test to verify API and UI are running after dependency updates.

DEPENDENCIES (Who uses this file):
- Developers: Run after dependency updates to verify services
- CI/CD: Quick health check before deployment

IMPORTS (What this file needs):
- httpx: HTTP requests
- sys: Exit codes

LAST MAJOR UPDATE: 2026-01-31 (v1.10.0 - dependency update verification)
MAINTAINER: QA Team
"""

import sys
import httpx
import time


def test_api_health():
    """Test that API is accessible."""
    print("Testing API health...")
    try:
        response = httpx.get("http://localhost:8000/docs", timeout=5)
        if response.status_code == 200:
            print("[OK] API is running on http://localhost:8000")
            return True
        else:
            print(f"[FAIL] API returned status {response.status_code}")
            return False
    except httpx.ConnectError:
        print("[FAIL] API not accessible on http://localhost:8000")
        return False


def test_streamlit_health():
    """Test that Streamlit UI is accessible."""
    print("Testing Streamlit health...")
    try:
        response = httpx.get("http://localhost:8501", timeout=10)
        if response.status_code == 200 and "streamlit" in response.text.lower():
            print("[OK] Streamlit is running on http://localhost:8501")
            return True
        else:
            print("[FAIL] Streamlit returned unexpected response")
            return False
    except httpx.ConnectError:
        print("[FAIL] Streamlit not accessible on http://localhost:8501")
        return False


def test_api_chat_endpoint():
    """Test that chat endpoint is functional."""
    print("Testing chat endpoint...")
    try:
        # This would require API key - just test the endpoint exists
        response = httpx.post(
            "http://localhost:8000/chat", json={"question": "test", "session_id": "smoke_test"}, timeout=5
        )
        # Will return 401/403 without API key, but that's fine - endpoint exists
        if response.status_code in [200, 401, 403, 422]:
            print(f"[OK] Chat endpoint accessible (status: {response.status_code})")
            return True
        else:
            print(f"[FAIL] Chat endpoint returned {response.status_code}")
            return False
    except Exception as e:
        print(f"[FAIL] Chat endpoint error: {e}")
        return False


def main():
    """Run all smoke tests."""
    print("=" * 60)
    print("SMOKE TEST: API + UI Health Check")
    print("=" * 60)
    print()

    results = []

    # Test API
    results.append(("API Health", test_api_health()))
    time.sleep(1)

    # Test Streamlit
    results.append(("Streamlit Health", test_streamlit_health()))
    time.sleep(1)

    # Test Chat Endpoint
    results.append(("Chat Endpoint", test_api_chat_endpoint()))

    print()
    print("=" * 60)
    print("RESULTS")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        symbol = "[OK]" if result else "[FAIL]"
        print(f"{symbol} {test_name}: {status}")

    print()
    print(f"Summary: {passed}/{total} tests passed")
    print("=" * 60)

    if passed == total:
        print("\n[OK] All smoke tests passed! Services are healthy.")
        return 0
    else:
        print(f"\n[FAIL] {total - passed} test(s) failed. Check services.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
