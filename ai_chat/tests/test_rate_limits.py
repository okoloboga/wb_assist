"""
Tests for rate limiting functionality.
"""

import pytest
from unittest.mock import patch
from datetime import date, timedelta
from ai_chat.app.crud import AIChatCRUD, DAILY_LIMIT
from ai_chat.app.models import AIChatDailyLimit


class TestRateLimiting:
    """Tests for rate limiting (30 requests per day)."""
    
    @patch("ai_chat.app.service._call_openai")
    def test_rate_limit_tracking(self, mock_openai, client, headers, sample_telegram_id):
        """Should track request count correctly."""
        mock_openai.return_value = ("Test response", 50)
        
        payload = {
            "telegram_id": sample_telegram_id,
            "message": "Test message"
        }
        
        # Make 5 requests
        for i in range(5):
            response = client.post("/v1/chat/send", json=payload, headers=headers)
            assert response.status_code == 200
            data = response.json()
            assert data["remaining_requests"] == DAILY_LIMIT - (i + 1)
    
    @patch("ai_chat.app.service._call_openai")
    def test_rate_limit_exceeded(self, mock_openai, client, headers, test_db_session, sample_telegram_id):
        """Should reject requests after limit exceeded."""
        mock_openai.return_value = ("Test response", 50)
        
        # Set limit to maximum - 1
        limit = AIChatDailyLimit(
            telegram_id=sample_telegram_id,
            request_count=DAILY_LIMIT - 1,
            last_reset_date=date.today()
        )
        test_db_session.add(limit)
        test_db_session.commit()
        
        payload = {
            "telegram_id": sample_telegram_id,
            "message": "Test message"
        }
        
        # This should succeed (last allowed request)
        response1 = client.post("/v1/chat/send", json=payload, headers=headers)
        assert response1.status_code == 200
        assert response1.json()["remaining_requests"] == 0
        
        # This should fail (limit exceeded)
        response2 = client.post("/v1/chat/send", json=payload, headers=headers)
        assert response2.status_code == 429
        assert "detail" in response2.json()
    
    def test_rate_limit_reset_on_new_day(self, test_db_session, sample_telegram_id):
        """Should reset limit when it's a new day."""
        crud = AIChatCRUD(test_db_session)
        
        # Create limit from yesterday at maximum
        yesterday = date.today() - timedelta(days=1)
        limit = AIChatDailyLimit(
            telegram_id=sample_telegram_id,
            request_count=DAILY_LIMIT,
            last_reset_date=yesterday
        )
        test_db_session.add(limit)
        test_db_session.commit()
        
        # Check limit should reset and allow request
        can_request, remaining = crud.check_and_update_limit(sample_telegram_id)
        
        assert can_request is True
        assert remaining == DAILY_LIMIT - 1
        
        # Verify limit was reset in database
        test_db_session.refresh(limit)
        assert limit.request_count == 1
        assert limit.last_reset_date == date.today()
    
    def test_get_limits_does_not_count(self, client, headers, test_db_session, sample_telegram_id):
        """Getting limits should NOT count as a request."""
        # Set initial count
        limit = AIChatDailyLimit(
            telegram_id=sample_telegram_id,
            request_count=10,
            last_reset_date=date.today()
        )
        test_db_session.add(limit)
        test_db_session.commit()
        
        # Get limits multiple times
        for _ in range(5):
            response = client.get(
                f"/v1/chat/limits/{sample_telegram_id}",
                headers=headers
            )
            assert response.status_code == 200
        
        # Counter should NOT have changed
        test_db_session.refresh(limit)
        assert limit.request_count == 10
    
    @patch("ai_chat.app.service._call_openai")
    def test_rate_limit_per_user(self, mock_openai, client, headers):
        """Rate limits should be tracked per user."""
        mock_openai.return_value = ("Test response", 50)
        
        user1 = 111111
        user2 = 222222
        
        # User 1 makes 5 requests
        payload1 = {"telegram_id": user1, "message": "Test"}
        for _ in range(5):
            response = client.post("/v1/chat/send", json=payload1, headers=headers)
            assert response.status_code == 200
        
        # User 2 should still have full limit
        payload2 = {"telegram_id": user2, "message": "Test"}
        response = client.post("/v1/chat/send", json=payload2, headers=headers)
        assert response.status_code == 200
        assert response.json()["remaining_requests"] == DAILY_LIMIT - 1


class TestAdminResetLimit:
    """Tests for admin limit reset functionality."""
    
    def test_admin_reset_restores_full_limit(self, client, headers, test_db_session, sample_telegram_id):
        """Admin reset should restore full limit."""
        # User exhausts limit
        limit = AIChatDailyLimit(
            telegram_id=sample_telegram_id,
            request_count=DAILY_LIMIT,
            last_reset_date=date.today()
        )
        test_db_session.add(limit)
        test_db_session.commit()
        
        # Admin resets limit
        reset_payload = {"telegram_id": sample_telegram_id}
        reset_response = client.post("/v1/chat/reset-limit", json=reset_payload, headers=headers)
        assert reset_response.status_code == 200
        assert reset_response.json()["success"] is True
        
        # Check limit is restored
        limits_response = client.get(
            f"/v1/chat/limits/{sample_telegram_id}",
            headers=headers
        )
        assert limits_response.status_code == 200
        data = limits_response.json()
        assert data["requests_today"] == 0
        assert data["requests_remaining"] == DAILY_LIMIT


class TestContextTracking:
    """Tests for chat context tracking."""
    
    @patch("ai_chat.app.service._call_openai")
    def test_context_includes_previous_messages(self, mock_openai, client, headers, test_db_session, sample_telegram_id):
        """AI calls should include context from previous messages."""
        mock_openai.return_value = ("Test response", 50)
        
        payload = {
            "telegram_id": sample_telegram_id,
            "message": "Test message"
        }
        
        # Make first request
        response1 = client.post("/v1/chat/send", json=payload, headers=headers)
        assert response1.status_code == 200
        
        # Make second request
        response2 = client.post("/v1/chat/send", json=payload, headers=headers)
        assert response2.status_code == 200
        
        # Check that OpenAI was called with context
        # Second call should have more messages (system + context from first + new message)
        calls = mock_openai.call_args_list
        assert len(calls) == 2
        
        # First call: system prompt + user message
        first_call_messages = calls[0][0][0]
        assert len(first_call_messages) >= 2
        
        # Second call: system prompt + context + user message
        second_call_messages = calls[1][0][0]
        assert len(second_call_messages) > len(first_call_messages)
    
    def test_context_limit(self, test_db_session, create_chat_history):
        """Context should be limited to last N messages."""
        from ai_chat.app.crud import AIChatCRUD
        
        # Create 10 messages
        create_chat_history(10)
        
        crud = AIChatCRUD(test_db_session)
        context = crud.get_recent_context(123456789, limit=3)
        
        # Should return only 3 messages (6 with user + assistant)
        assert len(context) == 6

