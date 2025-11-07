"""
AI Chat Service - Conversational AI for Wildberries sellers.

This service provides:
- AI-powered chat assistance for Wildberries and e-commerce topics
- Rate limiting (30 requests per day per user)
- Chat history storage
- Integration with Telegram bot via REST API
"""

__version__ = "1.0.0"

from .database import Base, engine, SessionLocal, get_db, init_db
from .models import AIChatRequest, AIChatDailyLimit
from .schemas import (
    ChatSendRequest,
    ChatSendResponse,
    ChatHistoryRequest,
    ChatHistoryItem,
    ChatHistoryResponse,
    ChatLimitsResponse,
    ResetLimitRequest,
    ResetLimitResponse,
    ChatStatsResponse,
)
from .crud import AIChatCRUD, DAILY_LIMIT
from .prompts import SYSTEM_PROMPT, SYSTEM_PROMPT_SHORT

__all__ = [
    # Version
    "__version__",
    # Database
    "Base",
    "engine",
    "SessionLocal",
    "get_db",
    "init_db",
    # Models
    "AIChatRequest",
    "AIChatDailyLimit",
    # Schemas
    "ChatSendRequest",
    "ChatSendResponse",
    "ChatHistoryRequest",
    "ChatHistoryItem",
    "ChatHistoryResponse",
    "ChatLimitsResponse",
    "ResetLimitRequest",
    "ResetLimitResponse",
    "ChatStatsResponse",
    # CRUD
    "AIChatCRUD",
    "DAILY_LIMIT",
    # Prompts
    "SYSTEM_PROMPT",
    "SYSTEM_PROMPT_SHORT",
]
