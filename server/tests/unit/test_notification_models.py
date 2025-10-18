"""
Тесты для моделей системы уведомлений S3
"""

import pytest
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.features.notifications.models import NotificationSettings, NotificationHistory, OrderStatusHistory


class TestNotificationSettings:
    """Тесты для модели NotificationSettings"""
    
    def test_create_notification_settings(self, db_session: Session):
        """Тест создания настроек уведомлений"""
        settings = NotificationSettings(
            user_id=123456789,
            notifications_enabled=True
        )
        
        db_session.add(settings)
        db_session.commit()
        db_session.refresh(settings)
        
        assert settings.id is not None
        assert settings.user_id == 123456789
        assert settings.notifications_enabled is True
        assert settings.new_orders_enabled is True  # default
        assert settings.order_buyouts_enabled is True  # default
        assert settings.grouping_enabled is True  # default
        assert settings.max_group_size == 5  # default
        assert settings.group_timeout == 300  # default
        assert settings.created_at is not None
        assert settings.updated_at is None
    
    def test_notification_settings_defaults(self, db_session: Session):
        """Тест значений по умолчанию для настроек"""
        settings = NotificationSettings(user_id=987654321)
        
        db_session.add(settings)
        db_session.commit()
        db_session.refresh(settings)
        
        # Проверяем все значения по умолчанию
        assert settings.notifications_enabled is True
        assert settings.new_orders_enabled is True
        assert settings.order_buyouts_enabled is True
        assert settings.order_cancellations_enabled is True
        assert settings.order_returns_enabled is True
        assert settings.negative_reviews_enabled is True
        assert settings.critical_stocks_enabled is True
        
        # Группировка по умолчанию
        assert settings.grouping_enabled is True
        assert settings.max_group_size == 5
        assert settings.group_timeout == 300
    
    def test_notification_settings_repr(self, db_session: Session):
        """Тест строкового представления модели"""
        settings = NotificationSettings(user_id=111222333)
        
        db_session.add(settings)
        db_session.commit()
        db_session.refresh(settings)
        
        repr_str = repr(settings)
        assert "NotificationSettings" in repr_str
        assert str(settings.id) in repr_str
        assert "User 111222333" in repr_str


class TestNotificationHistory:
    """Тесты для модели NotificationHistory"""
    
    def test_create_notification_history(self, db_session: Session):
        """Тест создания записи в истории уведомлений"""
        history = NotificationHistory(
            id="notif_12345",
            user_id=123456789,
            notification_type="new_order",
            priority="HIGH",
            title="Новый заказ #123",
            content="Детали заказа...",
            sent_at=datetime.now(timezone.utc),
            status="delivered"
        )
        
        db_session.add(history)
        db_session.commit()
        db_session.refresh(history)
        
        assert history.id == "notif_12345"
        assert history.user_id == 123456789
        assert history.notification_type == "new_order"
        assert history.priority == "HIGH"
        assert history.title == "Новый заказ #123"
        assert history.content == "Детали заказа..."
        assert history.status == "delivered"
        assert history.retry_count == 0  # default
        assert history.error_message is None  # default
        assert history.created_at is not None
    
    def test_notification_history_defaults(self, db_session: Session):
        """Тест значений по умолчанию для истории"""
        history = NotificationHistory(
            id="notif_67890",
            user_id=987654321,
            notification_type="order_buyout",
            priority="HIGH",
            title="Заказ выкуплен",
            content="Заказ #456 выкуплен",
            sent_at=datetime.now(timezone.utc)
        )
        
        db_session.add(history)
        db_session.commit()
        db_session.refresh(history)
        
        assert history.status == "pending"  # default
        assert history.retry_count == 0  # default
        assert history.error_message is None  # default
        assert history.delivery_time is None  # default
    
    def test_notification_history_repr(self, db_session: Session):
        """Тест строкового представления модели"""
        history = NotificationHistory(
            id="notif_99999",
            user_id=555666777,
            notification_type="critical_stocks",
            priority="HIGH",
            title="Критичные остатки",
            content="Товары заканчиваются",
            sent_at=datetime.now(timezone.utc)
        )
        
        db_session.add(history)
        db_session.commit()
        db_session.refresh(history)
        
        repr_str = repr(history)
        assert "NotificationHistory" in repr_str
        assert "notif_99999" in repr_str
        assert "critical_stocks" in repr_str


class TestOrderStatusHistory:
    """Тесты для модели OrderStatusHistory"""
    
    def test_create_order_status_history(self, db_session: Session):
        """Тест создания записи об изменении статуса заказа"""
        status_history = OrderStatusHistory(
            user_id=123456789,
            order_id=98765,
            previous_status="active",
            current_status="buyout",
            changed_at=datetime.now(timezone.utc),
            notification_sent=True
        )
        
        db_session.add(status_history)
        db_session.commit()
        db_session.refresh(status_history)
        
        assert status_history.id is not None
        assert status_history.user_id == 123456789
        assert status_history.order_id == 98765
        assert status_history.previous_status == "active"
        assert status_history.current_status == "buyout"
        assert status_history.notification_sent is True
        assert status_history.created_at is not None
    
    def test_order_status_history_defaults(self, db_session: Session):
        """Тест значений по умолчанию для истории статуса"""
        status_history = OrderStatusHistory(
            user_id=987654321,
            order_id=54321,
            current_status="cancelled",
            changed_at=datetime.now(timezone.utc)
        )
        
        db_session.add(status_history)
        db_session.commit()
        db_session.refresh(status_history)
        
        assert status_history.notification_sent is False  # default
        assert status_history.created_at is not None
    
    def test_order_status_history_repr(self, db_session: Session):
        """Тест строкового представления модели"""
        status_history = OrderStatusHistory(
            user_id=111222333,
            order_id=77788,
            current_status="return",
            changed_at=datetime.now(timezone.utc)
        )
        
        db_session.add(status_history)
        db_session.commit()
        db_session.refresh(status_history)
        
        repr_str = repr(status_history)
        assert "OrderStatusHistory" in repr_str
        assert str(status_history.id) in repr_str
        assert "Order 77788" in repr_str
