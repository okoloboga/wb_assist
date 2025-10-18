"""
Интеграционные тесты для Notification Service с WBSyncService
"""

import pytest
from datetime import datetime, timezone
from typing import List, Dict, Any
from unittest.mock import Mock, AsyncMock, patch

from app.features.notifications.notification_service import NotificationService


class TestNotificationServiceIntegration:
    """Интеграционные тесты для Notification Service"""
    
    @pytest.mark.asyncio
    async def test_notification_service_with_wb_sync_integration(self, db_session):
        """Тест интеграции Notification Service с WBSyncService"""
        service = NotificationService(db_session)
        
        # Создаем пользователя
        from app.features.user.models import User
        user = User(
            telegram_id=123456789, 
            username="integration_test_user",
            first_name="Integration",
            last_name="Test"
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        
        # Создаем настройки
        settings = service.settings_crud.create_default_settings(db_session, user.id)
        
        # Данные для синхронизации (как в WBSyncService)
        previous_orders = [
            {
                "order_id": 1,
                "status": "active",
                "amount": 1000,
                "product_name": "Товар 1",
                "brand": "Brand 1",
                "nm_id": 12345
            }
        ]
        
        current_orders = [
            {
                "order_id": 1,
                "status": "buyout",  # Статус изменился
                "amount": 1000,
                "product_name": "Товар 1",
                "brand": "Brand 1",
                "nm_id": 12345
            },
            {
                "order_id": 2,  # Новый заказ
                "status": "active",
                "amount": 2000,
                "product_name": "Товар 2",
                "brand": "Brand 2",
                "nm_id": 67890
            }
        ]
        
        # Мокаем webhook отправку
        with patch.object(service.webhook_sender, 'send_new_order_notification') as mock_new_order, \
             patch.object(service, '_send_generic_webhook_notification') as mock_generic:
            
            mock_new_order.return_value = {"success": True, "attempts": 1}
            mock_generic.return_value = {"success": True, "attempts": 1}
            
            # Обрабатываем события синхронизации
            result = await service.process_sync_events(
                user_id=user.id,
                cabinet_id=1,
                current_orders=current_orders,
                previous_orders=previous_orders,
                bot_webhook_url="http://test.com/webhook"
            )
        
        # Проверяем результат
        assert result["status"] == "success"
        assert result["notifications_sent"] == 2  # Новый заказ + изменение статуса
        assert len(result["events"]) == 2
        
        # Проверяем типы событий
        event_types = [event["type"] for event in result["events"]]
        assert "new_order" in event_types
        assert "order_buyout" in event_types
        
        # Проверяем, что были вызваны правильные методы отправки
        assert mock_new_order.called  # Для нового заказа
        assert mock_generic.called    # Для изменения статуса
    
    @pytest.mark.asyncio
    async def test_notification_service_with_reviews_integration(self, db_session):
        """Тест интеграции Notification Service с отзывами"""
        service = NotificationService(db_session)
        
        # Создаем пользователя
        from app.features.user.models import User
        user = User(
            telegram_id=987654321, 
            username="reviews_test_user",
            first_name="Reviews",
            last_name="Test"
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        
        # Создаем настройки
        settings = service.settings_crud.create_default_settings(db_session, user.id)
        
        # Предыдущие отзывы
        previous_reviews = [
            {
                "id": 1,
                "rating": 5,
                "text": "Отлично!",
                "product_name": "Товар 1",
                "nm_id": 12345
            }
        ]
        
        # Текущие отзывы (добавился негативный)
        current_reviews = [
            {
                "id": 1,
                "rating": 5,
                "text": "Отлично!",
                "product_name": "Товар 1",
                "nm_id": 12345
            },
            {
                "id": 2,
                "rating": 2,
                "text": "Плохой товар",
                "product_name": "Товар 2",
                "nm_id": 67890,
                "order_id": 123
            }
        ]
        
        # Мокаем webhook отправку
        with patch.object(service, '_send_generic_webhook_notification') as mock_send:
            mock_send.return_value = {"success": True, "attempts": 1}
            
            # Обрабатываем события синхронизации
            result = await service.process_sync_events(
                user_id=user.id,
                cabinet_id=1,
                current_orders=[],
                previous_orders=[],
                current_reviews=current_reviews,
                previous_reviews=previous_reviews,
                bot_webhook_url="http://test.com/webhook"
            )
        
        # Проверяем результат
        assert result["status"] == "success"
        assert result["notifications_sent"] == 1
        assert len(result["events"]) == 1
        assert result["events"][0]["type"] == "negative_review"
        
        # Проверяем, что был вызван метод отправки
        assert mock_send.called
    
    @pytest.mark.asyncio
    async def test_notification_service_with_stocks_integration(self, db_session):
        """Тест интеграции Notification Service с остатками"""
        service = NotificationService(db_session)
        
        # Создаем пользователя
        from app.features.user.models import User
        user = User(
            telegram_id=555666777, 
            username="stocks_test_user",
            first_name="Stocks",
            last_name="Test"
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        
        # Создаем настройки
        settings = service.settings_crud.create_default_settings(db_session, user.id)
        
        # Предыдущие остатки
        previous_stocks = [
            {
                "nm_id": 12345,
                "name": "Товар 1",
                "stocks": {"S": 10, "M": 5, "L": 3}
            }
        ]
        
        # Текущие остатки (стали критичными)
        current_stocks = [
            {
                "nm_id": 12345,
                "name": "Товар 1",
                "stocks": {"S": 1, "M": 0, "L": 0}
            }
        ]
        
        # Мокаем webhook отправку
        with patch.object(service.webhook_sender, 'send_critical_stocks_notification') as mock_send:
            mock_send.return_value = {"success": True, "attempts": 1}
            
            # Обрабатываем события синхронизации
            result = await service.process_sync_events(
                user_id=user.id,
                cabinet_id=1,
                current_orders=[],
                previous_orders=[],
                current_stocks=current_stocks,
                previous_stocks=previous_stocks,
                bot_webhook_url="http://test.com/webhook"
            )
        
        # Проверяем результат
        assert result["status"] == "success"
        assert result["notifications_sent"] == 1
        assert len(result["events"]) == 1
        assert result["events"][0]["type"] == "critical_stocks"
        
        # Проверяем, что был вызван метод отправки
        assert mock_send.called
    
    @pytest.mark.asyncio
    async def test_notification_service_complete_workflow(self, db_session):
        """Тест полного рабочего процесса Notification Service"""
        service = NotificationService(db_session)
        
        # Создаем пользователя
        from app.features.user.models import User
        user = User(
            telegram_id=111222333, 
            username="complete_test_user",
            first_name="Complete",
            last_name="Test"
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        
        # Создаем настройки
        settings = service.settings_crud.create_default_settings(db_session, user.id)
        
        # Комплексные данные для синхронизации
        previous_orders = [
            {
                "order_id": 1,
                "status": "active",
                "amount": 1000,
                "product_name": "Товар 1",
                "brand": "Brand 1",
                "nm_id": 12345
            }
        ]
        
        current_orders = [
            {
                "order_id": 1,
                "status": "buyout",  # Статус изменился
                "amount": 1000,
                "product_name": "Товар 1",
                "brand": "Brand 1",
                "nm_id": 12345
            },
            {
                "order_id": 2,  # Новый заказ
                "status": "active",
                "amount": 2000,
                "product_name": "Товар 2",
                "brand": "Brand 2",
                "nm_id": 67890
            }
        ]
        
        previous_reviews = [
            {
                "id": 1,
                "rating": 5,
                "text": "Отлично!",
                "product_name": "Товар 1",
                "nm_id": 12345
            }
        ]
        
        current_reviews = [
            {
                "id": 1,
                "rating": 5,
                "text": "Отлично!",
                "product_name": "Товар 1",
                "nm_id": 12345
            },
            {
                "id": 2,
                "rating": 2,
                "text": "Плохой товар",
                "product_name": "Товар 2",
                "nm_id": 67890,
                "order_id": 2
            }
        ]
        
        previous_stocks = [
            {
                "nm_id": 12345,
                "name": "Товар 1",
                "stocks": {"S": 10, "M": 5, "L": 3}
            }
        ]
        
        current_stocks = [
            {
                "nm_id": 12345,
                "name": "Товар 1",
                "stocks": {"S": 1, "M": 0, "L": 0}
            }
        ]
        
        # Мокаем webhook отправку
        with patch.object(service.webhook_sender, 'send_new_order_notification') as mock_new_order, \
             patch.object(service.webhook_sender, 'send_critical_stocks_notification') as mock_stocks, \
             patch.object(service, '_send_generic_webhook_notification') as mock_generic:
            
            mock_new_order.return_value = {"success": True, "attempts": 1}
            mock_stocks.return_value = {"success": True, "attempts": 1}
            mock_generic.return_value = {"success": True, "attempts": 1}
            
            # Обрабатываем все события синхронизации
            result = await service.process_sync_events(
                user_id=user.id,
                cabinet_id=1,
                current_orders=current_orders,
                previous_orders=previous_orders,
                current_reviews=current_reviews,
                previous_reviews=previous_reviews,
                current_stocks=current_stocks,
                previous_stocks=previous_stocks,
                bot_webhook_url="http://test.com/webhook"
            )
        
        # Проверяем результат
        assert result["status"] == "success"
        assert result["notifications_sent"] == 4  # Новый заказ + изменение статуса + негативный отзыв + критичные остатки
        assert len(result["events"]) == 4
        
        # Проверяем типы событий
        event_types = [event["type"] for event in result["events"]]
        assert "new_order" in event_types
        assert "order_buyout" in event_types
        assert "negative_review" in event_types
        assert "critical_stocks" in event_types
        
        # Проверяем, что были вызваны правильные методы отправки
        assert mock_new_order.called   # Для нового заказа
        assert mock_stocks.called      # Для критичных остатков
        assert mock_generic.call_count == 2  # Для изменения статуса + негативного отзыва
