"""
Интеграционные тесты для синхронизации продаж с WB API
"""
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timezone

from app.features.wb_api.sync_service import WBSyncService
from app.features.wb_api.client import WBAPIClient
from app.features.wb_api.models import WBCabinet
from app.features.user.models import User


class TestSalesSyncIntegration:
    """Интеграционные тесты для синхронизации продаж"""
    
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
        cabinet.api_key = "test_api_key"
        return cabinet
    
    @pytest.fixture
    def sample_wb_sales_data(self):
        """Пример данных продаж из WB API"""
        return [
            {
                "srid": "sale_123",
                "orderId": "order_456",
                "nmId": 12345,
                "subject": "Test Product 1",
                "brand": "Test Brand",
                "techSize": "M",
                "totalPrice": 1000.0,
                "date": "2025-01-28T12:00:00",
                "isCancel": False,
                "lastChangeDate": "2025-01-28T12:00:00"
            },
            {
                "srid": "sale_456",
                "orderId": "order_789",
                "nmId": 12346,
                "subject": "Test Product 2",
                "brand": "Test Brand",
                "techSize": "L",
                "totalPrice": 1500.0,
                "date": "2025-01-28T13:00:00",
                "isCancel": True,  # Возврат
                "lastChangeDate": "2025-01-28T13:00:00"
            }
        ]
    
    @pytest.fixture
    def wb_sync_service(self, mock_db, mock_redis):
        """Экземпляр WBSyncService"""
        return WBSyncService(mock_db, mock_redis)
    
    @pytest.mark.asyncio
    async def test_sync_sales_success(
        self,
        wb_sync_service,
        sample_cabinet,
        sample_wb_sales_data,
        mock_db,
        mock_redis
    ):
        """Тест успешной синхронизации продаж"""
        # Мокаем WBAPIClient
        mock_client = Mock(spec=WBAPIClient)
        mock_client.get_sales = AsyncMock(return_value=sample_wb_sales_data)
        
        # Мокаем WBSalesCRUD
        mock_sales_crud = Mock()
        mock_sales_crud.get_sale_by_sale_id.return_value = None  # Новые продажи
        mock_sales_crud.create_sale.return_value = Mock()
        
        with patch('app.features.wb_api.sync_service.WBAPIClient', return_value=mock_client):
            with patch('app.features.wb_api.crud_sales.WBSalesCRUD', return_value=mock_sales_crud):
                with patch.object(wb_sync_service, '_process_sale_notification', new_callable=AsyncMock) as mock_notification:
                    mock_notification.return_value = None
                    
                    # Выполняем синхронизацию
                    result = await wb_sync_service.sync_sales(
                        cabinet=sample_cabinet,
                        client=mock_client,
                        date_from="2025-01-28",
                        date_to="2025-01-28",
                        should_notify=True
                    )
                    
                    # Проверяем результат
                    assert result["status"] == "success"
                    assert result["records_processed"] == 2
                    assert result["records_created"] == 2
                    
                    # Проверяем, что CRUD методы были вызваны
                    assert mock_sales_crud.get_sale_by_sale_id.call_count == 2
                    assert mock_sales_crud.create_sale.call_count == 2
                    
                    # Проверяем, что уведомления были обработаны
                    assert mock_notification.call_count == 2
    
    @pytest.mark.asyncio
    async def test_sync_sales_no_data(
        self,
        wb_sync_service,
        sample_cabinet,
        mock_db,
        mock_redis
    ):
        """Тест синхронизации без данных"""
        # Мокаем WBAPIClient с пустыми данными
        mock_client = Mock(spec=WBAPIClient)
        mock_client.get_sales = AsyncMock(return_value=[])
        
        with patch('app.features.wb_api.sync_service.WBAPIClient', return_value=mock_client):
            result = await wb_sync_service.sync_sales(
                cabinet=sample_cabinet,
                client=mock_client,
                date_from="2025-01-28",
                date_to="2025-01-28",
                should_notify=False
            )
            
            # Проверяем результат
            assert result["status"] == "success"
            assert result["records_processed"] == 0
            assert result["records_created"] == 0
    
    @pytest.mark.asyncio
    async def test_sync_sales_existing_records(
        self,
        wb_sync_service,
        sample_cabinet,
        sample_wb_sales_data,
        mock_db,
        mock_redis
    ):
        """Тест синхронизации с существующими записями"""
        # Мокаем WBAPIClient
        mock_client = Mock(spec=WBAPIClient)
        mock_client.get_sales = AsyncMock(return_value=sample_wb_sales_data)
        
        # Мокаем WBSalesCRUD с существующими записями
        mock_sales_crud = Mock()
        mock_sales_crud.get_sale_by_sale_id.return_value = Mock()  # Записи уже существуют
        
        with patch('app.features.wb_api.sync_service.WBAPIClient', return_value=mock_client):
            with patch('app.features.wb_api.crud_sales.WBSalesCRUD', return_value=mock_sales_crud):
                result = await wb_sync_service.sync_sales(
                    cabinet=sample_cabinet,
                    client=mock_client,
                    date_from="2025-01-28",
                    date_to="2025-01-28",
                    should_notify=False
                )
                
                # Проверяем результат
                assert result["status"] == "success"
                assert result["records_processed"] == 2
                assert result["records_created"] == 0  # Новые записи не созданы
                
                # Проверяем, что create_sale не был вызван
                mock_sales_crud.create_sale.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_sync_sales_api_error(
        self,
        wb_sync_service,
        sample_cabinet,
        mock_db,
        mock_redis
    ):
        """Тест синхронизации с ошибкой API"""
        # Мокаем WBAPIClient с ошибкой
        mock_client = Mock(spec=WBAPIClient)
        mock_client.get_sales = AsyncMock(side_effect=Exception("API Error"))
        
        with patch('app.features.wb_api.sync_service.WBAPIClient', return_value=mock_client):
            result = await wb_sync_service.sync_sales(
                cabinet=sample_cabinet,
                client=mock_client,
                date_from="2025-01-28",
                date_to="2025-01-28",
                should_notify=False
            )
            
            # Проверяем результат
            assert result["status"] == "error"
            assert "API Error" in result["error_message"]
    
    @pytest.mark.asyncio
    async def test_sync_sales_buyout_detection(
        self,
        wb_sync_service,
        sample_cabinet,
        mock_db,
        mock_redis
    ):
        """Тест определения выкупов"""
        # Данные с выкупом
        buyout_data = [{
            "srid": "sale_123",
            "orderId": "order_456",
            "nmId": 12345,
            "subject": "Test Product",
            "brand": "Test Brand",
            "techSize": "M",
            "totalPrice": 1000.0,
            "date": "2025-01-28T12:00:00",
            "isCancel": False,
            "lastChangeDate": "2025-01-28T12:00:00"
        }]
        
        # Мокаем WBAPIClient
        mock_client = Mock(spec=WBAPIClient)
        mock_client.get_sales = AsyncMock(return_value=buyout_data)
        
        # Мокаем WBSalesCRUD
        mock_sales_crud = Mock()
        mock_sales_crud.get_sale_by_sale_id.return_value = None
        mock_sales_crud.create_sale.return_value = Mock()
        
        with patch('app.features.wb_api.sync_service.WBAPIClient', return_value=mock_client):
            with patch('app.features.wb_api.crud_sales.WBSalesCRUD', return_value=mock_sales_crud):
                with patch.object(wb_sync_service, '_process_sale_notification', new_callable=AsyncMock) as mock_notification:
                    result = await wb_sync_service.sync_sales(
                        cabinet=sample_cabinet,
                        client=mock_client,
                        date_from="2025-01-28",
                        date_to="2025-01-28",
                        should_notify=True
                    )
                    
                    # Проверяем, что была создана запись с типом "buyout"
                    create_call_args = mock_sales_crud.create_sale.call_args[0][1]
                    assert create_call_args["type"] == "buyout"
                    assert create_call_args["is_cancel"] == False
    
    @pytest.mark.asyncio
    async def test_sync_sales_return_detection(
        self,
        wb_sync_service,
        sample_cabinet,
        mock_db,
        mock_redis
    ):
        """Тест определения возвратов"""
        # Данные с возвратом
        return_data = [{
            "srid": "sale_456",
            "orderId": "order_789",
            "nmId": 12346,
            "subject": "Test Product Return",
            "brand": "Test Brand",
            "techSize": "L",
            "totalPrice": 1500.0,
            "date": "2025-01-28T13:00:00",
            "isCancel": True,  # Возврат
            "lastChangeDate": "2025-01-28T13:00:00"
        }]
        
        # Мокаем WBAPIClient
        mock_client = Mock(spec=WBAPIClient)
        mock_client.get_sales = AsyncMock(return_value=return_data)
        
        # Мокаем WBSalesCRUD
        mock_sales_crud = Mock()
        mock_sales_crud.get_sale_by_sale_id.return_value = None
        mock_sales_crud.create_sale.return_value = Mock()
        
        with patch('app.features.wb_api.sync_service.WBAPIClient', return_value=mock_client):
            with patch('app.features.wb_api.crud_sales.WBSalesCRUD', return_value=mock_sales_crud):
                with patch.object(wb_sync_service, '_process_sale_notification', new_callable=AsyncMock) as mock_notification:
                    result = await wb_sync_service.sync_sales(
                        cabinet=sample_cabinet,
                        client=mock_client,
                        date_from="2025-01-28",
                        date_to="2025-01-28",
                        should_notify=True
                    )
                    
                    # Проверяем, что была создана запись с типом "return"
                    create_call_args = mock_sales_crud.create_sale.call_args[0][1]
                    assert create_call_args["type"] == "return"
                    assert create_call_args["is_cancel"] == True
    
    @pytest.mark.asyncio
    async def test_sync_sales_integration_with_notifications(
        self,
        wb_sync_service,
        sample_cabinet,
        sample_wb_sales_data,
        mock_db,
        mock_redis
    ):
        """Тест полной интеграции синхронизации с уведомлениями"""
        # Мокаем WBAPIClient
        mock_client = Mock(spec=WBAPIClient)
        mock_client.get_sales = AsyncMock(return_value=sample_wb_sales_data)
        
        # Мокаем WBSalesCRUD
        mock_sales_crud = Mock()
        mock_sales_crud.get_sale_by_sale_id.return_value = None
        mock_sales_crud.create_sale.return_value = Mock()
        
        # Мокаем NotificationService
        mock_notification_service = Mock()
        mock_notification_service.send_test_notification = AsyncMock(return_value={"success": True})
        
        with patch('app.features.wb_api.sync_service.WBAPIClient', return_value=mock_client):
            with patch('app.features.wb_api.crud_sales.WBSalesCRUD', return_value=mock_sales_crud):
                with patch('app.features.notifications.notification_service.NotificationService', return_value=mock_notification_service):
                    with patch.object(wb_sync_service, '_process_sale_notification', new_callable=AsyncMock) as mock_notification:
                        result = await wb_sync_service.sync_sales(
                            cabinet=sample_cabinet,
                            client=mock_client,
                            date_from="2025-01-28",
                            date_to="2025-01-28",
                            should_notify=True
                        )
                        
                        # Проверяем результат
                        assert result["status"] == "success"
                        assert result["records_processed"] == 2
                        assert result["records_created"] == 2
                        
                        # Проверяем, что уведомления были обработаны
                        assert mock_notification.call_count == 2
