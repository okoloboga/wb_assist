"""
Интеграционные тесты для Bot API endpoints с реальной БД
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from main import app


class TestBotAPIEndpointsReal:
    """Тесты Bot API endpoints с реальной БД"""

    @pytest.fixture
    def client(self):
        """Фикстура для тестового клиента"""
        return TestClient(app)

    @pytest.fixture
    def mock_redis(self):
        """Фикстура с моком Redis"""
        redis = AsyncMock()
        redis.get.return_value = None
        redis.set.return_value = True
        redis.ping.return_value = True
        return redis

    @pytest.fixture
    def mock_sync_service(self):
        """Фикстура с моком сервиса синхронизации"""
        return AsyncMock()

    def test_dashboard_endpoint_success(self, client, test_user_with_cabinet, test_orders_data, test_products_data):
        """Тест успешного получения дашборда"""
        user, cabinet = test_user_with_cabinet
        
        with patch('app.features.bot_api.routes.WBCacheManager') as mock_cache_class, \
             patch('app.features.bot_api.routes.WBSyncService') as mock_sync_class:
            
            mock_cache = AsyncMock()
            mock_cache_class.return_value = mock_cache
            
            mock_sync = AsyncMock()
            mock_sync_class.return_value = mock_sync
            
            response = client.get(f"/bot/dashboard?telegram_id={user.telegram_id}")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "dashboard" in data
            assert "total_orders" in data["dashboard"]

    def test_orders_recent_endpoint_success(self, client, test_user_with_cabinet, test_orders_data):
        """Тест успешного получения последних заказов"""
        user, cabinet = test_user_with_cabinet
        
        with patch('app.features.bot_api.routes.WBCacheManager') as mock_cache_class, \
             patch('app.features.bot_api.routes.WBSyncService') as mock_sync_class:
            
            mock_cache = AsyncMock()
            mock_cache_class.return_value = mock_cache
            
            mock_sync = AsyncMock()
            mock_sync_class.return_value = mock_sync
            
            response = client.get(f"/bot/orders/recent?telegram_id={user.telegram_id}&limit=10")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "orders" in data
            assert len(data["orders"]) == 2

    def test_orders_detail_endpoint_success(self, client, test_user_with_cabinet, test_orders_data):
        """Тест успешного получения деталей заказа"""
        user, cabinet = test_user_with_cabinet
        
        with patch('app.features.bot_api.routes.WBCacheManager') as mock_cache_class, \
             patch('app.features.bot_api.routes.WBSyncService') as mock_sync_class:
            
            mock_cache = AsyncMock()
            mock_cache_class.return_value = mock_cache
            
            mock_sync = AsyncMock()
            mock_sync_class.return_value = mock_sync
            
            response = client.get(f"/bot/orders/12345?telegram_id={user.telegram_id}")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "order" in data
            assert data["order"]["order_id"] == "12345"

    def test_stocks_critical_endpoint_success(self, client, test_user_with_cabinet, test_stocks_data):
        """Тест успешного получения критических остатков"""
        user, cabinet = test_user_with_cabinet
        
        with patch('app.features.bot_api.routes.WBCacheManager') as mock_cache_class, \
             patch('app.features.bot_api.routes.WBSyncService') as mock_sync_class:
            
            mock_cache = AsyncMock()
            mock_cache_class.return_value = mock_cache
            
            mock_sync = AsyncMock()
            mock_sync_class.return_value = mock_sync
            
            response = client.get(f"/bot/stocks/critical?telegram_id={user.telegram_id}")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "stocks" in data

    def test_reviews_summary_endpoint_success(self, client, test_user_with_cabinet, test_reviews_data):
        """Тест успешного получения сводки отзывов"""
        user, cabinet = test_user_with_cabinet
        
        with patch('app.features.bot_api.routes.WBCacheManager') as mock_cache_class, \
             patch('app.features.bot_api.routes.WBSyncService') as mock_sync_class:
            
            mock_cache = AsyncMock()
            mock_cache_class.return_value = mock_cache
            
            mock_sync = AsyncMock()
            mock_sync_class.return_value = mock_sync
            
            response = client.get(f"/bot/reviews/summary?telegram_id={user.telegram_id}")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "reviews" in data

    def test_analytics_sales_endpoint_success(self, client, test_user_with_cabinet, test_orders_data):
        """Тест успешного получения аналитики продаж"""
        user, cabinet = test_user_with_cabinet
        
        with patch('app.features.bot_api.routes.WBCacheManager') as mock_cache_class, \
             patch('app.features.bot_api.routes.WBSyncService') as mock_sync_class:
            
            mock_cache = AsyncMock()
            mock_cache_class.return_value = mock_cache
            
            mock_sync = AsyncMock()
            mock_sync_class.return_value = mock_sync
            
            response = client.get(f"/bot/analytics/sales?telegram_id={user.telegram_id}&days=7")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "analytics" in data

    def test_sync_start_endpoint_success(self, client, test_user_with_cabinet, mock_sync_service):
        """Тест успешного запуска синхронизации"""
        user, cabinet = test_user_with_cabinet
        mock_sync_service.sync_cabinet.return_value = {"status": "success"}
        
        with patch('app.features.bot_api.routes.WBCacheManager') as mock_cache_class, \
             patch('app.features.bot_api.routes.WBSyncService') as mock_sync_class:
            
            mock_cache = AsyncMock()
            mock_cache_class.return_value = mock_cache
            
            mock_sync_class.return_value = mock_sync_service
            
            response = client.post(f"/bot/sync/start?telegram_id={user.telegram_id}")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "Синхронизация запущена" in data["message"]

    def test_sync_status_endpoint_success(self, client, test_user_with_cabinet):
        """Тест успешного получения статуса синхронизации"""
        user, cabinet = test_user_with_cabinet
        
        with patch('app.features.bot_api.routes.WBCacheManager') as mock_cache_class, \
             patch('app.features.bot_api.routes.WBSyncService') as mock_sync_class:
            
            mock_cache = AsyncMock()
            mock_cache_class.return_value = mock_cache
            
            mock_sync = AsyncMock()
            mock_sync_class.return_value = mock_sync
            
            response = client.get(f"/bot/sync/status?telegram_id={user.telegram_id}")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "sync_status" in data

    def test_missing_telegram_id_parameter(self, client):
        """Тест ошибки при отсутствии telegram_id"""
        response = client.get("/bot/dashboard")
        
        assert response.status_code == 422  # Validation error

    def test_invalid_telegram_id_parameter(self, client):
        """Тест ошибки при неверном telegram_id"""
        response = client.get("/bot/dashboard?telegram_id=invalid")
        
        assert response.status_code == 422  # Validation error

    def test_user_not_found(self, client):
        """Тест ошибки при несуществующем пользователе"""
        with patch('app.features.bot_api.routes.WBCacheManager') as mock_cache_class, \
             patch('app.features.bot_api.routes.WBSyncService') as mock_sync_class:
            
            mock_cache = AsyncMock()
            mock_cache_class.return_value = mock_cache
            
            mock_sync = AsyncMock()
            mock_sync_class.return_value = mock_sync
            
            response = client.get("/bot/dashboard?telegram_id=99999")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "error"
            assert "Пользователь не найден" in data["message"]

    def test_pagination_parameters(self, client, test_user_with_cabinet, test_orders_data):
        """Тест работы параметров пагинации"""
        user, cabinet = test_user_with_cabinet
        
        with patch('app.features.bot_api.routes.WBCacheManager') as mock_cache_class, \
             patch('app.features.bot_api.routes.WBSyncService') as mock_sync_class:
            
            mock_cache = AsyncMock()
            mock_cache_class.return_value = mock_cache
            
            mock_sync = AsyncMock()
            mock_sync_class.return_value = mock_sync
            
            response = client.get(f"/bot/orders/recent?telegram_id={user.telegram_id}&limit=1&offset=0")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "pagination" in data
            assert data["pagination"]["limit"] == 1
            assert data["pagination"]["offset"] == 0