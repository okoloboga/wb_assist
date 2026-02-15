"""
AI Chat Service - FastAPI application.

Provides REST API for conversational AI chat with Wildberries focus.
"""

import os
import logging
from typing import Optional
from pathlib import Path
from dotenv import load_dotenv

# Загружаем переменные окружения из корневого .env файла
# В Docker переменные окружения уже установлены через docker-compose.yml
env_file = Path(__file__).parent.parent.parent.parent / ".env"
if env_file.exists():
    load_dotenv(env_file)
else:
    # Пробуем загрузить из текущей директории (для обратной совместимости)
    load_dotenv(override=False)

from fastapi import APIRouter, FastAPI, HTTPException, Header, Depends
from sqlalchemy.orm import Session
from openai import OpenAI

from .database import Base, engine, get_db
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
from ..agent import run_agent
from ..tools.db_pool import init_pool as init_asyncpg_pool, close_pool as close_asyncpg_pool

# Import user model helper (correct path)
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from gpt_integration.core.user_model import get_user_preferred_model_async

# RAG integration
try:
    from ..rag.prompt_enricher import enrich_prompt_with_rag, RAG_ENABLED
    from ..rag.utils import get_cabinet_id_for_user
except ImportError:
    # Fallback для случая, когда папка называется RAG (с большой буквы)
    from ..RAG.prompt_enricher import enrich_prompt_with_rag, RAG_ENABLED
    from ..RAG.utils import get_cabinet_id_for_user


# ============================================================================
# Configuration
# ============================================================================

# Environment variables
API_SECRET_KEY = os.getenv("API_SECRET_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
_openai_base_url_raw = os.getenv("OPENAI_BASE_URL")
OPENAI_BASE_URL = None
if _openai_base_url_raw and _openai_base_url_raw.strip():
    _openai_base_url_clean = _openai_base_url_raw.strip()
    # Проверяем, что URL валидный (начинается с http:// или https://)
    if _openai_base_url_clean.startswith(("http://", "https://")):
        OPENAI_BASE_URL = _openai_base_url_clean
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
    if OPENAI_BASE_URL and OPENAI_BASE_URL.strip():
        client_kwargs["base_url"] = OPENAI_BASE_URL.strip()
    
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


router = APIRouter(tags=["ai-chat"])

@router.get("/health")
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


@router.post("/send", response_model=ChatSendResponse)
async def send_message(
    request: ChatSendRequest,
    db: Session = Depends(get_db),
    _: None = Depends(_verify_api_key)
):
    """
    Send message to AI and get response.
    
    Rate limited to DAILY_LIMIT requests per day per user (0 = unlimited).
    """
    telegram_id = request.telegram_id
    message = request.message
    user_context = request.user_context
    
    logger.info(f"📨 Received chat request: telegram_id={telegram_id}, message_length={len(message)}, has_context={user_context is not None}")
    
    try:
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
                    "message": (
                        f"Вы исчерпали дневной лимит запросов ({DAILY_LIMIT}/день). "
                        "Попробуйте завтра! 🌅"
                    ),
                    "daily_limit": DAILY_LIMIT,
                    "requests_today": DAILY_LIMIT,
                    "requests_remaining": 0
                }
            )
        
        # Get recent context for AI
        context_messages = crud.get_recent_context(telegram_id, limit=5)
        
        # Получаем предпочитаемую модель пользователя
        user_model = await get_user_preferred_model_async(telegram_id)
        logger.info(f"🤖 Using AI model for user {telegram_id}: {user_model}")
        
        # RAG: Получить cabinet_id и обогатить промпт
        system_prompt = SYSTEM_PROMPT
        cabinet_id = None
        
        if RAG_ENABLED:
            try:
                cabinet_id = await get_cabinet_id_for_user(telegram_id)
                if cabinet_id:
                    system_prompt = await enrich_prompt_with_rag(
                        user_message=message,
                        cabinet_id=cabinet_id,
                        original_prompt=SYSTEM_PROMPT
                    )
                    logger.info(
                        f"✅ Prompt enriched with RAG context for "
                        f"telegram_id={telegram_id}, cabinet_id={cabinet_id}"
                    )
                else:
                    logger.debug(
                        f"⚠️ Cabinet not found for telegram_id={telegram_id}, "
                        f"using original prompt"
                    )
            except Exception as e:
                logger.error(
                    f"❌ Error enriching prompt with RAG for "
                    f"telegram_id={telegram_id}: {e}",
                    exc_info=True
                )
                # Fallback на исходный промпт
                system_prompt = SYSTEM_PROMPT
        
        # Build messages for OpenAI
        # Добавляем telegram_id в system prompt, чтобы AI знал его и не запрашивал у пользователя
        system_prompt_with_context = f"""{system_prompt}

**КРИТИЧЕСКИ ВАЖНО - КОНТЕКСТ ПОЛЬЗОВАТЕЛЯ:**
- Telegram ID пользователя: {telegram_id}
- ❌ НИКОГДА не запрашивай Telegram ID у пользователя - он уже известен!
- ✅ ВСЕГДА используй `telegram_id={telegram_id}` при вызове любого инструмента.
- ✅ Например, вызов инструмента `run_report` должен выглядеть так: `run_report(report_name='top_products', params={{'telegram_id': {telegram_id}}})`. `telegram_id` должен быть внутри `params`.
- ✅ Если пользователь спрашивает про свои данные, сразу используй инструменты с `telegram_id={telegram_id}`, НЕ спрашивая у пользователя."""
        
        messages = [
            {"role": "system", "content": system_prompt_with_context},
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
        
        # Stage 1: Call internal agent (LLM + tools in next stage)
        try:
            agent_result = await run_agent(messages, model=user_model)
            response_text = agent_result.get("final", "")
            tokens_used = agent_result.get("tokens_used", 0)
        except RuntimeError as e:
            # Handle regional restriction and other runtime errors
            error_msg = str(e)
            if "недоступен в вашем регионе" in error_msg or "unsupported_country" in error_msg.lower():
                logger.error(f"❌ Regional restriction error for telegram_id={telegram_id}: {error_msg}")
                raise HTTPException(
                    status_code=503,
                    detail={
                        "error": "OpenAI API unavailable",
                        "message": (
                            "⚠️ OpenAI API недоступен в вашем регионе.\n\n"
                            "Для решения проблемы необходимо настроить альтернативный API endpoint:\n"
                            "1. Используйте прокси-сервер для OpenAI API\n"
                            "2. Или используйте OpenAI-совместимый провайдер (Azure OpenAI, Anyscale и др.)\n"
                            "3. Установите переменную окружения OPENAI_BASE_URL с адресом альтернативного endpoint\n\n"
                            f"Технические детали: {error_msg}"
                        )
                    }
                )
            else:
                logger.error(f"❌ Runtime error for telegram_id={telegram_id}: {error_msg}")
                # Убираем дублирование, если сообщение уже содержит "Ошибка запроса к LLM"
                if "Ошибка запроса к LLM:" in error_msg:
                    display_msg = error_msg
                else:
                    display_msg = f"⚠️ Ошибка запроса к LLM: {error_msg}"
                raise HTTPException(
                    status_code=500,
                    detail={
                        "error": "LLM request failed",
                        "message": display_msg
                    }
                )
        except Exception as e:
            logger.error(f"❌ Unexpected error for telegram_id={telegram_id}: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "Internal server error",
                    "message": "⚠️ Произошла внутренняя ошибка. Пожалуйста, повторите попытку позже."
                }
            )
        
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
    except HTTPException:
        # Re-raise HTTP exceptions (rate limit, etc.)
        raise
    except Exception as e:
        # Catch any other database or CRUD errors
        logger.error(f"❌ Database/CRUD error for telegram_id={telegram_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Database error",
                "message": f"⚠️ Ошибка работы с базой данных: {str(e)}"
            }
        )


@router.post("/history", response_model=ChatHistoryResponse)
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


@router.get("/limits/{telegram_id}", response_model=ChatLimitsResponse)
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


@router.post("/reset-limit", response_model=ResetLimitResponse)
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


@router.get("/stats/{telegram_id}")
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

def setup_ai_chat(app: FastAPI) -> None:
    """
    Register startup/shutdown handlers for AI chat components on the main app.
    """
    app.add_event_handler("startup", _startup_event)
    app.add_event_handler("shutdown", _shutdown_event)


# ============================================================================
# Internal lifecycle events for shared usage
# ============================================================================

_startup_registered = False


async def _startup_event():
    """Startup tasks for AI chat (idempotent)."""
    global _startup_registered
    if _startup_registered:
        return
    _startup_registered = True
    
    logger.info("🚀 Starting AI Chat Service components...")
    
    if not OPENAI_API_KEY:
        logger.warning("⚠️  OPENAI_API_KEY not configured!")
    else:
        logger.info("✅ OpenAI API key configured")
    
    if not os.getenv("TESTING"):
        try:
            Base.metadata.create_all(bind=engine)
            logger.info("✅ Database tables created/verified")
        except Exception as exc:
            logger.error("❌ Failed to create database tables: %s", exc, exc_info=True)
            # Don't raise - allow service to start even if DB init fails
            # The error will be caught when trying to use DB
            logger.warning("⚠️  Service will continue, but database operations may fail")
    
    try:
        await init_asyncpg_pool()
        logger.info("✅ asyncpg pool initialized (if Postgres configured)")
    except Exception as exc:
        logger.warning("⚠️  asyncpg pool not initialized: %s", exc)
    
    # Initialize RAG database tables
    try:
        from ..RAG.database import init_rag_db
        init_rag_db()
        logger.info("✅ RAG database tables created/verified")
    except Exception as exc:
        logger.error("❌ Failed to initialize RAG database: %s", exc, exc_info=True)
        # Don't raise - allow service to start even if RAG DB init fails
        logger.warning("⚠️  Service will continue, but RAG features may not work")
    
    logger.info("🎯 AI Chat components ready")


async def _shutdown_event():
    """Shutdown tasks for AI chat."""
    logger.info("👋 Shutting down AI Chat components...")
    try:
        await close_asyncpg_pool()
    except Exception:
        pass


# ============================================================================
# Standalone application factory (legacy / manual usage)
# ============================================================================


def create_app() -> FastAPI:
    """Create a standalone FastAPI app for legacy/manual runs."""
    standalone_app = FastAPI(
        title="AI Chat Service",
        description="AI чат-ассистент для продавцов Wildberries с ограничением запросов",
        version="1.0.0",
    )
    setup_ai_chat(standalone_app)
    standalone_app.include_router(router, prefix="/v1/chat")
    standalone_app.add_api_route("/health", health_check, methods=["GET"], include_in_schema=False)
    return standalone_app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "gpt_integration.ai_chat.app.service:app",
        host="0.0.0.0",
        port=AI_CHAT_PORT,
        reload=True
    )
