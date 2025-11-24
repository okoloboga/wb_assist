"""
Сервис обработки фотографий через нейронную сеть.

Основные функции:
- Обработка фотографий по промпту пользователя
- Интеграция с API генерации изображений
- Сохранение результатов в БД
"""

import os
import logging
from typing import Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session

from .image_client import ImageGenerationClient, download_telegram_photo
from .database import SessionLocal
from .models import PhotoProcessingResult

logger = logging.getLogger(__name__)


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
    
    try:
        # Получаем токен бота из переменных окружения, если не передан
        if not bot_token:
            bot_token = os.getenv("BOT_TOKEN")
            if not bot_token:
                raise ValueError("BOT_TOKEN not set")
        
        # Загружаем фото из Telegram
        logger.info(f"📥 Downloading photo from Telegram: {photo_file_id}")
        image_url = await download_telegram_photo(bot_token, photo_file_id)
        
        # Создаем клиент для API генерации изображений
        client = ImageGenerationClient()
        
        # Обрабатываем изображение
        logger.info(f"🎨 Processing image with prompt: {prompt[:50]}...")
        result = await client.process_image(image_url, prompt)
        
        photo_url = result["photo_url"]
        processing_time = result["processing_time"]
        
        # Сохраняем результат в БД
        logger.info(f"💾 Saving result to database...")
        result_id = await save_processing_result(
            telegram_id=telegram_id,
            original_photo_file_id=photo_file_id,
            prompt=prompt,
            result_photo_url=photo_url,
            processing_service="image_generation_api",
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










