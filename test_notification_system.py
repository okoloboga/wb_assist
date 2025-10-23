#!/usr/bin/env python3
"""
Тестовый скрипт для проверки системы уведомлений
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta

# Добавляем путь к проекту
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from server.app.core.database import get_db
from server.app.features.notifications.notification_service import NotificationService
from server.app.features.wb_api.sync_service import WBSyncService
from server.app.features.user.crud import get_user_by_telegram_id
from server.app.features.wb_api.crud import get_cabinet_by_user_id
from sqlalchemy.orm import Session

async def test_notification_system():
    """Тестирование системы уведомлений"""
    print("🧪 Запуск тестирования системы уведомлений...")
    
    # Получаем подключение к БД
    db = next(get_db())
    
    try:
        # Находим тестового пользователя
        user = get_user_by_telegram_id(db, 123456789)  # Замените на ваш telegram_id
        if not user:
            print("❌ Пользователь не найден. Создайте пользователя с telegram_id=123456789")
            return
        
        print(f"✅ Найден пользователь: {user.id} (telegram_id: {user.telegram_id})")
        
        # Находим кабинет пользователя
        cabinet = get_cabinet_by_user_id(db, user.id)
        if not cabinet:
            print("❌ Кабинет пользователя не найден")
            return
        
        print(f"✅ Найден кабинет: {cabinet.id}")
        
        # Создаем сервисы
        notification_service = NotificationService()
        sync_service = WBSyncService()
        
        # Тест 1: Проверяем настройки уведомлений
        print("\n📋 Тест 1: Проверка настроек уведомлений")
        settings = notification_service.get_user_notification_settings(db, user.id)
        print(f"   - Уведомления о заказах: {settings.notify_orders}")
        print(f"   - Уведомления о отзывах: {settings.notify_reviews}")
        print(f"   - Уведомления о остатках: {settings.notify_stocks}")
        print(f"   - Webhook URL: {user.bot_webhook_url}")
        
        # Тест 2: Симулируем синхронизацию
        print("\n🔄 Тест 2: Симуляция синхронизации")
        
        # Обновляем last_sync_at на 1 час назад
        cabinet.last_sync_at = datetime.utcnow() - timedelta(hours=1)
        db.commit()
        
        print(f"   - Обновлен last_sync_at на: {cabinet.last_sync_at}")
        
        # Тест 3: Создаем тестовые данные
        print("\n📊 Тест 3: Создание тестовых данных")
        
        # Здесь можно добавить создание тестовых заказов, отзывов, остатков
        # Для простоты тестируем только логику уведомлений
        
        # Тест 4: Запускаем обработку уведомлений
        print("\n📢 Тест 4: Обработка уведомлений")
        
        # Симулируем завершение синхронизации
        previous_sync_at = cabinet.last_sync_at
        cabinet.last_sync_at = datetime.utcnow()
        db.commit()
        
        # Запускаем обработку уведомлений
        result = await notification_service.process_sync_events(
            db, user.id, cabinet.id, previous_sync_at, cabinet.last_sync_at
        )
        
        print(f"   - Результат обработки: {result}")
        
        # Тест 5: Проверяем историю уведомлений
        print("\n📚 Тест 5: Проверка истории уведомлений")
        from server.app.features.notifications.models import NotificationHistory
        
        recent_notifications = db.query(NotificationHistory).filter(
            NotificationHistory.user_id == user.id,
            NotificationHistory.created_at > datetime.utcnow() - timedelta(minutes=5)
        ).all()
        
        print(f"   - Недавние уведомления: {len(recent_notifications)}")
        for notif in recent_notifications:
            print(f"     * {notif.event_type} в {notif.created_at}")
        
        print("\n✅ Тестирование завершено!")
        
    except Exception as e:
        print(f"❌ Ошибка при тестировании: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(test_notification_system())
