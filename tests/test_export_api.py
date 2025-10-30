#!/usr/bin/env python3
"""
Тестовый скрипт для проверки API экспорта Google Sheets
"""

import asyncio
import aiohttp
import json

async def test_export_api():
    """Тестирует API эндпоинты экспорта"""
    base_url = "http://localhost:8000"
    
    async with aiohttp.ClientSession() as session:
        print("🧪 Тестирование API экспорта Google Sheets...")
        
        # Тест 1: Проверка здоровья сервиса
        print("\n1️⃣ Тест здоровья сервиса экспорта...")
        try:
            async with session.get(f"{base_url}/api/export/health") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print(f"✅ Сервис экспорта работает: {data}")
                else:
                    print(f"❌ Ошибка здоровья сервиса: {resp.status}")
        except Exception as e:
            print(f"❌ Ошибка подключения: {e}")
            return
        
        # Тест 2: Получение интервала синхронизации
        print("\n2️⃣ Тест получения интервала синхронизации...")
        try:
            async with session.get(f"{base_url}/api/export/sync-interval") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print(f"✅ Интервал синхронизации: {data}")
                else:
                    print(f"❌ Ошибка получения интервала: {resp.status}")
        except Exception as e:
            print(f"❌ Ошибка: {e}")
        
        # Тест 3: Создание токена экспорта (требует валидный cabinet_id)
        print("\n3️⃣ Тест создания токена экспорта...")
        try:
            token_data = {
                "user_id": 123456789,
                "cabinet_id": 1  # Замените на реальный ID кабинета
            }
            async with session.post(
                f"{base_url}/api/export/token",
                json=token_data
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print(f"✅ Токен создан: {data['token'][:20]}...")
                else:
                    error_data = await resp.json()
                    print(f"❌ Ошибка создания токена: {resp.status} - {error_data}")
        except Exception as e:
            print(f"❌ Ошибка: {e}")
        
        # Тест 4: Создание шаблона Google Sheets
        print("\n4️⃣ Тест создания шаблона Google Sheets...")
        try:
            async with session.post(
                f"{base_url}/api/export/template/create",
                params={"template_name": "Тестовый шаблон"}
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print(f"✅ Шаблон создан: {data['template_url']}")
                else:
                    error_data = await resp.json()
                    print(f"❌ Ошибка создания шаблона: {resp.status} - {error_data}")
        except Exception as e:
            print(f"❌ Ошибка: {e}")
        
        print("\n🎉 Тестирование завершено!")

if __name__ == "__main__":
    asyncio.run(test_export_api())
