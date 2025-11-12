#!/bin/bash
# Smoke Test Script for GPT Integration Service
# Проверяет все критичные эндпоинты после слияния AI Chat

BASE_URL="${1:-http://localhost:9000}"
API_KEY="${API_SECRET_KEY}"

echo "🧪 Starting Smoke Test for GPT Integration Service"
echo "Base URL: $BASE_URL"
echo ""

TESTS_PASSED=0
TESTS_FAILED=0

test_endpoint() {
    local name="$1"
    local method="$2"
    local url="$3"
    local body="$4"
    
    echo -n "Testing: $name"
    
    if [ -z "$body" ]; then
        response=$(curl -s -w "\n%{http_code}" -X "$method" "$url" \
            -H "X-API-KEY: $API_KEY" \
            -H "Content-Type: application/json")
    else
        response=$(curl -s -w "\n%{http_code}" -X "$method" "$url" \
            -H "X-API-KEY: $API_KEY" \
            -H "Content-Type: application/json" \
            -d "$body")
    fi
    
    http_code=$(echo "$response" | tail -n1)
    
    if [ "$http_code" -ge 200 ] && [ "$http_code" -lt 300 ]; then
        echo " ✅ PASSED"
        ((TESTS_PASSED++))
        return 0
    else
        echo " ❌ FAILED (HTTP $http_code)"
        ((TESTS_FAILED++))
        return 1
    fi
}

# Test 1: Health Check
echo ""
echo "📋 General Endpoints"
test_endpoint "Health Check" "GET" "$BASE_URL/health"

# Test 2: AI Chat Endpoints
echo ""
echo "💬 AI Chat Endpoints"

test_endpoint "Get Chat Limits" "GET" "$BASE_URL/v1/chat/limits/123456789"

test_endpoint "Send Chat Message" "POST" "$BASE_URL/v1/chat/send" \
    '{"telegram_id": 123456789, "message": "Привет! Это тестовое сообщение."}'

test_endpoint "Get Chat History" "POST" "$BASE_URL/v1/chat/history" \
    '{"telegram_id": 123456789, "limit": 5, "offset": 0}'

test_endpoint "Get Chat Stats" "GET" "$BASE_URL/v1/chat/stats/123456789?days=7"

# Test 3: Analysis Endpoints
echo ""
echo "📊 Analysis Endpoints"

test_endpoint "Start Analysis" "POST" "$BASE_URL/v1/analysis/start" \
    '{"telegram_id": 123456789, "period": "7d", "validate_output": true}'

# Summary
echo ""
echo "=================================================="
echo "📊 Test Summary"
echo "=================================================="
echo "Passed: $TESTS_PASSED"
echo "Failed: $TESTS_FAILED"
echo "Total:  $((TESTS_PASSED + TESTS_FAILED))"

if [ $TESTS_FAILED -eq 0 ]; then
    echo ""
    echo "✅ All tests passed!"
    exit 0
else
    echo ""
    echo "❌ Some tests failed. Please check the logs."
    exit 1
fi
