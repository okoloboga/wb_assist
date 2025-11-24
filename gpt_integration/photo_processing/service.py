"""
Сервис обработки фотографий через нейронную сеть.

Основные функции:
- Обработка фотографий по промпту пользователя
- Интеграция с API генерации изображений
- Сохранение результатов в БД
"""

import os
import logging
import httpx
from typing import Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session

from .image_client import ImageGenerationClient
from .database import SessionLocal
from .models import PhotoProcessingResult

logger = logging.getLogger(__name__)


async def _get_telegram_file_url(bot_token: str, file_id: str) -> str:
    """Get public URL for a Telegram file."""
    async with httpx.AsyncClient() as client:
        get_file_url = f"https://api.telegram.org/bot{bot_token}/getFile"
        try:
            response = await client.post(get_file_url, json={"file_id": file_id}, timeout=20.0)
            response.raise_for_status()
            data = response.json()
            if not data.get("ok"):
                raise ValueError(f"Telegram API error: {data.get('description')}")
            file_path = data["result"]["file_path"]
            return f"https://api.telegram.org/file/bot{bot_token}/{file_path}"
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error getting file path from Telegram: {e.response.text}")
            raise ValueError("Failed to get file path from Telegram.") from e
        except Exception as e:
            logger.error(f"Error getting file path from Telegram: {e}")
            raise ValueError("Failed to get file path from Telegram.") from e


async def process_photo(
    telegram_id: int,
    photo_file_id: str,
    prompt: str,
    user_id: Optional[int] = None,
    bot_token: Optional[str] = None
) -> Dict[str, Any]:
    """
    Обработать фотографию по промпту пользователя.
    
    Args:
        telegram_id: ID пользователя в Telegram
        photo_file_id: Telegram file_id исходного фото
        prompt: Текстовое описание желаемого результата
        user_id: ID пользователя в основной БД (опционально)
        bot_token: Токен Telegram бота (для загрузки фото)
    
    Returns:
        Dict с результатом обработки:
        - photo_url: URL обработанного изображения
        - processing_time: Время обработки в секундах
        - result_id: ID сохраненной записи в БД
    
    Raises:
        ValueError: При некорректных входных данных
        Exception: При ошибках обработки
    """
    start_time = datetime.now()
    
    logger.info(f"📸 Processing photo for user {telegram_id} with prompt: {prompt[:50]}...")
    
    client = None
    try:
        # 1. Получаем токен бота
        if not bot_token:
            bot_token = os.getenv("BOT_TOKEN")
            if not bot_token:
                raise ValueError("BOT_TOKEN not set")
        
        # 2. Получаем URL фото из Telegram
        logger.info(f"📥 Getting file URL from Telegram for: {photo_file_id}")
        image_url = await _get_telegram_file_url(bot_token, photo_file_id)
        
        # 3. Создаем клиент для API генерации изображений
        api_key = os.getenv("IMAGE_GEN_API_KEY") or os.getenv("COMET_API_KEY")
        if not api_key:
            raise ValueError("IMAGE_GEN_API_KEY or COMET_API_KEY not set")
            
        base_url = os.getenv("IMAGE_GEN_BASE_URL") or "https://api.cometapi.com"
        model = os.getenv("IMAGE_GEN_MODEL") or "gemini-2.5-flash-image"
        timeout_str = os.getenv("IMAGE_GEN_TIMEOUT", "120.0")
        timeout = float(timeout_str)

        client = ImageGenerationClient(api_key=api_key, base_url=base_url, model=model, timeout=timeout)
        
        # 4. Обрабатываем изображение
        logger.info(f"🎨 Processing image with prompt: {prompt[:50]}...")
        # `process_image` теперь возвращает data URI, а не словарь
        photo_data_uri = await client.process_image(image_url, prompt)
        
        # 5. Сохраняем результат в БД
        # В данном примере мы сохраняем data URI напрямую.
        # Если нужно загружать куда-то и получать URL, здесь будет доп. логика.
        photo_url = photo_data_uri 
        
        # Засекаем время выполнения только для `process_image`
        processing_time = (datetime.now() - start_time).total_seconds()

        logger.info(f"💾 Saving result to database...")
        result_id = await save_processing_result(
            telegram_id=telegram_id,
            original_photo_file_id=photo_file_id,
            prompt=prompt,
            result_photo_url=photo_url,
            processing_service="gemini_cometapi", # Уточнили сервис
            processing_time=processing_time,
            user_id=user_id
        )
        
        total_time = (datetime.now() - start_time).total_seconds()
        logger.info(f"✅ Photo processed successfully in {total_time:.2f}s, result_id: {result_id}")
        
        return {
            "photo_url": photo_url,
            "processing_time": processing_time,
            "result_id": result_id
        }
    
    except ValueError as e:
        logger.error(f"❌ Validation error: {e}")
        raise
    
    except Exception as e:
        total_time = (datetime.now() - start_time).total_seconds()
        logger.error(f"❌ Photo processing failed after {total_time:.2f}s: {e}")
        raise
    finally:
        if client:
            await client.close()


async def save_processing_result(
    telegram_id: int,
    original_photo_file_id: str,
    prompt: str,
    result_photo_url: str,
    processing_service: str,
    processing_time: float,
    user_id: Optional[int] = None
) -> Optional[int]:
    """
    Сохранить результат обработки фото в БД (Вариант 1: ссылки).
    
    Args:
        telegram_id: ID пользователя в Telegram
        original_photo_file_id: Telegram file_id исходного фото
        prompt: Текст промпта
        result_photo_url: URL обработанного изображения
        processing_service: Название сервиса генерации
        processing_time: Время обработки в секундах
        user_id: ID пользователя в основной БД (опционально)
    
    Returns:
        ID сохраненной записи или None в случае ошибки
    """
    db = SessionLocal()
    try:
        logger.info(f"💾 Saving processing result for user {telegram_id}")
        
        # Создаем новую запись
        result = PhotoProcessingResult(
            telegram_id=telegram_id,
            user_id=user_id,
            original_photo_file_id=original_photo_file_id,
            prompt=prompt,
            result_photo_url=result_photo_url,
            processing_service=processing_service,
            processing_time=processing_time
        )
        
        db.add(result)
        db.commit()
        db.refresh(result)
        
        logger.info(f"✅ Result saved with ID: {result.id}")
        return result.id
    
    except Exception as e:
        logger.error(f"❌ Failed to save result to database: {e}")
        db.rollback()
        return None
    
    finally:
        db.close()


async def get_processing_history(
    telegram_id: int,
    limit: int = 20,
    offset: int = 0
) -> Dict[str, Any]:
    """
    Получить историю обработанных фотографий пользователя.
    
    Args:
        telegram_id: ID пользователя в Telegram
        limit: Количество записей на странице
        offset: Смещение для пагинации
    
    Returns:
        Dict с историей:
        - items: Массив записей с результатами обработки
        - total: Общее количество записей
        - limit: Лимит на странице
        - offset: Текущее смещение
    """
    db = SessionLocal()
    try:
        logger.info(f"📜 Getting processing history for user {telegram_id}, limit={limit}, offset={offset}")
        
        # Получаем общее количество записей
        total = db.query(PhotoProcessingResult).filter(
            PhotoProcessingResult.telegram_id == telegram_id
        ).count()
        
        # Получаем записи с пагинацией и сортировкой по дате (новые первыми)
        results = db.query(PhotoProcessingResult).filter(
            PhotoProcessingResult.telegram_id == telegram_id
        ).order_by(
            PhotoProcessingResult.created_at.desc()
        ).limit(limit).offset(offset).all()
        
        # Форматируем результаты
        items = []
        for result in results:
            items.append({
                "id": result.id,
                "original_photo_file_id": result.original_photo_file_id,
                "prompt": result.prompt,
                "result_photo_url": result.result_photo_url,
                "processing_time": result.processing_time,
                "created_at": result.created_at.isoformat() if result.created_at else None
            })
        
        logger.info(f"✅ Found {len(items)} results (total: {total})")
        
        return {
            "items": items,
            "total": total,
            "limit": limit,
            "offset": offset
        }
    
    except Exception as e:
        logger.error(f"❌ Failed to get processing history: {e}")
        return {
            "items": [],
            "total": 0,
            "limit": limit,
            "offset": offset
        }
    
    finally:
        db.close()










