"""
Integration tests for API endpoints.
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import date


class TestHealthEndpoint:
    """Tests for /health endpoint."""
    
    def test_health_check(self, client):
        """Health check should return OK without authentication."""
        response = client.get("/health")
        
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
        assert response.json()["service"] == "ai_chat"
        assert response.json()["version"] == "1.0.0"


class TestChatSendEndpoint:
    """Tests for POST /v1/chat/send endpoint."""
    
    @patch("ai_chat.app.service._call_openai")
    def test_send_message_success(self, mock_openai, client, headers, sample_telegram_id):
        """Should successfully send message and get AI response."""
        mock_openai.return_value = ("Это тестовый ответ", 100)
        
        payload = {
            "telegram_id": sample_telegram_id,
            "message": "Как увеличить продажи?"
        }
        
        response = client.post("/v1/chat/send", json=payload, headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        assert "remaining_requests" in data
        assert "tokens_used" in data
        assert data["tokens_used"] == 100
    
    def test_send_message_without_api_key(self, client, sample_telegram_id):
        """Should reject request without API key."""
        payload = {
            "telegram_id": sample_telegram_id,
            "message": "Test message"
        }
        
        response = client.post("/v1/chat/send", json=payload)
        
        assert response.status_code == 403
    
    def test_send_message_invalid_api_key(self, client, sample_telegram_id):
        """Should reject request with invalid API key."""
        payload = {
            "telegram_id": sample_telegram_id,
            "message": "Test message"
        }
        headers = {"X-API-KEY": "wrong-key"}
        
        response = client.post("/v1/chat/send", json=payload, headers=headers)
        
        assert response.status_code == 403
    
    def test_send_message_validation_error(self, client, headers):
        """Should validate request payload."""
        # Missing telegram_id
        payload = {"message": "Test"}
        
        response = client.post("/v1/chat/send", json=payload, headers=headers)
        
        assert response.status_code == 422
    
    def test_send_message_empty_text(self, client, headers, sample_telegram_id):
        """Should reject empty message."""
        payload = {
            "telegram_id": sample_telegram_id,
            "message": ""
        }
        
        response = client.post("/v1/chat/send", json=payload, headers=headers)
        
        assert response.status_code == 422
    
    def test_send_message_too_long(self, client, headers, sample_telegram_id):
        """Should reject message that's too long."""
        payload = {
            "telegram_id": sample_telegram_id,
            "message": "a" * 5000  # More than 4000 chars
        }
        
        response = client.post("/v1/chat/send", json=payload, headers=headers)
        
        assert response.status_code == 422


class TestChatHistoryEndpoint:
    """Tests for POST /v1/chat/history endpoint."""
    
    def test_get_history_empty(self, client, headers, sample_telegram_id):
        """Should return empty history for new user."""
        payload = {
            "telegram_id": sample_telegram_id,
            "limit": 10,
            "offset": 0
        }
        
        response = client.post("/v1/chat/history", json=payload, headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0
        assert data["limit"] == 10
        assert data["offset"] == 0
    
    def test_get_history_with_records(self, client, headers, create_chat_history):
        """Should return chat history."""
        create_chat_history(5)
        
        payload = {
            "telegram_id": 123456789,
            "limit": 10,
            "offset": 0
        }
        
        response = client.post("/v1/chat/history", json=payload, headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 5
        assert data["total"] == 5
    
    def test_get_history_pagination(self, client, headers, create_chat_history):
        """Should support pagination."""
        create_chat_history(15)
        
        # First page
        payload1 = {
            "telegram_id": 123456789,
            "limit": 5,
            "offset": 0
        }
        response1 = client.post("/v1/chat/history", json=payload1, headers=headers)
        
        # Second page
        payload2 = {
            "telegram_id": 123456789,
            "limit": 5,
            "offset": 5
        }
        response2 = client.post("/v1/chat/history", json=payload2, headers=headers)
        
        assert response1.status_code == 200
        assert response2.status_code == 200
        
        data1 = response1.json()
        data2 = response2.json()
        
        assert len(data1["items"]) == 5
        assert len(data2["items"]) == 5
        assert data1["total"] == 15
        assert data2["total"] == 15
    
    def test_get_history_without_api_key(self, client, sample_telegram_id):
        """Should reject request without API key."""
        payload = {
            "telegram_id": sample_telegram_id,
            "limit": 10
        }
        
        response = client.post("/v1/chat/history", json=payload)
        
        assert response.status_code == 403


class TestChatLimitsEndpoint:
    """Tests for GET /v1/chat/limits/{telegram_id} endpoint."""
    
    def test_get_limits_new_user(self, client, headers, sample_telegram_id):
        """Should return default limits for new user."""
        response = client.get(
            f"/v1/chat/limits/{sample_telegram_id}",
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["telegram_id"] == sample_telegram_id
        assert data["requests_today"] == 0
        assert data["requests_remaining"] == 30
        assert data["daily_limit"] == 30
    
    def test_get_limits_existing_user(self, client, headers, sample_daily_limit):
        """Should return current limits for existing user."""
        telegram_id = sample_daily_limit.telegram_id
        
        response = client.get(
            f"/v1/chat/limits/{telegram_id}",
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["telegram_id"] == telegram_id
        assert data["requests_today"] == 5
        assert data["requests_remaining"] == 25
    
    def test_get_limits_without_api_key(self, client, sample_telegram_id):
        """Should reject request without API key."""
        response = client.get(f"/v1/chat/limits/{sample_telegram_id}")
        
        assert response.status_code == 403


class TestResetLimitEndpoint:
    """Tests for POST /v1/chat/reset-limit endpoint."""
    
    def test_reset_limit_success(self, client, headers, sample_daily_limit):
        """Should reset user's limit."""
        telegram_id = sample_daily_limit.telegram_id
        
        payload = {"telegram_id": telegram_id}
        response = client.post("/v1/chat/reset-limit", json=payload, headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "успешно" in data["message"].lower()
    
    def test_reset_limit_nonexistent_user(self, client, headers):
        """Should return failure for non-existent user."""
        payload = {"telegram_id": 999999999}
        response = client.post("/v1/chat/reset-limit", json=payload, headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "не найден" in data["message"].lower()
    
    def test_reset_limit_without_api_key(self, client):
        """Should reject request without API key."""
        payload = {"telegram_id": 123456789}
        response = client.post("/v1/chat/reset-limit", json=payload)
        
        assert response.status_code == 403


class TestStatsEndpoint:
    """Tests for GET /v1/chat/stats/{telegram_id} endpoint."""
    
    def test_get_stats_empty(self, client, headers, sample_telegram_id):
        """Should return zero stats for user with no history."""
        response = client.get(
            f"/v1/chat/stats/{sample_telegram_id}",
            headers=headers,
            params={"days": 7}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["telegram_id"] == sample_telegram_id
        assert data["total_requests"] == 0
        assert data["total_tokens"] == 0
        assert data["days"] == 7
    
    def test_get_stats_with_history(self, client, headers, create_chat_history):
        """Should calculate correct statistics."""
        create_chat_history(10)
        
        response = client.get(
            "/v1/chat/stats/123456789",
            headers=headers,
            params={"days": 7}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_requests"] == 10
        assert data["total_tokens"] > 0
        assert data["avg_requests_per_day"] > 0
    
    def test_get_stats_invalid_days(self, client, headers, sample_telegram_id):
        """Should reject invalid days parameter."""
        response = client.get(
            f"/v1/chat/stats/{sample_telegram_id}",
            headers=headers,
            params={"days": 500}  # More than 365
        )
        
        assert response.status_code == 400
    
    def test_get_stats_without_api_key(self, client, sample_telegram_id):
        """Should reject request without API key."""
        response = client.get(f"/v1/chat/stats/{sample_telegram_id}")
        
        assert response.status_code == 403

