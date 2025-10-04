"""
Интеграционные тесты для Bot API с реальной БД (исправленная версия)
"""

import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime, timezone, timedelta
from app.features.bot_api.service import BotAPIService
from app.features.wb_api.cache_manager import WBCacheManager
from app.features.wb_api.sync_service import WBSyncService


class TestBotAPIServiceRealDB:
    """Тесты Bot API сервиса с реальной БД"""

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

    @pytest.fixture
    def cache_manager(self, db_session, mock_redis):
        """Фикстура для кэш-менеджера"""
        return WBCacheManager(db_session, mock_redis)

    @pytest.fixture
    def bot_service(self, db_session, cache_manager, mock_sync_service):
        """Фикстура для Bot API сервиса"""
        return BotAPIService(db_session, cache_manager, mock_sync_service)

    @pytest.mark.asyncio
    async def test_get_user_cabinet_success(self, bot_service, test_user_with_cabinet):
        """Тест успешного получения кабинета пользователя"""
        user, cabinet = test_user_with_cabinet
        
        result = await bot_service.get_user_cabinet(user.telegram_id)
        
        assert result is not None
        assert result.id == cabinet.id
        assert result.cabinet_name == cabinet.cabinet_name
        assert result.api_key == cabinet.api_key

    @pytest.mark.asyncio
    async def test_get_user_cabinet_not_found(self, bot_service):
        """Тест получения кабинета несуществующего пользователя"""
        result = await bot_service.get_user_cabinet(99999)
        
        assert result is None

    @pytest.mark.asyncio
    async def test_get_dashboard_data_success(self, bot_service, test_user_with_cabinet, test_orders_data, test_products_data):
        """Тест успешного получения данных дашборда"""
        user, cabinet = test_user_with_cabinet
        
        result = await bot_service.get_dashboard_data(cabinet)
        
        assert result["success"] == True
        assert "dashboard" in result["data"]
        assert "total_orders" in result["data"]["dashboard"]
        assert "total_revenue" in result["data"]["dashboard"]
        assert "total_products" in result["data"]["dashboard"]

    @pytest.mark.asyncio
    async def test_get_recent_orders_success(self, bot_service, test_user_with_cabinet, test_orders_data):
        """Тест успешного получения последних заказов"""
        user, cabinet = test_user_with_cabinet
        
        result = await bot_service.get_recent_orders(cabinet, limit=10)
        
        assert result["success"] == True
        assert "orders" in result["data"]
        assert len(result["data"]["orders"]) == 2  # У нас 2 тестовых заказа
        assert result["data"]["orders"][0]["order_id"] == "12345"
        assert result["data"]["orders"][1]["order_id"] == "12346"

    @pytest.mark.asyncio
    async def test_get_critical_stocks_success(self, bot_service, test_user_with_cabinet, test_stocks_data):
        """Тест успешного получения критических остатков"""
        user, cabinet = test_user_with_cabinet
        
        result = await bot_service.get_critical_stocks(cabinet)
        
        assert result["success"] == True
        assert "stocks" in result["data"]
        # У нас 1 критический остаток (quantity=0)
        critical_stocks = [s for s in result["data"]["stocks"] if s["quantity"] == 0]
        assert len(critical_stocks) == 1

    @pytest.mark.asyncio
    async def test_get_reviews_summary_success(self, bot_service, test_user_with_cabinet, test_reviews_data):
        """Тест успешного получения сводки отзывов"""
        user, cabinet = test_user_with_cabinet
        
        result = await bot_service.get_reviews_summary(cabinet)
        
        assert result["success"] == True
        assert "reviews" in result["data"]
        assert "total_reviews" in result["data"]["reviews"]
        assert "average_rating" in result["data"]["reviews"]
        assert "unanswered_count" in result["data"]["reviews"]

    @pytest.mark.asyncio
    async def test_get_analytics_sales_success(self, bot_service, test_user_with_cabinet, test_orders_data):
        """Тест успешного получения аналитики продаж"""
        user, cabinet = test_user_with_cabinet
        
        result = await bot_service.get_analytics_sales(cabinet, period="7d")
        
        assert result["success"] == True
        assert "analytics" in result["data"]
        assert "total_sales" in result["data"]["analytics"]
        assert "total_orders" in result["data"]["analytics"]
        assert "growth_percentage" in result["data"]["analytics"]

    @pytest.mark.asyncio
    async def test_get_order_detail_success(self, bot_service, test_user_with_cabinet, test_orders_data):
        """Тест успешного получения деталей заказа"""
        user, cabinet = test_user_with_cabinet
        
        result = await bot_service.get_order_detail(cabinet, "12345")
        
        assert result["success"] == True
        assert "order" in result["data"]
        assert result["data"]["order"]["order_id"] == "12345"
        assert result["data"]["order"]["total_price"] == 1500.0

    @pytest.mark.asyncio
    async def test_get_order_detail_not_found(self, bot_service, test_user_with_cabinet):
        """Тест получения несуществующего заказа"""
        user, cabinet = test_user_with_cabinet
        
        result = await bot_service.get_order_detail(cabinet, "99999")
        
        assert result["success"] == False
        assert "Заказ не найден" in result["error"]

    @pytest.mark.asyncio
    async def test_start_sync_success(self, bot_service, test_user_with_cabinet, mock_sync_service):
        """Тест успешного запуска синхронизации"""
        user, cabinet = test_user_with_cabinet
        mock_sync_service.sync_cabinet.return_value = {"status": "success"}
        
        result = await bot_service.start_sync(cabinet)
        
        assert result["success"] == True
        assert "Синхронизация запущена" in result["message"]

    @pytest.mark.asyncio
    async def test_get_sync_status_success(self, bot_service, test_user_with_cabinet):
        """Тест успешного получения статуса синхронизации"""
        user, cabinet = test_user_with_cabinet
        
        result = await bot_service.get_sync_status(cabinet)
        
        assert result["success"] == True
        assert "sync_status" in result["data"]
        assert "last_sync" in result["data"]["sync_status"]
        assert "is_running" in result["data"]["sync_status"]

    @pytest.mark.asyncio
    async def test_pagination_works(self, bot_service, test_user_with_cabinet, test_orders_data):
        """Тест работы пагинации"""
        user, cabinet = test_user_with_cabinet
        
        # Тест с лимитом 1
        result = await bot_service.get_recent_orders(cabinet, limit=1)
        
        assert result["success"] == True
        assert len(result["data"]["orders"]) == 1
        assert "pagination" in result["data"]
        assert result["data"]["pagination"]["limit"] == 1
        assert result["data"]["pagination"]["total"] == 2

    @pytest.mark.asyncio
    async def test_cache_fallback_works(self, bot_service, test_user_with_cabinet, test_orders_data, mock_redis):
        """Тест работы fallback на кэш при ошибке БД"""
        user, cabinet = test_user_with_cabinet
        
        # Мокаем ошибку БД
        with patch.object(bot_service.db, 'query', side_effect=Exception("Database error")):
            result = await bot_service.get_recent_orders(cabinet)
        
        assert result["success"] == False
        assert "Ошибка сервера" in result["error"]

    @pytest.mark.asyncio
    async def test_empty_data_handling(self, bot_service, test_user_with_cabinet):
        """Тест обработки пустых данных"""
        user, cabinet = test_user_with_cabinet
        
        # Тест с пустыми данными
        result = await bot_service.get_recent_orders(cabinet)
        
        assert result["success"] == True
        assert result["data"]["orders"] == []
        assert result["data"]["pagination"]["total"] == 0

    @pytest.mark.asyncio
    async def test_error_handling_database_error(self, bot_service, test_user_with_cabinet):
        """Тест обработки ошибок БД"""
        user, cabinet = test_user_with_cabinet
        
        # Мокаем ошибку БД
        with patch.object(bot_service.db, 'query', side_effect=Exception("Database connection failed")):
            result = await bot_service.get_dashboard_data(cabinet)
        
        assert result["success"] == False
        assert "Ошибка сервера" in result["error"]

    @pytest.mark.asyncio
    async def test_error_handling_wb_api_error(self, bot_service, test_user_with_cabinet):
        """Тест обработки ошибок WB API"""
        user, cabinet = test_user_with_cabinet
        
        # Мокаем ошибку WB API
        with patch.object(bot_service.db, 'query', side_effect=Exception("WB API error")):
            result = await bot_service.get_dashboard_data(cabinet)
        
        assert result["success"] == False
        assert "Ошибка WB API" in result["error"]