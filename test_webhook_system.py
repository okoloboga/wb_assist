#!/usr/bin/env python3
"""
Простой тест webhook системы
"""
import asyncio
import json
import aiohttp
from datetime import datetime

# Тестовые данные
TEST_WEBHOOK_URL = "http://localhost:8000/api/v1/notifications/test"
TEST_USER_ID = 5101525651  # Ваш telegram_id

async def test_webhook_system():
    """Тестирование webhook системы"""
    print("🧪 Тестирование webhook системы...")
    
    # Тестовые данные для уведомления
    test_data = {
        "notification_type": "new_order",
        "test_data": {
            "order_id": "TEST_12345",
            "product_name": "Тестовый товар",
            "amount": 1500,
            "brand": "Тестовый бренд"
        }
    }
    
    headers = {
        "Content-Type": "application/json",
        "X-API-SECRET-KEY": "CnWvwoDwwGKh"  # Ваш API ключ
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            # Отправляем тестовое уведомление
            print(f"📤 Отправка тестового уведомления для пользователя {TEST_USER_ID}...")
            
            async with session.post(
                TEST_WEBHOOK_URL,
                json=test_data,
                headers=headers,
                params={"telegram_id": TEST_USER_ID}
            ) as response:
                
                if response.status == 200:
                    result = await response.json()
                    print("✅ Тестовое уведомление отправлено успешно!")
                    print(f"📊 Результат: {json.dumps(result, indent=2, ensure_ascii=False)}")
                    
                    if result.get("success"):
                        print("🎉 Webhook система работает корректно!")
                    else:
                        print(f"❌ Ошибка: {result.get('error', 'Unknown error')}")
                else:
                    error_text = await response.text()
                    print(f"❌ HTTP {response.status}: {error_text}")
                    
    except Exception as e:
        print(f"❌ Ошибка при тестировании: {e}")

async def test_user_webhook_setup():
    """Тестирование настройки webhook для пользователя"""
    print("\n🔗 Тестирование настройки webhook...")
    
    webhook_data = {
        "bot_webhook_url": "https://your-bot-domain.com/webhook/notifications"
    }
    
    headers = {
        "Content-Type": "application/json",
        "X-API-SECRET-KEY": "CnWvwoDwwGKh"
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"http://localhost:8000/users/webhook",
                json=webhook_data,
                headers=headers,
                params={"telegram_id": TEST_USER_ID}
            ) as response:
                
                if response.status == 200:
                    result = await response.json()
                    print("✅ Webhook URL настроен успешно!")
                    print(f"📊 Результат: {json.dumps(result, indent=2, ensure_ascii=False)}")
                else:
                    error_text = await response.text()
                    print(f"❌ HTTP {response.status}: {error_text}")
                    
    except Exception as e:
        print(f"❌ Ошибка при настройке webhook: {e}")

async def main():
    """Главная функция тестирования"""
    print("🚀 Запуск тестов webhook системы")
    print("=" * 50)
    
    # Тест 1: Настройка webhook
    await test_user_webhook_setup()
    
    # Тест 2: Отправка тестового уведомления
    await test_webhook_system()
    
    print("\n" + "=" * 50)
    print("🏁 Тестирование завершено")

if __name__ == "__main__":
    asyncio.run(main())
