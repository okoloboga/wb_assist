"""
Тесты для интеграции NotificationService с WBSyncService
"""

import pytest
from datetime import datetime, timezone
from typing import List, Dict, Any
from unittest.mock import Mock, AsyncMock, patch

from app.features.notifications.wb_sync_integration import WBSyncNotificationIntegration


class TestWBSyncNotificationIntegration:
    """Тесты для интеграции WBSyncService с NotificationService"""
    
    def test_integration_initialization(self, db_session):
        """Тест инициализации интеграции"""
        integration = WBSyncNotificationIntegration(db_session)
        
        assert integration.db == db_session
        assert integration.notification_service is not None
    
    @pytest.mark.asyncio
    async def test_process_sync_notifications_success(self, db_session):
        """Тест успешной обработки уведомлений синхронизации"""
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
        
        # Добавляем bot_webhook_url
        user.bot_webhook_url = "http://test.com/webhook"
        db_session.commit()
        
        # Создаем кабинет
        from app.features.wb_api.models import WBCabinet
        cabinet = WBCabinet(
            user_id=user.id,
            name="Integration Cabinet",
            api_key="test_api_key",
            last_sync_at=datetime.now(timezone.utc)
        )
        db_session.add(cabinet)
        db_session.commit()
        db_session.refresh(cabinet)
        
        # Создаем интеграцию
        integration = WBSyncNotificationIntegration(db_session)
        
        # Мокаем NotificationService
        with patch.object(integration.notification_service, 'process_sync_events') as mock_process:
            mock_process.return_value = {
                "status": "success",
                "notifications_sent": 2,
                "events": [
                    {"type": "new_order", "order_id": 12345},
                    {"type": "order_buyout", "order_id": 67890}
                ]
            }
            
            # Обрабатываем уведомления
            result = await integration.process_sync_notifications(
                cabinet=cabinet,
                current_orders=[
                    {"order_id": 12345, "status": "active", "amount": 1000}
                ],
                previous_orders=[],
                current_reviews=[
                    {"id": 1, "rating": 2, "text": "Плохо"}
                ],
                previous_reviews=[]
            )
        
        # Проверяем результат
        assert result["status"] == "success"
        assert result["notifications_sent"] == 2
        assert len(result["events"]) == 2
        
        # Проверяем, что NotificationService был вызван
        mock_process.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_sync_notifications_user_not_found(self, db_session):
        """Тест обработки уведомлений при отсутствии пользователя"""
        # Создаем кабинет без пользователя
        from app.features.wb_api.models import WBCabinet
        cabinet = WBCabinet(
            user_id=999999,  # Несуществующий пользователь
            name="Orphan Cabinet",
            api_key="test_api_key",
            last_sync_at=datetime.now(timezone.utc)
        )
        db_session.add(cabinet)
        db_session.commit()
        db_session.refresh(cabinet)
        
        # Создаем интеграцию
        integration = WBSyncNotificationIntegration(db_session)
        
        # Обрабатываем уведомления
        result = await integration.process_sync_notifications(
            cabinet=cabinet,
            current_orders=[],
            previous_orders=[]
        )
        
        # Проверяем результат
        assert result["status"] == "error"
        assert "User not found" in result["error"]
    
    @pytest.mark.asyncio
    async def test_send_new_order_notification_success(self, db_session):
        """Тест успешной отправки уведомления о новом заказе"""
        # Создаем пользователя
        from app.features.user.models import User
        user = User(
            telegram_id=987654321,
            username="order_test_user",
            first_name="Order",
            last_name="Test"
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        
        # Добавляем bot_webhook_url
        user.bot_webhook_url = "http://test.com/webhook"
        db_session.commit()
        
        # Создаем кабинет
        from app.features.wb_api.models import WBCabinet
        cabinet = WBCabinet(
            user_id=user.id,
            name="Order Cabinet",
            api_key="test_api_key",
            last_sync_at=datetime.now(timezone.utc)
        )
        db_session.add(cabinet)
        db_session.commit()
        db_session.refresh(cabinet)
        
        # Создаем интеграцию
        integration = WBSyncNotificationIntegration(db_session)
        
        # Мокаем NotificationService
        with patch.object(integration.notification_service, 'process_sync_events') as mock_process:
            mock_process.return_value = {
                "status": "success",
                "notifications_sent": 1,
                "events": [{"type": "new_order", "order_id": 12345}]
            }
            
            # Отправляем уведомление о новом заказе
            order_data = {
                "order_id": 12345,
                "status": "active",
                "amount": 1000,
                "product_name": "Тестовый товар",
                "brand": "Test Brand",
                "nm_id": 67890
            }
            
            result = await integration.send_new_order_notification(
                cabinet=cabinet,
                order_data=order_data,
                order=None
            )
        
        # Проверяем результат
        assert result["status"] == "success"
        assert result["notifications_sent"] == 1
        
        # Проверяем, что NotificationService был вызван
        mock_process.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_critical_stocks_notification_success(self, db_session):
        """Тест успешной отправки уведомления о критичных остатках"""
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
        
        # Добавляем bot_webhook_url
        user.bot_webhook_url = "http://test.com/webhook"
        db_session.commit()
        
        # Создаем кабинет
        from app.features.wb_api.models import WBCabinet
        cabinet = WBCabinet(
            user_id=user.id,
            name="Stocks Cabinet",
            api_key="test_api_key",
            last_sync_at=datetime.now(timezone.utc)
        )
        db_session.add(cabinet)
        db_session.commit()
        db_session.refresh(cabinet)
        
        # Создаем интеграцию
        integration = WBSyncNotificationIntegration(db_session)
        
        # Мокаем NotificationService
        with patch.object(integration.notification_service, 'process_sync_events') as mock_process:
            mock_process.return_value = {
                "status": "success",
                "notifications_sent": 1,
                "events": [{"type": "critical_stocks", "nm_id": 11111}]
            }
            
            # Отправляем уведомление о критичных остатках
            stocks_data = [
                {
                    "nm_id": 11111,
                    "name": "Товар с критичными остатками",
                    "stocks": {"S": 1, "M": 0, "L": 0}
                }
            ]
            
            result = await integration.send_critical_stocks_notification(
                cabinet=cabinet,
                stocks_data=stocks_data
            )
        
        # Проверяем результат
        assert result["status"] == "success"
        assert result["notifications_sent"] == 1
        
        # Проверяем, что NotificationService был вызван
        mock_process.assert_called_once()
    
    def test_create_notification_service_wrapper(self, db_session):
        """Тест создания обертки для NotificationService"""
        integration = WBSyncNotificationIntegration(db_session)
        
        # Создаем мок оригинального метода
        original_method = AsyncMock()
        original_method.return_value = {"status": "success", "method": "original"}
        
        # Создаем обертку
        wrapper = integration.create_notification_service_wrapper(original_method)
        
        # Проверяем, что обертка создана
        assert callable(wrapper)
        
        # Тестируем вызов обертки (в реальной реализации это будет async)
        # wrapper(cabinet, order_data, order) - для нового заказа
        # wrapper(cabinet, stocks_data) - для критичных остатков
