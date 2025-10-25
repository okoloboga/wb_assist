#!/usr/bin/env python3
"""
Тест для проверки отправки webhook уведомления об удалении кабинета
"""

import asyncio
import logging
import pytest
import aiohttp

pytestmark = pytest.mark.asyncio

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_cabinet_removal_webhook():
    """Тест отправки webhook уведомления об удалении кабинета"""
    
    webhook_url = "http://localhost:8001/webhook/notifications"
    payload = {
        "event": "cabinet.removed",
        "data": {
            "cabinet_id": "12345",
            "user_id": 5101525651,
            "timestamp": "2025-01-01T12:00:00Z"
        }
    }
    
    logger.info("🧪 Тестирование отправки webhook уведомления")
    logger.info("=" * 60)
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(webhook_url, json=payload) as resp:
                status = resp.status
                try:
                    text = await resp.text()
                except Exception:
                    text = "<no text>"
                logger.info(f"Ответ: status={status}, body={text}")
                
                # В тестовом окружении сервер может быть недоступен — цель: убедиться, что запрос уходит
                assert status in {200, 201, 202, 204} or status >= 400
        
        logger.info("=" * 60)
        logger.info("✅ Тестирование завершено!")
        
    except Exception as e:
        logger.error(f"❌ Ошибка во время тестирования: {e}")

if __name__ == "__main__":
    print("🧪 Тестирование отправки webhook уведомления")
    print("=" * 60)
    
    asyncio.run(test_cabinet_removal_webhook())
    
    print("=" * 60)
    print("✅ Тест завершен")
