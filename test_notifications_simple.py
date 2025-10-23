#!/usr/bin/env python3
"""
Простой скрипт для тестирования уведомлений
"""

import requests
import json
import sys

def test_notifications():
    """Тестирование уведомлений через API"""
    
    # Настройки
    BASE_URL = "http://localhost:8000"  # Замените на ваш URL
    TELEGRAM_ID = 123456789  # Замените на ваш telegram_id
    
    print("🧪 Тестирование системы уведомлений...")
    print(f"📡 URL: {BASE_URL}")
    print(f"👤 Telegram ID: {TELEGRAM_ID}")
    
    # Тест 1: Проверка доступности API
    print("\n1️⃣ Проверка доступности API...")
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            print("✅ API доступен")
        else:
            print(f"❌ API недоступен: {response.status_code}")
            return
    except Exception as e:
        print(f"❌ Ошибка подключения: {e}")
        return
    
    # Тест 2: Запуск обработки событий синхронизации
    print("\n2️⃣ Запуск обработки событий синхронизации...")
    try:
        response = requests.post(
            f"{BASE_URL}/notifications/test/trigger-sync-events",
            params={"telegram_id": TELEGRAM_ID}
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Результат: {result}")
            
            if result.get("success"):
                events_result = result.get("result", {})
                print(f"   - События обработаны: {events_result.get('events_processed', 0)}")
                print(f"   - Уведомления отправлены: {events_result.get('notifications_sent', 0)}")
                print(f"   - События: {events_result.get('events', [])}")
            else:
                print(f"❌ Ошибка: {result.get('message')}")
        else:
            print(f"❌ HTTP ошибка: {response.status_code}")
            print(f"   Ответ: {response.text}")
            
    except Exception as e:
        print(f"❌ Ошибка запроса: {e}")
    
    # Тест 3: Отправка тестового уведомления
    print("\n3️⃣ Отправка тестового уведомления...")
    try:
        test_data = {
            "notification_type": "test",
            "test_data": {
                "message": "Тестовое уведомление",
                "timestamp": "2024-01-01T12:00:00Z"
            }
        }
        
        response = requests.post(
            f"{BASE_URL}/notifications/test/test",
            params={"telegram_id": TELEGRAM_ID},
            json=test_data
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Результат: {result}")
            
            if result.get("success"):
                print(f"   - Уведомление отправлено: {result.get('notification_sent')}")
                print(f"   - Webhook URL: {result.get('webhook_url')}")
            else:
                print(f"❌ Ошибка: {result.get('message')}")
        else:
            print(f"❌ HTTP ошибка: {response.status_code}")
            print(f"   Ответ: {response.text}")
            
    except Exception as e:
        print(f"❌ Ошибка запроса: {e}")
    
    print("\n✅ Тестирование завершено!")

if __name__ == "__main__":
    test_notifications()
