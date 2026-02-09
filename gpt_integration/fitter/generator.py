"""
Генерация примерки через Gemini API
"""
import logging
import asyncio
import os
from typing import List, Dict, Any
from datetime import datetime

from .image_client import ImageGenerationClient
from .prompts import (
    TRYON_SINGLE_ITEM,
    TRYON_FULL_OUTFIT,
)

logger = logging.getLogger(__name__)


async def generate_tryon(
    user_photo_source: str,
    product_photo_sources: List[str],
    api_key: str,
    base_url: str = "https://api.cometapi.com",
    model: str = "gemini-2.5-flash-image",
    timeout: float = 600.0,
    tryon_mode: str = "single_item",
    item_name: str = "одежда",
    category: str = "одежда"
) -> Dict[str, Any]:
    """
    Генерация примерки через Gemini API (CometAPI)

    Args:
        user_photo_source: URL или локальный путь к фото пользователя
        product_photo_sources: Список URL или локальных путей к фото товара (до 2 штук)
        api_key: API ключ для CometAPI
        base_url: Base URL API (по умолчанию https://api.cometapi.com)
        model: Модель для генерации:
            - "gemini-2.5-flash-image" - Nano Banana (быстро)
            - "gemini-3-pro-image" - Nano Banana Pro (дольше, качественнее)
        timeout: Таймаут в секундах
        tryon_mode: Режим примерки:
            - "single_item" - примерить ТОЛЬКО конкретный товар
            - "full_outfit" - примерить ВЕСЬ образ с референса
        item_name: Название товара (используется в режиме single_item)
        category: Категория товара (например, "ПИДЖАКИ", "ТРЕНЧКОТЫ")

    Returns:
        Dict с ключами: success, result/error
    """
    start_time = datetime.now()
    client = None

    try:
        # Ограничиваем до 2 фото товара (всего 3 с фото пользователя)
        product_sources = product_photo_sources[:2]

        # Собираем все источники: фото пользователя + фото товара
        all_image_sources = [user_photo_source] + product_sources

        logger.info(f"🎨 Starting try-on generation with {len(all_image_sources)} images (mode: {tryon_mode})")

        # Выбираем промпт в зависимости от режима
        if tryon_mode == "single_item":
            # Подставляем название товара и категорию в промпт
            prompt = TRYON_SINGLE_ITEM.format(category=category)
            logger.info(f"Using SINGLE_ITEM mode for: {category} - {item_name}")
        elif tryon_mode == "full_outfit":
            prompt = TRYON_FULL_OUTFIT
            logger.info("Using FULL_OUTFIT mode")
        else:
            raise ValueError(f"Unsupported tryon_mode: '{tryon_mode}'. Supported modes are 'single_item' and 'full_outfit'.")

        # Создаем клиент
        client = ImageGenerationClient(
            api_key=api_key,
            model=model,
            base_url=base_url,
            timeout=timeout
        )

        # Генерируем примерку
        result_data_uri = await client.process_images(all_image_sources, prompt)

        processing_time = (datetime.now() - start_time).total_seconds()

        logger.info(f"✅ Try-on generated successfully in {processing_time:.2f}s")

        return {
            "success": True,
            "result": {
                "photo_url": result_data_uri,
                "processing_time": int(processing_time)
            }
        }

    except asyncio.TimeoutError:
        processing_time = (datetime.now() - start_time).total_seconds()
        logger.error(f"❌ Try-on generation timeout after {processing_time:.2f}s")
        return {
            "success": False,
            "error": {
                "type": "timeout",
                "message": "Превышено время ожидания генерации"
            }
        }

    except Exception as e:
        processing_time = (datetime.now() - start_time).total_seconds()
        logger.error(f"❌ Try-on generation failed after {processing_time:.2f}s: {e}", exc_info=True)
        logger.error(f"Model used: {model}, Base URL: {base_url}")

        error_str = str(e).lower()
        if "timeout" in error_str:
            error_type = "timeout"
            message = "Превышено время ожидания генерации"
        elif "404" in error_str or "not found" in error_str or "no available channel" in error_str or "model_not_found" in error_str:
            error_type = "model_not_found"
            message = f"Модель '{model}' недоступна. Возможно, она не поддерживается в вашем тарифе CometAPI или название модели неверное. Попробуйте использовать модель 'Быстрая' или 'Качественная'."
        elif "remoteprotocol" in error_str or "server disconnected" in error_str or "all endpoints failed" in error_str or "connecterror" in error_str:
            error_type = "model_not_supported"
            message = f"Модель '{model}' недоступна в CometAPI. Возможно, она не поддерживается или недоступна в вашем тарифе. Попробуйте использовать модель 'Быстрая' или 'Качественная'."
        elif "api" in error_str or "network" in error_str or "http" in error_str:
            error_type = "api_error"
            message = "Ошибка при обращении к сервису генерации"
        else:
            error_type = "processing_error"
            message = f"Ошибка генерации: {str(e)}"

        return {
            "success": False,
            "error": {
                "type": error_type,
                "message": message
            }
        }

    finally:
        if client:
            await client.close()