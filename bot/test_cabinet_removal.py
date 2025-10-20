#!/usr/bin/env python3
"""
Тест для проверки обработки уведомлений об удалении кабинетов
"""

import asyncio
import json
import aiohttp
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_cabinet_removal_webhook():
    """Тест отправки webhook уведомления об удалении кабинета"""
    
    # Данные для тестирования
    webhook_data = {
        "type": "cabinet_removal",
        "telegram_id": 5101525651,  # Замените на реальный Telegram ID для тестирования
        "timestamp": "2025-10-19T11:15:19.325Z",
        "data": {
            "cabinet_id": 5,
            "cabinet_name": "Test Webhook Cabinet",
            "user_id": 1,
            "telegram_id": 5101525651,
            "validation_error": {
                "valid": False,
                "message": "API validation error: Invalid API key",
                "status_code": None
            },
            "removal_reason": "API key invalid or withdrawn",
            "removal_timestamp": "2025-10-19T11:15:19.325Z"
        }
    }
    
    webhook_url = "http://localhost:8001/webhook/notifications"
    
    logger.info("🧪 Тестирование webhook уведомления об удалении кабинета")
    logger.info(f"📤 URL: {webhook_url}")
    logger.info(f"📋 Данные: {json.dumps(webhook_data, indent=2, ensure_ascii=False)}")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                webhook_url,
                json=webhook_data,
                headers={"Content-Type": "application/json"}
            ) as response:
                
                logger.info(f"📤 Отправлен webhook: {webhook_data['type']}")
                logger.info(f"📊 Статус ответа: {response.status}")
                
                response_text = await response.text()
                logger.info(f"📋 Ответ сервера: {response_text}")
                
                if response.status == 200:
                    logger.info("✅ Webhook успешно обработан!")
                else:
                    logger.error(f"❌ Ошибка обработки webhook: {response.status}")
                    
    except Exception as e:
        logger.error(f"❌ Ошибка отправки webhook: {e}")

if __name__ == "__main__":
    print("🧪 Тестирование webhook уведомления об удалении кабинета")
    print("=" * 60)
    
    # Запускаем тест
    asyncio.run(test_cabinet_removal_webhook())
    
    print("=" * 60)
    print("✅ Тест завершен")
