"""
AI Chat Service - FastAPI application.

Provides REST API for conversational AI chat with Wildberries focus.
"""

import os
import logging
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from openai import OpenAI

from .database import Base, engine, get_db, init_db
from .schemas import (
    ChatSendRequest,
    ChatSendResponse,
    ChatHistoryRequest,
    ChatHistoryResponse,
    ChatLimitsResponse,
    ResetLimitRequest,
    ResetLimitResponse,
    ChatStatsResponse,
)
from .crud import AIChatCRUD, DAILY_LIMIT
from .prompts import SYSTEM_PROMPT


# ============================================================================
# Configuration
# ============================================================================

# Environment variables
API_SECRET_KEY = os.getenv("API_SECRET_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", None)
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_TEMPERATURE = float(os.getenv("OPENAI_TEMPERATURE", "0.7"))
OPENAI_MAX_TOKENS = int(os.getenv("OPENAI_MAX_TOKENS", "1000"))
AI_CHAT_PORT = int(os.getenv("AI_CHAT_PORT", "9001"))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# ============================================================================
# Application Lifecycle
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info("🚀 Starting AI Chat Service...")
    
    # Check OpenAI API key
    if not OPENAI_API_KEY:
        logger.warning("⚠️  OPENAI_API_KEY not configured!")
    else:
        logger.info("✅ OpenAI API key configured")
    
    # Create database tables (skip in tests)
    if not os.getenv("TESTING"):
        try:
            Base.metadata.create_all(bind=engine)
            logger.info("✅ Database tables created/verified")
        except Exception as e:
            logger.error(f"❌ Failed to create database tables: {e}")
            raise
    
    logger.info(f"🎯 Service ready on port {AI_CHAT_PORT}")
    
    yield
    
    # Shutdown
    logger.info("👋 Shutting down AI Chat Service...")


# ============================================================================
# FastAPI Application
# ============================================================================

app = FastAPI(
    title="AI Chat Service",
    description="AI чат-ассистент для продавцов Wildberries с ограничением запросов",
    version="1.0.0",
    lifespan=lifespan,
)


# ============================================================================
# Helper Functions
# ============================================================================

def _verify_api_key(x_api_key: Optional[str] = Header(None, alias="X-API-KEY")) -> None:
    """
    Verify API key from request headers.
    
    Args:
        x_api_key: API key from X-API-KEY header
        
    Raises:
        HTTPException: If API key is invalid or missing
    """
    if not API_SECRET_KEY:
        logger.error("❌ API_SECRET_KEY not configured on server")
        raise HTTPException(
            status_code=500,
            detail="API authentication not configured on server"
        )
    
    if not x_api_key or x_api_key != API_SECRET_KEY:
        logger.warning(f"⛔ Invalid API key attempt")
        raise HTTPException(
            status_code=403,
            detail="Invalid or missing API key"
        )


def _get_openai_client() -> OpenAI:
    """
    Create OpenAI client.
    
    Returns:
        OpenAI: Configured OpenAI client
        
    Raises:
        HTTPException: If OpenAI API key not configured
    """
    if not OPENAI_API_KEY:
        logger.error("❌ OPENAI_API_KEY not configured")
        raise HTTPException(
            status_code=500,
            detail="OpenAI API key not configured"
        )
    
    client_kwargs = {"api_key": OPENAI_API_KEY}
    if OPENAI_BASE_URL:
        client_kwargs["base_url"] = OPENAI_BASE_URL
    
    return OpenAI(**client_kwargs)


def _call_openai(
    messages: list,
    model: str = OPENAI_MODEL,
    max_tokens: int = OPENAI_MAX_TOKENS,
    temperature: float = OPENAI_TEMPERATURE
) -> tuple[str, int]:
    """
    Call OpenAI API with messages.
    
    Args:
        messages: List of message dicts for OpenAI API
        model: Model name (default from env)
        max_tokens: Maximum tokens in response
        temperature: Sampling temperature (0.0-2.0)
        
    Returns:
        tuple[str, int]: (response_text, tokens_used)
        
    Raises:
        HTTPException: If API call fails
    """
    try:
        client = _get_openai_client()
        
        logger.info(f"🤖 Calling OpenAI: model={model}, max_tokens={max_tokens}, temperature={temperature}, messages={len(messages)}")
        
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature
        )
        
        response_text = response.choices[0].message.content
        tokens_used = response.usage.total_tokens
        
        logger.info(f"✅ OpenAI response received: {len(response_text)} chars, {tokens_used} tokens")
        
        return (response_text, tokens_used)
        
    except Exception as e:
        logger.error(f"❌ OpenAI API error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"AI service error: {str(e)}"
        )


# ============================================================================
# API Endpoints
# ============================================================================

@app.get("/health")
async def health_check():
    """
    Health check endpoint.
    
    Returns service status without authentication.
    """
    return {
        "status": "ok",
        "service": "ai_chat",
        "version": "1.0.0"
    }


@app.post("/v1/chat/send", response_model=ChatSendResponse)
async def send_message(
    request: ChatSendRequest,
    db: Session = Depends(get_db),
    _: None = Depends(_verify_api_key)
):
    """
    Send message to AI and get response.
    
    Rate limited to 30 requests per day per user.
    """
    telegram_id = request.telegram_id
    message = request.message
    user_context = request.user_context
    
    logger.info(f"📨 Received chat request: telegram_id={telegram_id}, message_length={len(message)}, has_context={user_context is not None}")
    
    # Initialize CRUD
    crud = AIChatCRUD(db)
    
    # Check and update rate limit
    can_request, remaining = crud.check_and_update_limit(telegram_id)
    
    if not can_request:
        logger.warning(f"⛔ Rate limit exceeded for telegram_id={telegram_id}")
        raise HTTPException(
            status_code=429,
            detail={
                "error": "Rate limit exceeded",
                "message": "Вы исчерпали дневной лимит запросов (30/день). Попробуйте завтра! 🌅",
                "daily_limit": DAILY_LIMIT,
                "requests_today": DAILY_LIMIT,
                "requests_remaining": 0
            }
        )
    
    # Get recent context for AI
    context_messages = crud.get_recent_context(telegram_id, limit=5)
    
    # Build messages for OpenAI
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        *context_messages,
    ]
    
    # Add user context if available
    if user_context:
        messages.append({
            "role": "system",
            "content": f"📊 ДАННЫЕ ПОЛЬЗОВАТЕЛЯ:\n{user_context}\n\nИспользуй эти данные для персонализированных ответов!"
        })
        logger.info(f"✅ Added user context: {len(user_context)} chars")
    
    # Add user message
    messages.append({"role": "user", "content": message})
    
    # Call OpenAI
    response_text, tokens_used = _call_openai(messages)
    
    # Save to database
    crud.save_chat_request(
        telegram_id=telegram_id,
        user_id=None,  # TODO: Link with main database if needed
        message=message,
        response=response_text,
        tokens_used=tokens_used
    )
    
    logger.info(f"✅ Chat request completed: telegram_id={telegram_id}, remaining={remaining}")
    
    return ChatSendResponse(
        response=response_text,
        remaining_requests=remaining,
        tokens_used=tokens_used
    )


@app.post("/v1/chat/history", response_model=ChatHistoryResponse)
async def get_history(
    request: ChatHistoryRequest,
    db: Session = Depends(get_db),
    _: None = Depends(_verify_api_key)
):
    """
    Get chat history for user with pagination.
    """
    telegram_id = request.telegram_id
    limit = request.limit
    offset = request.offset
    
    logger.info(f"📜 History request: telegram_id={telegram_id}, limit={limit}, offset={offset}")
    
    crud = AIChatCRUD(db)
    records, total = crud.get_chat_history(telegram_id, limit=limit, offset=offset)
    
    return ChatHistoryResponse(
        items=records,
        total=total,
        limit=limit,
        offset=offset
    )


@app.get("/v1/chat/limits/{telegram_id}", response_model=ChatLimitsResponse)
async def get_limits(
    telegram_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(_verify_api_key)
):
    """
    Get current rate limits for user.
    
    Does NOT modify the request counter.
    """
    logger.info(f"📊 Limits check: telegram_id={telegram_id}")
    
    crud = AIChatCRUD(db)
    limits = crud.get_limits(telegram_id)
    
    return ChatLimitsResponse(
        telegram_id=telegram_id,
        **limits
    )


@app.post("/v1/chat/reset-limit", response_model=ResetLimitResponse)
async def reset_limit(
    request: ResetLimitRequest,
    db: Session = Depends(get_db),
    _: None = Depends(_verify_api_key)
):
    """
    Reset user's daily limit (admin function).
    """
    telegram_id = request.telegram_id
    
    logger.info(f"🔄 Admin reset request: telegram_id={telegram_id}")
    
    crud = AIChatCRUD(db)
    success = crud.reset_user_limit(telegram_id)
    
    if success:
        return ResetLimitResponse(
            success=True,
            message=f"Лимит пользователя {telegram_id} успешно сброшен"
        )
    else:
        return ResetLimitResponse(
            success=False,
            message=f"Пользователь {telegram_id} не найден"
        )


@app.get("/v1/chat/stats/{telegram_id}")
async def get_stats(
    telegram_id: int,
    days: int = 7,
    db: Session = Depends(get_db),
    _: None = Depends(_verify_api_key)
):
    """
    Get user statistics for the last N days.
    """
    logger.info(f"📊 Stats request: telegram_id={telegram_id}, days={days}")
    
    if days < 1 or days > 365:
        raise HTTPException(
            status_code=400,
            detail="Days parameter must be between 1 and 365"
        )
    
    crud = AIChatCRUD(db)
    stats = crud.get_user_stats(telegram_id, days=days)
    
    return {
        "telegram_id": telegram_id,
        **stats
    }


# ============================================================================
# Application Entry Point
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "ai_chat.service:app",
        host="0.0.0.0",
        port=AI_CHAT_PORT,
        reload=True
    )

