#!/usr/bin/env python3
"""
Скрипт для ручного тестирования функционала get_prices
"""

import os
import sys
import json
from datetime import datetime

# Добавляем путь к модулям
sys.path.append(os.path.join(os.path.dirname(__file__), 'wb_api'))

from wb_api.client import WildberriesAPI

def test_get_prices_manual():
    """Ручное тестирование метода get_prices"""
    
    print("🧪 Ручное тестирование метода get_prices")
    print("=" * 50)
    
    # Создаем клиент
    client = WildberriesAPI()
    
    print(f"📋 API Key: {'✅ Установлен' if client.api_key else '❌ Не установлен'}")
    print(f"🌐 Base URL: {client.base_url}")
    print(f"⏰ Время запуска: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    try:
        print("🔄 Выполняем запрос get_prices()...")
        prices = client.get_prices()
        
        print(f"✅ Запрос выполнен успешно!")
        print(f"📊 Получено записей: {len(prices)}")
        
        if prices:
            print("\n📋 Первые 3 записи:")
            for i, price in enumerate(prices[:3]):
                print(f"  {i+1}. {json.dumps(price, indent=4, ensure_ascii=False)}")
        else:
            print("📭 Данные отсутствуют (пустой список)")
            
    except Exception as e:
        print(f"❌ Ошибка при выполнении запроса: {e}")
        print(f"🔍 Тип ошибки: {type(e).__name__}")
    
    print("\n" + "=" * 50)
    print("🏁 Тестирование завершено")

def test_with_different_scenarios():
    """Тестирование различных сценариев"""
    
    print("\n🎯 Тестирование различных сценариов")
    print("=" * 50)
    
    # Тест 1: Проверка заголовков
    client = WildberriesAPI()
    print(f"🔑 Заголовки запроса:")
    for key, value in client.headers.items():
        if key == 'Authorization':
            print(f"  {key}: {'***скрыто***' if value else 'None'}")
        else:
            print(f"  {key}: {value}")
    
    # Тест 2: Проверка URL
    expected_url = "https://discounts-prices-api.wildberries.ru/api/v1/list/goods/filter"
    print(f"\n🌐 URL для запроса цен:")
    print(f"  {expected_url}")
    
    # Тест 3: Симуляция ошибки сети (для демонстрации)
    print(f"\n⚠️  Примечание: Если API ключ не настроен или неверный,")
    print(f"   метод вернет пустой список [] и запишет ошибку в лог")

if __name__ == "__main__":
    # Основное тестирование
    test_get_prices_manual()
    
    # Дополнительные сценарии
    test_with_different_scenarios()
    
    print(f"\n💡 Советы по тестированию:")
    print(f"   1. Установите реальный API ключ в .env файле")
    print(f"   2. Проверьте логи на наличие ошибок")
    print(f"   3. Используйте pytest для автоматических тестов")
    print(f"   4. Мокируйте API для unit-тестов")