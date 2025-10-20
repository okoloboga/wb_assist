"""
Тесты для CRUD операций системы уведомлений S3
"""

import pytest
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from typing import List, Optional

from app.features.notifications.models import NotificationSettings, NotificationHistory, OrderStatusHistory
from app.features.notifications.crud import (
    NotificationSettingsCRUD,
    NotificationHistoryCRUD,
    OrderStatusHistoryCRUD
)


class TestNotificationSettingsCRUD:
    """Тесты для CRUD операций с настройками уведомлений"""
    
    def test_get_user_settings_existing(self, db_session: Session):
        """Тест получения существующих настроек пользователя"""
        # Создаем настройки для пользователя
        settings = NotificationSettings(
            user_id=123456789,
            notifications_enabled=True,
            new_orders_enabled=False
        )
        db_session.add(settings)
        db_session.commit()
        
        # Получаем настройки через CRUD
        crud = NotificationSettingsCRUD()
        result = crud.get_user_settings(db_session, 123456789)
        
        assert result is not None
        assert result.user_id == 123456789
        assert result.notifications_enabled is True
        assert result.new_orders_enabled is False
    
    def test_get_user_settings_not_existing(self, db_session: Session):
        """Тест получения настроек несуществующего пользователя"""
        crud = NotificationSettingsCRUD()
        result = crud.get_user_settings(db_session, 999999999)
        
        assert result is None
    
    def test_create_default_settings(self, db_session: Session):
        """Тест создания настроек по умолчанию"""
        crud = NotificationSettingsCRUD()
        result = crud.create_default_settings(db_session, 987654321)
        
        assert result is not None
        assert result.user_id == 987654321
        assert result.notifications_enabled is True  # default
        assert result.new_orders_enabled is True  # default
        assert result.order_buyouts_enabled is True  # default
    
    def test_update_settings(self, db_session: Session):
        """Тест обновления настроек пользователя"""
        # Создаем начальные настройки
        settings = NotificationSettings(user_id=111222333)
        db_session.add(settings)
        db_session.commit()
        
        # Обновляем настройки
        update_data = {
            "notifications_enabled": False,
            "new_orders_enabled": False,
            "negative_reviews_enabled": False
        }
        
        crud = NotificationSettingsCRUD()
        result = crud.update_settings(db_session, 111222333, update_data)
        
        assert result is not None
        assert result.notifications_enabled is False
        assert result.new_orders_enabled is False
        assert result.negative_reviews_enabled is False


class TestNotificationHistoryCRUD:
    """Тесты для CRUD операций с историей уведомлений"""
    
    def test_create_notification(self, db_session: Session):
        """Тест создания записи уведомления"""
        notification_data = {
            "id": "notif_test_123",
            "user_id": 123456789,
            "notification_type": "new_order",
            "priority": "HIGH",
            "title": "Новый заказ #123",
            "content": "Детали заказа...",
            "sent_at": datetime.now(timezone.utc)
        }
        
        crud = NotificationHistoryCRUD()
        result = crud.create_notification(db_session, notification_data)
        
        assert result is not None
        assert result.id == "notif_test_123"
        assert result.user_id == 123456789
        assert result.notification_type == "new_order"
        assert result.status == "pending"  # default
        assert result.retry_count == 0  # default
    
    def test_update_delivery_status(self, db_session: Session):
        """Тест обновления статуса доставки"""
        # Создаем уведомление
        notification = NotificationHistory(
            id="notif_update_456",
            user_id=987654321,
            notification_type="order_buyout",
            priority="HIGH",
            title="Заказ выкуплен",
            content="Заказ #456 выкуплен",
            sent_at=datetime.now(timezone.utc)
        )
        db_session.add(notification)
        db_session.commit()
        
        # Обновляем статус
        crud = NotificationHistoryCRUD()
        result = crud.update_delivery_status(
            db_session, 
            "notif_update_456", 
            "delivered"
        )
        
        assert result is True
        
        # Проверяем, что статус обновился
        updated_notification = db_session.query(NotificationHistory).filter(
            NotificationHistory.id == "notif_update_456"
        ).first()
        
        assert updated_notification.status == "delivered"
        assert updated_notification.delivery_time is not None
    
    def test_get_user_history(self, db_session: Session):
        """Тест получения истории уведомлений пользователя"""
        # Создаем несколько уведомлений
        notifications = [
            NotificationHistory(
                id=f"notif_history_{i}",
                user_id=555666777,
                notification_type="new_order",
                priority="HIGH",
                title=f"Уведомление {i}",
                content=f"Содержимое {i}",
                sent_at=datetime.now(timezone.utc)
            ) for i in range(3)
        ]
        
        for notification in notifications:
            db_session.add(notification)
        db_session.commit()
        
        # Получаем историю
        crud = NotificationHistoryCRUD()
        result = crud.get_user_history(db_session, 555666777, {})
        
        assert len(result) == 3
        assert all(n.user_id == 555666777 for n in result)
        assert all(n.notification_type == "new_order" for n in result)
    
    def test_get_user_history_with_filters(self, db_session: Session):
        """Тест получения истории с фильтрами"""
        # Создаем уведомления разных типов
        notifications = [
            NotificationHistory(
                id=f"notif_filter_{i}",
                user_id=777888999,
                notification_type="new_order" if i % 2 == 0 else "order_buyout",
                priority="HIGH",
                title=f"Уведомление {i}",
                content=f"Содержимое {i}",
                sent_at=datetime.now(timezone.utc)
            ) for i in range(4)
        ]
        
        for notification in notifications:
            db_session.add(notification)
        db_session.commit()
        
        # Фильтруем по типу
        crud = NotificationHistoryCRUD()
        result = crud.get_user_history(
            db_session, 
            777888999, 
            {"type": "new_order"}
        )
        
        assert len(result) == 2
        assert all(n.notification_type == "new_order" for n in result)


class TestOrderStatusHistoryCRUD:
    """Тесты для CRUD операций с историей статуса заказов"""
    
    def test_track_status_change(self, db_session: Session):
        """Тест отслеживания изменения статуса заказа"""
        crud = OrderStatusHistoryCRUD()
        result = crud.track_status_change(
            db_session,
            123456789,
            98765,
            "active",
            "buyout"
        )
        
        assert result is not None
        assert result.user_id == 123456789
        assert result.order_id == 98765
        assert result.previous_status == "active"
        assert result.current_status == "buyout"
        assert result.notification_sent is False  # default
    
    def test_prevent_duplicate_notifications(self, db_session: Session):
        """Тест предотвращения дубликатов уведомлений"""
        # Создаем первое изменение статуса
        crud = OrderStatusHistoryCRUD()
        first_change = crud.track_status_change(
            db_session,
            111222333,
            54321,
            "active",
            "buyout"
        )
        
        # Пытаемся создать дубликат
        duplicate_change = crud.track_status_change(
            db_session,
            111222333,
            54321,
            "active",
            "buyout"
        )
        
        # Должен вернуть существующую запись
        assert duplicate_change is not None
        assert duplicate_change.id == first_change.id
    
    def test_get_pending_changes(self, db_session: Session):
        """Тест получения ожидающих изменений"""
        # Создаем несколько изменений статуса
        changes = [
            OrderStatusHistory(
                user_id=444555666,
                order_id=11111,
                previous_status="active",
                current_status="buyout",
                changed_at=datetime.now(timezone.utc),
                notification_sent=False
            ),
            OrderStatusHistory(
                user_id=444555666,
                order_id=22222,
                previous_status="active",
                current_status="cancelled",
                changed_at=datetime.now(timezone.utc),
                notification_sent=True  # уже отправлено
            ),
            OrderStatusHistory(
                user_id=444555666,
                order_id=33333,
                previous_status="buyout",
                current_status="return",
                changed_at=datetime.now(timezone.utc),
                notification_sent=False
            )
        ]
        
        for change in changes:
            db_session.add(change)
        db_session.commit()
        
        # Получаем ожидающие изменения
        crud = OrderStatusHistoryCRUD()
        result = crud.get_pending_changes(db_session, 444555666)
        
        assert len(result) == 2
        assert all(not change.notification_sent for change in result)
        assert any(change.order_id == 11111 for change in result)
        assert any(change.order_id == 33333 for change in result)
