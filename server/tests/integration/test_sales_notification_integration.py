"""
Интеграционные тесты для полного потока уведомлений о продажах
"""
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timezone

from app.features.notifications.notification_service import NotificationService
from app.features.notifications.wb_sync_integration import WBSyncNotificationIntegration
from app.features.wb_api.models import WBCabinet
from app.features.user.models import User


class TestSalesNotificationIntegration:
    """Интеграционные тесты для уведомлений о продажах"""
    
    @pytest.fixture
    def mock_db(self):
        """Мок базы данных"""
        return Mock()
    
    @pytest.fixture
    def mock_redis(self):
        """Мок Redis клиента"""
        return Mock()
    
    @pytest.fixture
    def sample_user(self):
        """Пример пользователя"""
        user = Mock(spec=User)
        user.id = 123
        user.telegram_id = 123456789
        user.first_name = "Test"
        user.last_name = "User"
        return user
    
    @pytest.fixture
    def sample_cabinet(self, sample_user):
        """Пример кабинета"""
        cabinet = Mock(spec=WBCabinet)
        cabinet.id = 1
        cabinet.user_id = sample_user.id
        cabinet.name = "Test Cabinet"
        return cabinet
    
    @pytest.fixture
    def sample_sales_data(self):
        """Пример данных продаж"""
        return [
            {
                "sale_id": "sale_1",
                "order_id": "order_1",
                "nm_id": 12345,
                "product_name": "Test Product 1",
                "brand": "Test Brand",
                "size": "M",
                "amount": 1000.0,
                "sale_date": datetime.now(timezone.utc),
                "type": "buyout",
                "status": "completed",
                "is_cancel": False
            },
            {
                "sale_id": "sale_2",
                "order_id": "order_2",
                "nm_id": 12346,
                "product_name": "Test Product 2",
                "brand": "Test Brand",
                "size": "L",
                "amount": 1500.0,
                "sale_date": datetime.now(timezone.utc),
                "type": "return",
                "status": "completed",
                "is_cancel": False
            }
        ]
    
    @pytest.fixture
    def notification_service(self, mock_db, mock_redis):
        """Экземпляр NotificationService"""
        return NotificationService(mock_db, mock_redis)
    
    @pytest.fixture
    def wb_sync_integration(self, mock_db, notification_service):
        """Экземпляр WBSyncNotificationIntegration"""
        return WBSyncNotificationIntegration(mock_db, notification_service)
    
    @pytest.mark.asyncio
    async def test_complete_sales_notification_flow(
        self, 
        notification_service, 
        wb_sync_integration, 
        sample_cabinet, 
        sample_sales_data,
        mock_db,
        mock_redis
    ):
        """Тест полного потока уведомлений о продажах"""
        # Мокаем настройки пользователя
        mock_settings = Mock()
        mock_settings.notifications_enabled = True
        mock_settings.order_buyouts_enabled = True
        mock_settings.order_returns_enabled = True
        
        with patch.object(notification_service.settings_crud, 'get_user_settings', return_value=mock_settings):
            with patch.object(notification_service, '_send_webhook_notification', new_callable=AsyncMock) as mock_webhook:
                mock_webhook.return_value = {"success": True, "message": "Notification sent"}
                
                # Обрабатываем события продаж
                result = await wb_sync_integration.process_sales_notifications(
                    cabinet=sample_cabinet,
                    current_sales=sample_sales_data,
                    previous_sales=[],
                    bot_webhook_url="http://test.com/webhook"
                )
                
                # Проверяем результат
                assert result["status"] == "success"
                assert result["notifications_sent"] == 2  # Один выкуп + один возврат
                assert result["sales_processed"] == 2
                
                # Проверяем, что webhook был вызван для каждого события
                assert mock_webhook.call_count == 2
    
    @pytest.mark.asyncio
    async def test_sales_notification_with_previous_data(
        self,
        notification_service,
        wb_sync_integration,
        sample_cabinet,
        sample_sales_data,
        mock_db,
        mock_redis
    ):
        """Тест уведомлений о продажах с предыдущими данными"""
        # Предыдущие данные (только один выкуп)
        previous_sales = [sample_sales_data[0]]
        
        # Текущие данные (оба продажи)
        current_sales = sample_sales_data
        
        # Мокаем настройки
        mock_settings = Mock()
        mock_settings.notifications_enabled = True
        mock_settings.order_buyouts_enabled = True
        mock_settings.order_returns_enabled = True
        
        with patch.object(notification_service.settings_crud, 'get_user_settings', return_value=mock_settings):
            with patch.object(notification_service, '_send_webhook_notification', new_callable=AsyncMock) as mock_webhook:
                mock_webhook.return_value = {"success": True, "message": "Notification sent"}
                
                # Обрабатываем события
                result = await wb_sync_integration.process_sales_notifications(
                    cabinet=sample_cabinet,
                    current_sales=current_sales,
                    previous_sales=previous_sales,
                    bot_webhook_url="http://test.com/webhook"
                )
                
                # Проверяем результат
                assert result["status"] == "success"
                assert result["notifications_sent"] == 1  # Только новый возврат
                assert result["sales_processed"] == 2
                
                # Проверяем, что webhook был вызван только для нового события
                assert mock_webhook.call_count == 1
    
    @pytest.mark.asyncio
    async def test_sales_notification_with_disabled_settings(
        self,
        notification_service,
        wb_sync_integration,
        sample_cabinet,
        sample_sales_data,
        mock_db,
        mock_redis
    ):
        """Тест уведомлений с отключенными настройками"""
        # Мокаем отключенные настройки
        mock_settings = Mock()
        mock_settings.notifications_enabled = False
        
        with patch.object(notification_service.settings_crud, 'get_user_settings', return_value=mock_settings):
            result = await wb_sync_integration.process_sales_notifications(
                cabinet=sample_cabinet,
                current_sales=sample_sales_data,
                previous_sales=[],
                bot_webhook_url="http://test.com/webhook"
            )
            
            # Проверяем, что уведомления не отправлены
            assert result["status"] == "success"
            assert result["notifications_sent"] == 0
    
    @pytest.mark.asyncio
    async def test_sales_notification_with_partial_settings(
        self,
        notification_service,
        wb_sync_integration,
        sample_cabinet,
        sample_sales_data,
        mock_db,
        mock_redis
    ):
        """Тест уведомлений с частично отключенными настройками"""
        # Мокаем частично отключенные настройки
        mock_settings = Mock()
        mock_settings.notifications_enabled = True
        mock_settings.order_buyouts_enabled = True
        mock_settings.order_returns_enabled = False  # Отключены возвраты
        
        with patch.object(notification_service.settings_crud, 'get_user_settings', return_value=mock_settings):
            with patch.object(notification_service, '_send_webhook_notification', new_callable=AsyncMock) as mock_webhook:
                mock_webhook.return_value = {"success": True, "message": "Notification sent"}
                
                result = await wb_sync_integration.process_sales_notifications(
                    cabinet=sample_cabinet,
                    current_sales=sample_sales_data,
                    previous_sales=[],
                    bot_webhook_url="http://test.com/webhook"
                )
                
                # Проверяем, что отправлено только уведомление о выкупе
                assert result["status"] == "success"
                assert result["notifications_sent"] == 1  # Только выкуп
                assert mock_webhook.call_count == 1
    
    @pytest.mark.asyncio
    async def test_individual_buyout_notification(
        self,
        wb_sync_integration,
        sample_cabinet,
        mock_db
    ):
        """Тест отправки индивидуального уведомления о выкупе"""
        buyout_data = {
            "sale_id": "sale_123",
            "order_id": "order_456",
            "product_name": "Test Product",
            "amount": 2000.0,
            "brand": "Test Brand",
            "size": "XL"
        }
        
        with patch.object(wb_sync_integration.notification_service, '_send_webhook_notification', new_callable=AsyncMock) as mock_webhook:
            mock_webhook.return_value = {"success": True, "message": "Buyout notification sent"}
            
            result = await wb_sync_integration.send_new_buyout_notification(
                cabinet=sample_cabinet,
                buyout_data=buyout_data,
                bot_webhook_url="http://test.com/webhook"
            )
            
            # Проверяем результат
            assert result["status"] == "success"
            assert result["notification_sent"] is True
            assert mock_webhook.call_count == 1
    
    @pytest.mark.asyncio
    async def test_individual_return_notification(
        self,
        wb_sync_integration,
        sample_cabinet,
        mock_db
    ):
        """Тест отправки индивидуального уведомления о возврате"""
        return_data = {
            "sale_id": "sale_456",
            "order_id": "order_789",
            "product_name": "Test Product Return",
            "amount": 1500.0,
            "brand": "Test Brand",
            "size": "M"
        }
        
        with patch.object(wb_sync_integration.notification_service, '_send_webhook_notification', new_callable=AsyncMock) as mock_webhook:
            mock_webhook.return_value = {"success": True, "message": "Return notification sent"}
            
            result = await wb_sync_integration.send_new_return_notification(
                cabinet=sample_cabinet,
                return_data=return_data,
                bot_webhook_url="http://test.com/webhook"
            )
            
            # Проверяем результат
            assert result["status"] == "success"
            assert result["notification_sent"] is True
            assert mock_webhook.call_count == 1
    
    @pytest.mark.asyncio
    async def test_sales_notification_error_handling(
        self,
        notification_service,
        wb_sync_integration,
        sample_cabinet,
        sample_sales_data,
        mock_db,
        mock_redis
    ):
        """Тест обработки ошибок в уведомлениях о продажах"""
        # Мокаем настройки
        mock_settings = Mock()
        mock_settings.notifications_enabled = True
        mock_settings.order_buyouts_enabled = True
        mock_settings.order_returns_enabled = True
        
        with patch.object(notification_service.settings_crud, 'get_user_settings', return_value=mock_settings):
            with patch.object(notification_service, '_send_webhook_notification', new_callable=AsyncMock) as mock_webhook:
                # Мокаем ошибку webhook
                mock_webhook.side_effect = Exception("Webhook error")
                
                result = await wb_sync_integration.process_sales_notifications(
                    cabinet=sample_cabinet,
                    current_sales=sample_sales_data,
                    previous_sales=[],
                    bot_webhook_url="http://test.com/webhook"
                )
                
                # Проверяем, что система обработала ошибку gracefully
                assert result["status"] == "success"
                assert result["notifications_sent"] == 0  # Ни одно уведомление не отправлено
                assert result["sales_processed"] == 2
    
    @pytest.mark.asyncio
    async def test_sales_monitor_integration(
        self,
        notification_service,
        sample_cabinet,
        sample_sales_data,
        mock_db,
        mock_redis
    ):
        """Тест интеграции с SalesMonitor"""
        # Мокаем настройки
        mock_settings = Mock()
        mock_settings.notifications_enabled = True
        mock_settings.order_buyouts_enabled = True
        mock_settings.order_returns_enabled = True
        
        with patch.object(notification_service.settings_crud, 'get_user_settings', return_value=mock_settings):
            with patch.object(notification_service, '_send_webhook_notification', new_callable=AsyncMock) as mock_webhook:
                mock_webhook.return_value = {"success": True, "message": "Notification sent"}
                
                # Обрабатываем события продаж
                result = await notification_service.process_sales_events(
                    user_id=sample_cabinet.user_id,
                    cabinet_id=sample_cabinet.id,
                    current_sales=sample_sales_data,
                    previous_sales=[],
                    bot_webhook_url="http://test.com/webhook"
                )
                
                # Проверяем результат
                assert result == 2  # Два уведомления отправлено
                
                # Проверяем, что SalesMonitor был использован
                mock_redis.lpush.assert_called()  # SalesMonitor должен сохранить изменения в Redis
