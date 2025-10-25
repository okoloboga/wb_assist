#!/usr/bin/env python3
"""
Тест для проверки новых методов API клиента
"""

import asyncio
import logging
import os
import pytest

# Устанавливаем тестовый секрет до импорта клиента
os.environ.setdefault("API_SECRET_KEY", "test_secret")

from api.client import BotAPIClient

# Инициализируем клиент
bot_api_client = BotAPIClient()

pytestmark = pytest.mark.asyncio

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_new_api_methods():
    """Тест новых методов API клиента"""
    
    test_user_id = 5101525651  # Замените на реальный Telegram ID для тестирования
    
    logger.info("🧪 Тестирование новых методов API клиента")
    logger.info("=" * 60)
    
    try:
        # 1. Тест статистики заказов
        logger.info("1️⃣ Тестирование get_orders_statistics...")
        response = await bot_api_client.get_orders_statistics(user_id=test_user_id)
        logger.info(f"   Результат: success={response.success}, status_code={response.status_code}")
        if response.error:
            logger.error(f"   Ошибка: {response.error}")
        
        # 2. Тест продаж
        logger.info("2️⃣ Тестирование get_recent_sales...")
        response = await bot_api_client.get_recent_sales(user_id=test_user_id, limit=5)
        logger.info(f"   Результат: success={response.success}, status_code={response.status_code}")
        if response.error:
            logger.error(f"   Ошибка: {response.error}")
        
        # 3. Тест выкупов
        logger.info("3️⃣ Тестирование get_buyouts...")
        response = await bot_api_client.get_buyouts(user_id=test_user_id, limit=5)
        logger.info(f"   Результат: success={response.success}, status_code={response.status_code}")
        if response.error:
            logger.error(f"   Ошибка: {response.error}")
        
        # 4. Тест возвратов
        logger.info("4️⃣ Тестирование get_returns...")
        response = await bot_api_client.get_returns(user_id=test_user_id, limit=5)
        logger.info(f"   Результат: success={response.success}, status_code={response.status_code}")
        if response.error:
            logger.error(f"   Ошибка: {response.error}")
        
        # 5. Тест статистики продаж
        logger.info("5️⃣ Тестирование get_sales_statistics...")
        response = await bot_api_client.get_sales_statistics(user_id=test_user_id)
        logger.info(f"   Результат: success={response.success}, status_code={response.status_code}")
        if response.error:
            logger.error(f"   Ошибка: {response.error}")
        
        # 6. Тест кабинетов пользователя
        logger.info("6️⃣ Тестирование get_user_cabinets...")
        response = await bot_api_client.get_user_cabinets(user_id=test_user_id)
        logger.info(f"   Результат: success={response.success}, status_code={response.status_code}")
        if response.error:
            logger.error(f"   Ошибка: {response.error}")
        
        # 7. Тест валидации кабинетов
        logger.info("7️⃣ Тестирование validate_all_cabinets...")
        response = await bot_api_client.validate_all_cabinets()
        logger.info(f"   Результат: success={response.success}, status_code={response.status_code}")
        if response.error:
            logger.error(f"   Ошибка: {response.error}")
        
        # 8. Тест фильтрации заказов
        logger.info("8️⃣ Тестирование get_recent_orders с фильтрацией...")
        response = await bot_api_client.get_recent_orders(user_id=test_user_id, status="active")
        logger.info(f"   Результат: success={response.success}, status_code={response.status_code}")
        if response.error:
            logger.error(f"   Ошибка: {response.error}")
        
        # 9. Тест deprecated методов
        logger.info("9️⃣ Тестирование deprecated методов...")
        response = await bot_api_client.get_cabinet_status(user_id=test_user_id)
        logger.info(f"   get_cabinet_status: success={response.success}, status_code={response.status_code}")
        
        response = await bot_api_client.connect_wb_cabinet(user_id=test_user_id, api_key="test_key")
        logger.info(f"   connect_wb_cabinet: success={response.success}, status_code={response.status_code}")
        
        logger.info("=" * 60)
        logger.info("✅ Тестирование завершено!")
        
    except Exception as e:
        logger.error(f"❌ Ошибка во время тестирования: {e}")

if __name__ == "__main__":
    print("🧪 Тестирование новых методов API клиента")
    print("=" * 60)
    
    # Запускаем тест
    asyncio.run(test_new_api_methods())
    
    print("=" * 60)
    print("✅ Тест завершен")
