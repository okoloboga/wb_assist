"""
Pydantic schemas for AI Chat Service API.

Request/Response models for all API endpoints.
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
from datetime import datetime, date


# ============================================================================
# POST /v1/chat/send
# ============================================================================

class ChatSendRequest(BaseModel):
    """Request to send a message to AI."""
    telegram_id: int = Field(..., description="Telegram user ID", gt=0)
    message: str = Field(
        ..., 
        description="User message to AI", 
        min_length=1, 
        max_length=4000
    )
    user_context: Optional[str] = Field(
        None,
        description="Additional user context from main DB (sales stats, orders, etc.)"
    )


class ChatSendResponse(BaseModel):
    """Response from AI chat."""
    response: str = Field(..., description="AI generated response")
    remaining_requests: int = Field(..., description="Remaining requests for today", ge=0)
    tokens_used: int = Field(..., description="Tokens consumed in this request", ge=0)


# ============================================================================
# POST /v1/chat/history
# ============================================================================

class ChatHistoryRequest(BaseModel):
    """Request to get chat history."""
    telegram_id: int = Field(..., description="Telegram user ID", gt=0)
    limit: int = Field(10, description="Number of items to return", ge=1, le=100)
    offset: int = Field(0, description="Offset for pagination", ge=0)


class ChatHistoryItem(BaseModel):
    """Single chat history item."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    message: str
    response: str
    tokens_used: int
    created_at: datetime


class ChatHistoryResponse(BaseModel):
    """Response with chat history."""
    items: List[ChatHistoryItem] = Field(..., description="Chat history items")
    total: int = Field(..., description="Total number of items", ge=0)
    limit: int = Field(..., description="Requested limit", ge=1)
    offset: int = Field(..., description="Requested offset", ge=0)


# ============================================================================
# GET /v1/chat/limits/{telegram_id}
# ============================================================================

class ChatLimitsResponse(BaseModel):
    """Response with user's rate limits."""
    telegram_id: int = Field(..., description="Telegram user ID")
    requests_today: int = Field(..., description="Requests made today", ge=0)
    requests_remaining: int = Field(..., description="Remaining requests", ge=0)
    daily_limit: int = Field(..., description="Daily request limit")
    reset_date: date = Field(..., description="Date of last reset")


# ============================================================================
# POST /v1/chat/reset-limit
# ============================================================================

class ResetLimitRequest(BaseModel):
    """Request to reset user's limit (admin only)."""
    telegram_id: int = Field(..., description="Telegram user ID to reset", gt=0)


class ResetLimitResponse(BaseModel):
    """Response after limit reset."""
    success: bool = Field(..., description="Whether reset was successful")
    message: str = Field(..., description="Status message")


# ============================================================================
# GET /v1/chat/stats/{telegram_id}
# ============================================================================

class ChatStatsResponse(BaseModel):
    """User statistics response."""
    telegram_id: int
    total_requests: int = Field(..., ge=0)
    total_tokens: int = Field(..., ge=0)
    days: int = Field(..., ge=1)
    avg_requests_per_day: float = Field(..., ge=0)
    avg_tokens_per_request: float = Field(..., ge=0)

