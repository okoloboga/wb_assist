"""
Unit tests for CRUD operations.
"""

import pytest
from datetime import date, timedelta
from ai_chat.app.crud import AIChatCRUD, DAILY_LIMIT
from ai_chat.app.models import AIChatRequest, AIChatDailyLimit


class TestCheckAndUpdateLimit:
    """Tests for check_and_update_limit method."""
    
    def test_new_user_creates_record(self, test_db_session, sample_telegram_id):
        """New user should get a limit record created."""
        crud = AIChatCRUD(test_db_session)
        
        can_request, remaining = crud.check_and_update_limit(sample_telegram_id)
        
        assert can_request is True
        assert remaining == DAILY_LIMIT - 1
        
        # Verify record was created
        record = test_db_session.query(AIChatDailyLimit).filter(
            AIChatDailyLimit.telegram_id == sample_telegram_id
        ).first()
        assert record is not None
        assert record.request_count == 1
        assert record.last_reset_date == date.today()
    
    def test_increment_counter(self, test_db_session, sample_daily_limit):
        """Counter should increment on each request."""
        crud = AIChatCRUD(test_db_session)
        telegram_id = sample_daily_limit.telegram_id
        initial_count = sample_daily_limit.request_count
        
        can_request, remaining = crud.check_and_update_limit(telegram_id)
        
        assert can_request is True
        assert remaining == DAILY_LIMIT - initial_count - 1
        
        # Verify counter incremented
        test_db_session.refresh(sample_daily_limit)
        assert sample_daily_limit.request_count == initial_count + 1
    
    def test_limit_exceeded(self, test_db_session, sample_telegram_id):
        """Should reject request when limit exceeded."""
        crud = AIChatCRUD(test_db_session)
        
        # Create limit at maximum
        limit = AIChatDailyLimit(
            telegram_id=sample_telegram_id,
            request_count=DAILY_LIMIT,
            last_reset_date=date.today()
        )
        test_db_session.add(limit)
        test_db_session.commit()
        
        can_request, remaining = crud.check_and_update_limit(sample_telegram_id)
        
        assert can_request is False
        assert remaining == 0
        
        # Counter should NOT increment
        test_db_session.refresh(limit)
        assert limit.request_count == DAILY_LIMIT
    
    def test_reset_on_new_day(self, test_db_session, sample_telegram_id):
        """Counter should reset when it's a new day."""
        crud = AIChatCRUD(test_db_session)
        
        # Create limit from yesterday
        yesterday = date.today() - timedelta(days=1)
        limit = AIChatDailyLimit(
            telegram_id=sample_telegram_id,
            request_count=25,
            last_reset_date=yesterday
        )
        test_db_session.add(limit)
        test_db_session.commit()
        
        can_request, remaining = crud.check_and_update_limit(sample_telegram_id)
        
        assert can_request is True
        assert remaining == DAILY_LIMIT - 1
        
        # Verify reset
        test_db_session.refresh(limit)
        assert limit.request_count == 1
        assert limit.last_reset_date == date.today()


class TestGetLimits:
    """Tests for get_limits method."""
    
    def test_new_user(self, test_db_session, sample_telegram_id):
        """New user should get default limits."""
        crud = AIChatCRUD(test_db_session)
        
        limits = crud.get_limits(sample_telegram_id)
        
        assert limits["requests_today"] == 0
        assert limits["requests_remaining"] == DAILY_LIMIT
        assert limits["daily_limit"] == DAILY_LIMIT
        assert limits["reset_date"] == date.today()
    
    def test_existing_user(self, test_db_session, sample_daily_limit):
        """Existing user should get current limits."""
        crud = AIChatCRUD(test_db_session)
        telegram_id = sample_daily_limit.telegram_id
        
        limits = crud.get_limits(telegram_id)
        
        assert limits["requests_today"] == sample_daily_limit.request_count
        assert limits["requests_remaining"] == DAILY_LIMIT - sample_daily_limit.request_count
        assert limits["daily_limit"] == DAILY_LIMIT
    
    def test_does_not_modify_counter(self, test_db_session, sample_daily_limit):
        """get_limits should NOT modify the counter."""
        crud = AIChatCRUD(test_db_session)
        telegram_id = sample_daily_limit.telegram_id
        initial_count = sample_daily_limit.request_count
        
        limits = crud.get_limits(telegram_id)
        
        test_db_session.refresh(sample_daily_limit)
        assert sample_daily_limit.request_count == initial_count


class TestSaveChatRequest:
    """Tests for save_chat_request method."""
    
    def test_save_request(self, test_db_session, sample_telegram_id):
        """Should save chat request to database."""
        crud = AIChatCRUD(test_db_session)
        
        message = "Тестовый вопрос"
        response = "Тестовый ответ"
        tokens = 150
        
        record = crud.save_chat_request(
            telegram_id=sample_telegram_id,
            user_id=None,
            message=message,
            response=response,
            tokens_used=tokens
        )
        
        assert record.id is not None
        assert record.telegram_id == sample_telegram_id
        assert record.message == message
        assert record.response == response
        assert record.tokens_used == tokens
        assert record.request_date == date.today()
        assert record.created_at is not None


class TestGetChatHistory:
    """Tests for get_chat_history method."""
    
    def test_empty_history(self, test_db_session, sample_telegram_id):
        """Should return empty list for user with no history."""
        crud = AIChatCRUD(test_db_session)
        
        records, total = crud.get_chat_history(sample_telegram_id)
        
        assert records == []
        assert total == 0
    
    def test_get_history(self, test_db_session, create_chat_history):
        """Should return chat history with pagination."""
        create_chat_history(10)
        crud = AIChatCRUD(test_db_session)
        
        records, total = crud.get_chat_history(123456789, limit=5, offset=0)
        
        assert len(records) == 5
        assert total == 10
    
    def test_pagination(self, test_db_session, create_chat_history):
        """Should support pagination."""
        create_chat_history(15)
        crud = AIChatCRUD(test_db_session)
        
        # First page
        records1, total1 = crud.get_chat_history(123456789, limit=5, offset=0)
        # Second page
        records2, total2 = crud.get_chat_history(123456789, limit=5, offset=5)
        
        assert len(records1) == 5
        assert len(records2) == 5
        assert total1 == total2 == 15
        assert records1[0].id != records2[0].id


class TestGetRecentContext:
    """Tests for get_recent_context method."""
    
    def test_empty_context(self, test_db_session, sample_telegram_id):
        """Should return empty list for user with no history."""
        crud = AIChatCRUD(test_db_session)
        
        context = crud.get_recent_context(sample_telegram_id)
        
        assert context == []
    
    def test_get_context(self, test_db_session, create_chat_history):
        """Should return recent messages in correct format."""
        create_chat_history(3)
        crud = AIChatCRUD(test_db_session)
        
        context = crud.get_recent_context(123456789, limit=5)
        
        assert len(context) == 6  # 3 messages * 2 (user + assistant)
        assert context[0]["role"] == "user"
        assert context[1]["role"] == "assistant"
        assert "content" in context[0]
        assert "content" in context[1]
    
    def test_limit_context(self, test_db_session, create_chat_history):
        """Should respect limit parameter."""
        create_chat_history(10)
        crud = AIChatCRUD(test_db_session)
        
        context = crud.get_recent_context(123456789, limit=3)
        
        assert len(context) == 6  # 3 messages * 2


class TestResetUserLimit:
    """Tests for reset_user_limit method."""
    
    def test_reset_limit(self, test_db_session, sample_daily_limit):
        """Should reset user's limit."""
        crud = AIChatCRUD(test_db_session)
        telegram_id = sample_daily_limit.telegram_id
        
        success = crud.reset_user_limit(telegram_id)
        
        assert success is True
        
        test_db_session.refresh(sample_daily_limit)
        assert sample_daily_limit.request_count == 0
        assert sample_daily_limit.last_reset_date == date.today()
    
    def test_reset_nonexistent_user(self, test_db_session):
        """Should return False for non-existent user."""
        crud = AIChatCRUD(test_db_session)
        
        success = crud.reset_user_limit(999999999)
        
        assert success is False


class TestGetUserStats:
    """Tests for get_user_stats method."""
    
    def test_empty_stats(self, test_db_session, sample_telegram_id):
        """Should return zeros for user with no history."""
        crud = AIChatCRUD(test_db_session)
        
        stats = crud.get_user_stats(sample_telegram_id, days=7)
        
        assert stats["total_requests"] == 0
        assert stats["total_tokens"] == 0
        assert stats["days"] == 7
        assert stats["avg_requests_per_day"] == 0
        assert stats["avg_tokens_per_request"] == 0
    
    def test_calculate_stats(self, test_db_session, create_chat_history):
        """Should calculate correct statistics."""
        create_chat_history(10)
        crud = AIChatCRUD(test_db_session)
        
        stats = crud.get_user_stats(123456789, days=7)
        
        assert stats["total_requests"] == 10
        assert stats["total_tokens"] > 0
        assert stats["avg_requests_per_day"] > 0
        assert stats["avg_tokens_per_request"] > 0

