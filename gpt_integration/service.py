"""
GPT Integration Service - главный роутер для всех GPT функционалов.

Модули:
- analysis: анализ данных через GPT
- ai_chat: простой чат через GPT
- card_generation: генерация карточек товаров через GPT
"""

import os
import asyncio
import logging
from typing import Any, Dict, List, Optional
from pathlib import Path
from dotenv import load_dotenv

# Загружаем переменные окружения из корневого .env файла
# В Docker переменные окружения уже установлены через docker-compose.yml
env_file = Path(__file__).parent.parent / ".env"
if env_file.exists():
    load_dotenv(env_file)
else:
    # Пробуем загрузить из текущей директории (для обратной совместимости)
    load_dotenv(override=False)

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

# Import modules
from gpt_integration.analysis.service import orchestrate_analysis
from gpt_integration.analysis.pipeline import run_analysis
from gpt_integration.ai_chat.service import chat as ai_chat_service
from gpt_integration.ai_chat.app.service import (
    router as ai_chat_router,
    setup_ai_chat as setup_ai_chat_components,
)
from gpt_integration.card_generation.service import generate_card as card_generation_service
from gpt_integration.semantic_core.service import generate_semantic_core as semantic_core_service # New import

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="GPT Integration Service", version="1.0.0")

# Включаем полнофункциональный AI Chat Router
setup_ai_chat_components(app)
app.include_router(ai_chat_router, prefix="/v1/chat")


# ============================================================================
# Pydantic Models
# ============================================================================

class ChatRequest(BaseModel):
    messages: List[Dict[str, str]]
    system_prompt: Optional[str] = None


class ChatResponse(BaseModel):
    text: str


class AnalysisRequest(BaseModel):
    data: Dict[str, Any]
    template_path: Optional[str] = None
    validate_output: bool = False


class AnalysisStartRequest(BaseModel):
    telegram_id: int
    period: str = "7d"
    validate_output: bool = True


class CardGenerationRequest(BaseModel):
    telegram_id: int
    photo_file_id: str
    characteristics: Dict[str, str]
    target_audience: str
    selling_points: str


class SemanticCoreRequest(BaseModel): # New Pydantic model
    descriptions_text: str


# ============================================================================
# Health Check
# ============================================================================

@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


# ============================================================================
# AI Chat Endpoints
# ============================================================================

@app.post("/v1/chat", response_model=ChatResponse)
def chat(req: ChatRequest, x_api_key: Optional[str] = Header(None)) -> ChatResponse:
    """
    Простой чат через GPT.
    """
    expected_key = os.getenv("API_SECRET_KEY", "")
    if not x_api_key or x_api_key != expected_key:
        raise HTTPException(status_code=403, detail="Invalid or missing API key")
    
    text = ai_chat_service(req.messages, req.system_prompt)
    return ChatResponse(text=text)


# ============================================================================
# Analysis Endpoints
# ============================================================================

@app.post("/v1/analysis")
def analysis(req: AnalysisRequest) -> Dict[str, Any]:
    """
    Синхронный анализ данных через GPT.
    """
    from gpt_integration.gpt_client import GPTClient
    
    client = GPTClient.from_env()
    result = run_analysis(client, data=req.data, template_path=req.template_path, validate=req.validate_output)
    return result


@app.post("/v1/analysis/start")
async def analysis_start(req: AnalysisStartRequest, x_api_key: Optional[str] = Header(None)) -> Dict[str, Any]:
    """
    Асинхронный запуск анализа для пользователя.
    """
    expected_key = os.getenv("API_SECRET_KEY", "")
    # Simple header check to avoid public triggering
    if not x_api_key or x_api_key != expected_key:
        raise HTTPException(status_code=403, detail="Invalid or missing API key")

    # Fire-and-forget orchestration
    asyncio.create_task(orchestrate_analysis(req.telegram_id, req.period, req.validate_output))
    return {"status": "accepted", "message": "analysis started"}


# ============================================================================
# Card Generation Endpoints
# ============================================================================

@app.post("/v1/card/generate")
async def card_generate(
    req: CardGenerationRequest,
    x_api_key: Optional[str] = Header(None)
) -> Dict[str, Any]:
    """
    Генерация карточки товара через GPT.
    """
    expected_key = os.getenv("API_SECRET_KEY", "")
    if not x_api_key or x_api_key != expected_key:
        raise HTTPException(status_code=403, detail="Invalid or missing API key")
    
    logger.info(f"🎨 Generating card for telegram_id={req.telegram_id}")
    
    try:
        result = card_generation_service(
            characteristics=req.characteristics,
            target_audience=req.target_audience,
            selling_points=req.selling_points
        )
        
        if result.get("status") == "error":
            error_message = result.get("message", "Unknown error")
            error_type = result.get("error_type")
            logger.error(f"❌ Card generation failed: {error_message}")
            
            # Для ошибки региона возвращаем 403 с понятным сообщением
            if error_type == "regional_restriction":
                raise HTTPException(
                    status_code=403,
                    detail=error_message
                )
            
            raise HTTPException(
                status_code=500,
                detail=error_message
            )
        
        return {
            "status": "success",
            "card": result.get("card", "")
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Unexpected error in card generation endpoint: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


# ============================================================================
# Semantic Core Endpoints
# ============================================================================

@app.post("/v1/semantic-core/generate")
async def semantic_core_generate(
    req: SemanticCoreRequest,
    x_api_key: Optional[str] = Header(None)
) -> Dict[str, Any]:
    """
    Генерация семантического ядра на основе описаний товаров.
    """
    expected_key = os.getenv("API_SECRET_KEY", "")
    if not x_api_key or x_api_key != expected_key:
        raise HTTPException(status_code=403, detail="Invalid or missing API key")
    
    logger.info("💎 Generating semantic core...")
    
    try:
        result = semantic_core_service(descriptions_text=req.descriptions_text)
        
        if result.get("status") == "error":
            error_message = result.get("message", "Unknown error")
            logger.error(f"❌ Semantic core generation failed: {error_message}")
            raise HTTPException(
                status_code=500,
                detail=error_message
            )
        
        return {
            "status": "success",
            "core": result.get("core", "")
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Unexpected error in semantic core generation endpoint: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    port_str = os.getenv("GPT_PORT") or "9000"
    port = int(port_str)
    import uvicorn
    uvicorn.run("gpt_integration.service:app", host="0.0.0.0", port=port)
