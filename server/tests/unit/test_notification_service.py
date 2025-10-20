"""
Тесты для Notification Service системы уведомлений S3
"""

import pytest
from datetime import datetime, timezone
from typing import List, Dict, Any
from unittest.mock import Mock, AsyncMock, patch

from app.features.notifications.notification_service import NotificationService


class TestNotificationService:
    """Тесты для Notification Service"""
    
    def test_notification_service_initialization(self, db_session):
        """Тест инициализации Notification Service"""
        service = NotificationService(db_session)
        
        assert service.db == db_session
        assert service.event_detector is not None
        assert service.status_monitor is not None
        assert service.notification_generator is not None
        assert service.webhook_sender is not None
        assert service.message_formatter is not None
        assert service.settings_crud is not None
        assert service.history_crud is not None
        assert service.order_crud is not None
    
    @pytest.mark.asyncio
    async def test_process_sync_events_disabled_notifications(self, db_session):
        """Тест обработки событий при отключенных уведомлениях"""
        service = NotificationService(db_session)
        
        # Создаем пользователя с отключенными уведомлениями
        from app.features.user.models import User
        user = User(
            telegram_id=123456789, 
            username="test_user",
            first_name="Test",
            last_name="User"
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        
        # Создаем настройки с отключенными уведомлениями
        settings = service.settings_crud.create_default_settings(db_session, user.id)
        service.settings_crud.update_settings(db_session, user.id, {
            "notifications_enabled": False
        })
        
        # Обрабатываем события
        result = await service.process_sync_events(
            user_id=user.id,
            cabinet_id=1,
            current_orders=[{"order_id": 1, "status": "active", "amount": 1000}],
            previous_orders=[],
            bot_webhook_url="http://test.com/webhook"
        )
        
        assert result["status"] == "disabled"
        assert result["notifications_sent"] == 0
    
    @pytest.mark.asyncio
    async def test_process_sync_events_new_orders(self, db_session):
        """Тест обработки событий новых заказов"""
        service = NotificationService(db_session)
        
        # Создаем пользователя
        from app.features.user.models import User
        user = User(
            telegram_id=987654321, 
            username="test_user_2",
            first_name="Test2",
            last_name="User2"
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        
        # Создаем настройки
        settings = service.settings_crud.create_default_settings(db_session, user.id)
        
        # Мокаем webhook отправку
        with patch.object(service.webhook_sender, 'send_new_order_notification') as mock_send:
            mock_send.return_value = {"success": True, "attempts": 1}
            
            result = await service.process_sync_events(
                user_id=user.id,
                cabinet_id=1,
                current_orders=[
                    {"order_id": 1, "status": "active", "amount": 1000, "product_name": "Товар 1"}
                ],
                previous_orders=[],
                bot_webhook_url="http://test.com/webhook"
            )
        
        assert result["status"] == "success"
        assert result["notifications_sent"] == 1
        assert len(result["events"]) == 1
        assert result["events"][0]["type"] == "new_order"
    
    @pytest.mark.asyncio
    async def test_process_sync_events_status_changes(self, db_session):
        """Тест обработки событий изменения статуса заказов"""
        service = NotificationService(db_session)
        
        # Создаем пользователя
        from app.features.user.models import User
        user = User(
            telegram_id=555666777, 
            username="test_user_3",
            first_name="Test3",
            last_name="User3"
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        
        # Создаем настройки
        settings = service.settings_crud.create_default_settings(db_session, user.id)
        
        # Предыдущие заказы
        previous_orders = [
            {"order_id": 1, "status": "active", "amount": 1000, "product_name": "Товар 1"}
        ]
        
        # Текущие заказы (статус изменился)
        current_orders = [
            {"order_id": 1, "status": "buyout", "amount": 1000, "product_name": "Товар 1"}
        ]
        
        # Мокаем webhook отправку
        with patch.object(service, '_send_generic_webhook_notification') as mock_send:
            mock_send.return_value = {"success": True, "attempts": 1}
            
            result = await service.process_sync_events(
                user_id=user.id,
                cabinet_id=1,
                current_orders=current_orders,
                previous_orders=previous_orders,
                bot_webhook_url="http://test.com/webhook"
            )
        
        assert result["status"] == "success"
        assert result["notifications_sent"] == 1
        assert len(result["events"]) == 1
        assert result["events"][0]["type"] == "order_buyout"
    
    @pytest.mark.asyncio
    async def test_process_sync_events_negative_reviews(self, db_session):
        """Тест обработки событий негативных отзывов"""
        service = NotificationService(db_session)
        
        # Создаем пользователя
        from app.features.user.models import User
        user = User(
            telegram_id=111222333, 
            username="test_user_4",
            first_name="Test4",
            last_name="User4"
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        
        # Создаем настройки
        settings = service.settings_crud.create_default_settings(db_session, user.id)
        
        # Предыдущие отзывы
        previous_reviews = [
            {"id": 1, "rating": 5, "text": "Отлично!", "product_name": "Товар 1"}
        ]
        
        # Текущие отзывы (добавился негативный)
        current_reviews = [
            {"id": 1, "rating": 5, "text": "Отлично!", "product_name": "Товар 1"},
            {"id": 2, "rating": 2, "text": "Плохо", "product_name": "Товар 2"}
        ]
        
        # Мокаем webhook отправку
        with patch.object(service, '_send_generic_webhook_notification') as mock_send:
            mock_send.return_value = {"success": True, "attempts": 1}
            
            result = await service.process_sync_events(
                user_id=user.id,
                cabinet_id=1,
                current_orders=[],
                previous_orders=[],
                current_reviews=current_reviews,
                previous_reviews=previous_reviews,
                bot_webhook_url="http://test.com/webhook"
            )
        
        assert result["status"] == "success"
        assert result["notifications_sent"] == 1
        assert len(result["events"]) == 1
        assert result["events"][0]["type"] == "negative_review"
    
    @pytest.mark.asyncio
    async def test_process_sync_events_critical_stocks(self, db_session):
        """Тест обработки событий критичных остатков"""
        service = NotificationService(db_session)
        
        # Создаем пользователя
        from app.features.user.models import User
        user = User(
            telegram_id=444555666, 
            username="test_user_5",
            first_name="Test5",
            last_name="User5"
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        
        # Создаем настройки
        settings = service.settings_crud.create_default_settings(db_session, user.id)
        
        # Предыдущие остатки
        previous_stocks = [
            {"nm_id": 1, "name": "Товар 1", "stocks": {"S": 10, "M": 5, "L": 3}}
        ]
        
        # Текущие остатки (стали критичными)
        current_stocks = [
            {"nm_id": 1, "name": "Товар 1", "stocks": {"S": 1, "M": 0, "L": 0}}
        ]
        
        # Мокаем webhook отправку
        with patch.object(service.webhook_sender, 'send_critical_stocks_notification') as mock_send:
            mock_send.return_value = {"success": True, "attempts": 1}
            
            result = await service.process_sync_events(
                user_id=user.id,
                cabinet_id=1,
                current_orders=[],
                previous_orders=[],
                current_stocks=current_stocks,
                previous_stocks=previous_stocks,
                bot_webhook_url="http://test.com/webhook"
            )
        
        assert result["status"] == "success"
        assert result["notifications_sent"] == 1
        assert len(result["events"]) == 1
        assert result["events"][0]["type"] == "critical_stocks"
    
    def test_format_order_buyout_for_telegram(self, db_session):
        """Тест форматирования уведомления о выкупе для Telegram"""
        service = NotificationService(db_session)
        
        notification = {
            "order_id": 12345,
            "amount": 2500,
            "product_name": "Тестовый товар",
            "brand": "Test Brand"
        }
        
        result = service._format_order_buyout_for_telegram(notification)
        
        assert "ЗАКАЗ ВЫКУПЛЕН" in result
        assert "12345" in result
        assert "2,500" in result
        assert "Тестовый товар" in result
        assert "Test Brand" in result
    
    def test_format_order_cancellation_for_telegram(self, db_session):
        """Тест форматирования уведомления об отмене для Telegram"""
        service = NotificationService(db_session)
        
        notification = {
            "order_id": 67890,
            "amount": 1800,
            "product_name": "Отмененный товар",
            "brand": "Cancel Brand"
        }
        
        result = service._format_order_cancellation_for_telegram(notification)
        
        assert "ЗАКАЗ ОТМЕНЕН" in result
        assert "67890" in result
        assert "1,800" in result
        assert "Отмененный товар" in result
        assert "Cancel Brand" in result
    
    def test_format_order_return_for_telegram(self, db_session):
        """Тест форматирования уведомления о возврате для Telegram"""
        service = NotificationService(db_session)
        
        notification = {
            "order_id": 11111,
            "amount": 3000,
            "product_name": "Возвращенный товар",
            "brand": "Return Brand"
        }
        
        result = service._format_order_return_for_telegram(notification)
        
        assert "ЗАКАЗ ВОЗВРАЩЕН" in result
        assert "11111" in result
        assert "3,000" in result
        assert "Возвращенный товар" in result
        assert "Return Brand" in result
    
    def test_format_negative_review_for_telegram(self, db_session):
        """Тест форматирования уведомления о негативном отзыве для Telegram"""
        service = NotificationService(db_session)
        
        notification = {
            "review_id": 22222,
            "rating": 2,
            "text": "Плохой товар",
            "product_name": "Товар с плохим отзывом",
            "order_id": 33333
        }
        
        result = service._format_negative_review_for_telegram(notification)
        
        assert "НЕГАТИВНЫЙ ОТЗЫВ" in result
        assert "2/5" in result
        assert "Плохой товар" in result
        assert "Товар с плохим отзывом" in result
        assert "33333" in result
    
    def test_settings_to_dict(self, db_session):
        """Тест преобразования настроек в словарь"""
        service = NotificationService(db_session)
        
        # Создаем пользователя и настройки
        from app.features.user.models import User
        user = User(
            telegram_id=777888999, 
            username="test_user_6",
            first_name="Test6",
            last_name="User6"
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        
        settings = service.settings_crud.create_default_settings(db_session, user.id)
        
        # Преобразуем в словарь
        settings_dict = service._settings_to_dict(settings)
        
        assert isinstance(settings_dict, dict)
        assert "notifications_enabled" in settings_dict
        assert "new_orders_enabled" in settings_dict
        assert "order_buyouts_enabled" in settings_dict
        assert "order_cancellations_enabled" in settings_dict
        assert "order_returns_enabled" in settings_dict
        assert "negative_reviews_enabled" in settings_dict
        assert "critical_stocks_enabled" in settings_dict
        assert "grouping_enabled" in settings_dict
        assert "max_group_size" in settings_dict
        assert "group_timeout" in settings_dict
