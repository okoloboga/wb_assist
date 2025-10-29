"""
SQLAlchemy models for AI Chat Service.

Models:
    - AIChatRequest: Stores complete chat history
    - AIChatDailyLimit: Tracks daily request limits per user
"""

from sqlalchemy import Column, Integer, BigInteger, String, Text, Date, DateTime, ForeignKey, Index
from sqlalchemy.sql import func
from .database import Base


class AIChatRequest(Base):
    """
    Chat history storage.
    
    Stores all user requests and AI responses with metadata.
    """
    __tablename__ = "ai_chat_requests"
    
    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(BigInteger, nullable=False, index=True)
    user_id = Column(Integer, nullable=True, index=True)  # Reference to main users table (no FK for independence)
    message = Column(Text, nullable=False)
    response = Column(Text, nullable=False)
    tokens_used = Column(Integer, default=0)
    request_date = Column(Date, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=func.now(), nullable=False, index=True)
    
    def __repr__(self) -> str:
        return f"<AIChatRequest(id={self.id}, telegram_id={self.telegram_id}, tokens={self.tokens_used}, date={self.request_date})>"


class AIChatDailyLimit(Base):
    """
    Daily request limit tracking.
    
    Maintains counters for rate limiting (30 requests per day).
    """
    __tablename__ = "ai_chat_daily_limits"
    
    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(BigInteger, nullable=False, unique=True, index=True)
    request_count = Column(Integer, default=0, nullable=False)
    last_reset_date = Column(Date, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def __repr__(self) -> str:
        return f"<AIChatDailyLimit(telegram_id={self.telegram_id}, count={self.request_count}/30)>"

