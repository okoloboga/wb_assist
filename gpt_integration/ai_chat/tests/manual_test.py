"""
Manual testing script for AI Chat Service.

Tests basic functionality by making HTTP requests to running service.

Usage:
    # Start service first:
    python -m ai_chat.service
    
    # Then run tests:
    python ai_chat/tests/manual_test.py
"""

import os
import requests
from datetime import datetime


# Configuration
AI_CHAT_URL = os.getenv("AI_CHAT_SERVICE_URL", "http://localhost:9001")
API_SECRET_KEY = os.getenv("API_SECRET_KEY", "test-api-key")

# Test user
TEST_TELEGRAM_ID = 999888777


def print_test(name):
    """Print test name."""
    print(f"\n{'='*60}")
    print(f"🧪 TEST: {name}")
    print(f"{'='*60}")


def print_result(response, show_body=True):
    """Print response result."""
    status_emoji = "✅" if response.status_code < 400 else "❌"
    print(f"{status_emoji} Status: {response.status_code}")
    
    if show_body:
        try:
            data = response.json()
            print(f"Response: {data}")
        except:
            print(f"Response: {response.text}")


def test_health_check():
    """Test health endpoint."""
    print_test("Health Check")
    
    response = requests.get(f"{AI_CHAT_URL}/health")
    print_result(response)
    
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    print("✅ Health check passed")


def test_get_limits():
    """Test getting user limits."""
    print_test("Get Limits")
    
    headers = {"X-API-KEY": API_SECRET_KEY}
    response = requests.get(
        f"{AI_CHAT_URL}/v1/chat/limits/{TEST_TELEGRAM_ID}",
        headers=headers
    )
    print_result(response)
    
    assert response.status_code == 200
    data = response.json()
    assert "requests_today" in data
    assert "requests_remaining" in data
    print(f"✅ Limits: {data['requests_today']}/30 used, {data['requests_remaining']} remaining")


def test_send_message():
    """Test sending a message to AI."""
    print_test("Send Message to AI")
    
    headers = {
        "X-API-KEY": API_SECRET_KEY,
        "Content-Type": "application/json"
    }
    
    payload = {
        "telegram_id": TEST_TELEGRAM_ID,
        "message": "Привет! Расскажи кратко о Wildberries в двух предложениях."
    }
    
    print(f"📤 Sending: {payload['message']}")
    
    response = requests.post(
        f"{AI_CHAT_URL}/v1/chat/send",
        headers=headers,
        json=payload,
        timeout=60
    )
    print_result(response)
    
    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert "remaining_requests" in data
    
    print(f"\n🤖 AI Response:\n{data['response']}")
    print(f"\n📊 Tokens used: {data['tokens_used']}")
    print(f"📊 Remaining requests: {data['remaining_requests']}")


def test_get_history():
    """Test getting chat history."""
    print_test("Get Chat History")
    
    headers = {
        "X-API-KEY": API_SECRET_KEY,
        "Content-Type": "application/json"
    }
    
    payload = {
        "telegram_id": TEST_TELEGRAM_ID,
        "limit": 5,
        "offset": 0
    }
    
    response = requests.post(
        f"{AI_CHAT_URL}/v1/chat/history",
        headers=headers,
        json=payload
    )
    print_result(response, show_body=False)
    
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    
    print(f"📜 Total messages: {data['total']}")
    print(f"📜 Returned: {len(data['items'])}")
    
    if data['items']:
        print("\nLast message:")
        last_msg = data['items'][0]
        print(f"  User: {last_msg['message'][:50]}...")
        print(f"  AI: {last_msg['response'][:50]}...")


def test_get_stats():
    """Test getting user statistics."""
    print_test("Get User Statistics")
    
    headers = {"X-API-KEY": API_SECRET_KEY}
    
    response = requests.get(
        f"{AI_CHAT_URL}/v1/chat/stats/{TEST_TELEGRAM_ID}",
        headers=headers,
        params={"days": 7}
    )
    print_result(response)
    
    assert response.status_code == 200
    data = response.json()
    
    print(f"📊 Total requests (7 days): {data['total_requests']}")
    print(f"📊 Total tokens: {data['total_tokens']}")
    print(f"📊 Avg requests/day: {data['avg_requests_per_day']}")
    print(f"📊 Avg tokens/request: {data['avg_tokens_per_request']}")


def test_invalid_api_key():
    """Test with invalid API key."""
    print_test("Invalid API Key (should fail)")
    
    headers = {"X-API-KEY": "wrong-key"}
    
    response = requests.get(
        f"{AI_CHAT_URL}/v1/chat/limits/{TEST_TELEGRAM_ID}",
        headers=headers
    )
    print_result(response)
    
    assert response.status_code == 403
    print("✅ Correctly rejected invalid API key")


def test_missing_api_key():
    """Test without API key."""
    print_test("Missing API Key (should fail)")
    
    response = requests.get(
        f"{AI_CHAT_URL}/v1/chat/limits/{TEST_TELEGRAM_ID}"
    )
    print_result(response)
    
    assert response.status_code == 403
    print("✅ Correctly rejected missing API key")


def main():
    """Run all manual tests."""
    print(f"\n🚀 AI Chat Service Manual Tests")
    print(f"URL: {AI_CHAT_URL}")
    print(f"Time: {datetime.now()}")
    
    tests = [
        test_health_check,
        test_invalid_api_key,
        test_missing_api_key,
        test_get_limits,
        test_send_message,
        test_get_history,
        test_get_stats,
    ]
    
    passed = 0
    failed = 0
    
    for test_func in tests:
        try:
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"❌ TEST FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"❌ ERROR: {e}")
            failed += 1
    
    print(f"\n{'='*60}")
    print(f"📊 RESULTS: {passed} passed, {failed} failed")
    print(f"{'='*60}\n")
    
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())

