"""
CRUD operations for AI Chat Service.

Handles database operations for chat history and rate limiting.
"""

import logging
import os
from datetime import date, datetime, timedelta
from typing import Tuple, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from .models import AIChatRequest, AIChatDailyLimit


# Configure logging
logger = logging.getLogger(__name__)

# Daily request limit (0 = unlimited)
def _load_daily_limit() -> int:
    raw = os.getenv("RAG_USAGE") or os.getenv("DAILY_LIMIT") or "30"
    try:
        value = int(raw)
        return max(0, value)
    except ValueError:
        logger.warning(f"⚠️ Invalid RAG_USAGE/DAILY_LIMIT value '{raw}', fallback to 30")
        return 30


DAILY_LIMIT = _load_daily_limit()


class AIChatCRUD:
    """
    CRUD operations for AI Chat Service.
    
    Handles:
    - Rate limiting (30 requests per day)
    - Chat history storage
    - User statistics
    """
    
    def __init__(self, db: Session):
        """
        Initialize CRUD with database session.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
    
    def check_and_update_limit(self, telegram_id: int) -> Tuple[bool, int]:
        """
        Check if user can make a request and update counter.

        This method:
        1. Gets or creates limit record
        2. Resets counter if it's a new day
        3. Checks if limit is exceeded
        4. Increments counter if allowed

        Args:
            telegram_id: Telegram user ID

        Returns:
            Tuple[bool, int]: (can_request, remaining_requests)
                - can_request: True if request allowed
                - remaining_requests: Number of requests left (0 if exceeded, -1 if unlimited)
        """
        if DAILY_LIMIT == 0:
            logger.debug(f"♾️ Limit disabled (DAILY_LIMIT=0) for telegram_id={telegram_id}")
            return (True, -1)  # -1 indicates unlimited

        today = date.today()
        
        # Get or create limit record
        limit_record = self.db.query(AIChatDailyLimit).filter(
            AIChatDailyLimit.telegram_id == telegram_id
        ).first()
        
        if not limit_record:
            # Create new record for first-time user
            limit_record = AIChatDailyLimit(
                telegram_id=telegram_id,
                request_count=0,
                last_reset_date=today
            )
            self.db.add(limit_record)
            self.db.commit()
            self.db.refresh(limit_record)
            logger.info(f"✨ Created new limit record for telegram_id={telegram_id}")
        
        # Reset counter if it's a new day
        if limit_record.last_reset_date < today:
            limit_record.request_count = 0
            limit_record.last_reset_date = today
            self.db.commit()
            logger.info(f"🔄 Reset daily limit for telegram_id={telegram_id}")
        
        # Check if limit exceeded
        if limit_record.request_count >= DAILY_LIMIT:
            logger.warning(f"⛔ Limit exceeded for telegram_id={telegram_id} ({limit_record.request_count}/{DAILY_LIMIT})")
            return (False, 0)
        
        # Increment counter
        limit_record.request_count += 1
        limit_record.updated_at = datetime.now()
        self.db.commit()
        
        remaining = DAILY_LIMIT - limit_record.request_count
        logger.info(f"✅ Request allowed for telegram_id={telegram_id} ({limit_record.request_count}/{DAILY_LIMIT}, remaining={remaining})")
        
        return (True, remaining)
    
    def get_limits(self, telegram_id: int) -> dict:
        """
        Get current rate limits for user WITHOUT modifying counter.

        Args:
            telegram_id: Telegram user ID

        Returns:
            dict: Limit information
                - requests_today: Current counter
                - requests_remaining: Remaining requests (-1 if unlimited)
                - daily_limit: Daily limit (0 if unlimited)
                - reset_date: Last reset date
        """
        if DAILY_LIMIT == 0:
            today = date.today()
            return {
                "requests_today": 0,
                "requests_remaining": -1,  # -1 indicates unlimited
                "daily_limit": 0,
                "reset_date": today
            }

        today = date.today()
        
        limit_record = self.db.query(AIChatDailyLimit).filter(
            AIChatDailyLimit.telegram_id == telegram_id
        ).first()
        
        if not limit_record:
            # User has never used the service
            return {
                "requests_today": 0,
                "requests_remaining": DAILY_LIMIT,
                "daily_limit": DAILY_LIMIT,
                "reset_date": today
            }
        
        # Reset if it's a new day (but don't save to DB yet)
        requests_today = 0 if limit_record.last_reset_date < today else limit_record.request_count
        
        return {
            "requests_today": requests_today,
            "requests_remaining": max(0, DAILY_LIMIT - requests_today),
            "daily_limit": DAILY_LIMIT,
            "reset_date": limit_record.last_reset_date if limit_record.last_reset_date >= today else today
        }
    
    def save_chat_request(
        self, 
        telegram_id: int, 
        user_id: Optional[int],
        message: str, 
        response: str, 
        tokens_used: int
    ) -> AIChatRequest:
        """
        Save chat request and response to history.
        
        Args:
            telegram_id: Telegram user ID
            user_id: User ID from main database (optional)
            message: User's message
            response: AI's response
            tokens_used: Number of tokens consumed
            
        Returns:
            AIChatRequest: Created database record
        """
        chat_request = AIChatRequest(
            telegram_id=telegram_id,
            user_id=user_id,
            message=message,
            response=response,
            tokens_used=tokens_used,
            request_date=date.today()
        )
        
        self.db.add(chat_request)
        self.db.commit()
        self.db.refresh(chat_request)
        
        logger.info(f"💾 Saved chat request: telegram_id={telegram_id}, tokens={tokens_used}, id={chat_request.id}")
        
        return chat_request
    
    def get_chat_history(
        self, 
        telegram_id: int, 
        limit: int = 10, 
        offset: int = 0
    ) -> Tuple[List[AIChatRequest], int]:
        """
        Get paginated chat history for user.
        
        Args:
            telegram_id: Telegram user ID
            limit: Number of records to return
            offset: Offset for pagination
            
        Returns:
            Tuple[List[AIChatRequest], int]: (records, total_count)
        """
        query = self.db.query(AIChatRequest).filter(
            AIChatRequest.telegram_id == telegram_id
        )
        
        total = query.count()
        
        records = query.order_by(
            AIChatRequest.created_at.desc()
        ).limit(limit).offset(offset).all()
        
        logger.info(f"📜 Retrieved chat history: telegram_id={telegram_id}, total={total}, returned={len(records)}")
        
        return (records, total)
    
    def get_recent_context(self, telegram_id: int, limit: int = 5) -> List[dict]:
        """
        Get recent messages for AI context.
        
        Returns messages in chronological order (oldest first) formatted for OpenAI API.
        
        Args:
            telegram_id: Telegram user ID
            limit: Maximum number of message pairs to retrieve
            
        Returns:
            List[dict]: Messages in OpenAI format
                [
                    {"role": "user", "content": "..."},
                    {"role": "assistant", "content": "..."},
                    ...
                ]
        """
        records = self.db.query(AIChatRequest).filter(
            AIChatRequest.telegram_id == telegram_id
        ).order_by(
            AIChatRequest.created_at.desc()
        ).limit(limit).all()
        
        # Reverse to get chronological order (oldest first)
        records = list(reversed(records))
        
        # Format for OpenAI API
        messages = []
        for record in records:
            messages.append({"role": "user", "content": record.message})
            messages.append({"role": "assistant", "content": record.response})
        
        logger.info(f"🔍 Retrieved context: telegram_id={telegram_id}, messages={len(messages)}")
        
        return messages
    
    def reset_user_limit(self, telegram_id: int) -> bool:
        """
        Reset user's daily limit (admin function).
        
        Args:
            telegram_id: Telegram user ID
            
        Returns:
            bool: True if successful, False if user not found
        """
        limit_record = self.db.query(AIChatDailyLimit).filter(
            AIChatDailyLimit.telegram_id == telegram_id
        ).first()
        
        if not limit_record:
            logger.warning(f"❌ Cannot reset limit: telegram_id={telegram_id} not found")
            return False
        
        limit_record.request_count = 0
        limit_record.last_reset_date = date.today()
        limit_record.updated_at = datetime.now()
        self.db.commit()
        
        logger.info(f"🔄 Admin reset limit for telegram_id={telegram_id}")
        
        return True
    
    def get_user_stats(self, telegram_id: int, days: int = 7) -> dict:
        """
        Get user statistics for the last N days.
        
        Args:
            telegram_id: Telegram user ID
            days: Number of days to analyze
            
        Returns:
            dict: Statistics
                - total_requests: Total number of requests
                - total_tokens: Total tokens used
                - days: Analysis period
                - avg_requests_per_day: Average requests per day
                - avg_tokens_per_request: Average tokens per request
        """
        since_date = date.today() - timedelta(days=days)
        
        records = self.db.query(AIChatRequest).filter(
            AIChatRequest.telegram_id == telegram_id,
            AIChatRequest.request_date >= since_date
        ).all()
        
        total_requests = len(records)
        total_tokens = sum(r.tokens_used for r in records)
        
        # Avoid division by zero
        avg_requests_per_day = total_requests / days if days > 0 else 0
        avg_tokens_per_request = total_tokens / total_requests if total_requests > 0 else 0
        
        stats = {
            "total_requests": total_requests,
            "total_tokens": total_tokens,
            "days": days,
            "avg_requests_per_day": round(avg_requests_per_day, 2),
            "avg_tokens_per_request": round(avg_tokens_per_request, 2)
        }
        
        logger.info(f"📊 Stats for telegram_id={telegram_id}: {stats}")
        
        return stats
