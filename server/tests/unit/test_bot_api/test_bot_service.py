"""
Unit тесты для Bot API сервиса
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone, timedelta
from app.features.bot_api.service import BotAPIService
from app.features.user.models import User
from app.features.wb_api.models import WBCabinet, WBOrder, WBProduct, WBStock, WBReview


class TestBotAPIService:
    """Тесты для Bot API сервиса"""

    @pytest.fixture
    def mock_db_session(self):
        """Фикстура для мока сессии БД"""
        return Mock()

    @pytest.fixture
    def mock_cache_manager(self):
        """Фикстура для мока кэш-менеджера"""
        return AsyncMock()

    @pytest.fixture
    def mock_sync_service(self):
        """Фикстура для мока сервиса синхронизации"""
        return AsyncMock()

    @pytest.fixture
    def bot_service(self, mock_db_session, mock_cache_manager, mock_sync_service):
        """Фикстура для Bot API сервиса"""
        return BotAPIService(mock_db_session, mock_cache_manager, mock_sync_service)

    @pytest.fixture
    def sample_user(self):
        """Фикстура для тестового пользователя"""
        user = User(
            id=1,
            telegram_id=123456789,
            username="testuser",
            first_name="Тест",
            last_name="Пользователь"
        )
        return user

    @pytest.fixture
    def sample_cabinet(self, sample_user):
        """Фикстура для тестового кабинета"""
        cabinet = WBCabinet(
            id=1,
            user_id=sample_user.id,
            api_key="test_api_key",
            cabinet_name="Test Cabinet",
            is_active=True,
            last_sync_at=datetime.now(timezone.utc) - timedelta(minutes=5)
        )
        cabinet.user = sample_user
        return cabinet

    @pytest.mark.asyncio
    async def test_get_user_cabinet_success(self, bot_service, mock_db_session, sample_user, sample_cabinet):
        """Тест успешного получения кабинета пользователя"""
        # Настраиваем моки для двух запросов: User и WBCabinet
        mock_query = mock_db_session.query
        mock_query.return_value.filter.return_value.first.side_effect = [sample_user, sample_cabinet]
        
        result = await bot_service.get_user_cabinet(sample_user.telegram_id)
        
        assert result == sample_cabinet
        assert mock_db_session.query.call_count == 2  # User + WBCabinet

    @pytest.mark.asyncio
    async def test_get_user_cabinet_not_found(self, bot_service, mock_db_session, sample_user):
        """Тест случая, когда кабинет не найден"""
        mock_db_session.query.return_value.filter.return_value.first.return_value = None
        
        result = await bot_service.get_user_cabinet(sample_user.telegram_id)
        
        assert result is None

    @pytest.mark.asyncio
    async def test_get_dashboard_data_success(self, bot_service, mock_db_session, sample_cabinet, mock_cache_manager):
        """Тест успешного получения данных dashboard"""
        # Мокаем данные из кэша
        mock_cache_manager.get_cached_data.return_value = {
            "cabinet_name": "Test Cabinet",
            "last_sync": "2 мин назад",
            "status": "Активен",
            "products": {"total": 45, "active": 42, "moderation": 3, "critical_stocks": 3},
            "orders_today": {"count": 19, "amount": 26790, "yesterday_count": 24, "yesterday_amount": 33840, "growth_percent": 12},
            "stocks": {"critical_count": 3, "zero_count": 1, "attention_needed": 2, "top_product": "Test Product"},
            "reviews": {"new_count": 5, "average_rating": 4.8, "unanswered": 2, "total": 214},
            "recommendations": ["Test recommendation"]
        }
        
        result = await bot_service.get_dashboard_data(sample_cabinet)
        
        assert result["success"] is True
        assert "data" in result
        assert "telegram_text" in result
        assert result["data"]["cabinet_name"] == "Test Cabinet"
        mock_cache_manager.get_cached_data.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_dashboard_data_cache_miss(self, bot_service, mock_db_session, sample_cabinet, mock_cache_manager):
        """Тест получения данных dashboard при отсутствии в кэше"""
        mock_cache_manager.get_cached_data.return_value = None
        
        # Мокаем данные из БД
        with patch.object(bot_service, '_fetch_dashboard_from_db') as mock_fetch:
            mock_fetch.return_value = {
                "cabinet_name": "Test Cabinet",
                "last_sync": "2 мин назад",
                "status": "Активен",
                "products": {"total": 45, "active": 42, "moderation": 3, "critical_stocks": 3},
                "orders_today": {"count": 19, "amount": 26790, "yesterday_count": 24, "yesterday_amount": 33840, "growth_percent": 12},
                "stocks": {"critical_count": 3, "zero_count": 1, "attention_needed": 2, "top_product": "Test Product"},
                "reviews": {"new_count": 5, "average_rating": 4.8, "unanswered": 2, "total": 214},
                "recommendations": ["Test recommendation"]
            }
            
            result = await bot_service.get_dashboard_data(sample_cabinet)
            
            assert result["success"] is True
            assert "data" in result
            assert "telegram_text" in result
            mock_fetch.assert_called_once_with(sample_cabinet)

    @pytest.mark.asyncio
    async def test_get_recent_orders_success(self, bot_service, mock_db_session, sample_cabinet, mock_cache_manager):
        """Тест успешного получения последних заказов"""
        mock_orders_data = {
            "orders": [
                {
                    "id": 154,
                    "date": "2025-10-03T12:48:00",
                    "amount": 1410,
                    "product_name": "Test Product (S)",
                    "brand": "Test Brand",
                    "warehouse_from": "Test Warehouse",
                    "warehouse_to": "Test Destination",
                    "commission_percent": 29.5,
                    "rating": 4.8
                }
            ],
            "statistics": {
                "today_count": 19,
                "today_amount": 26790,
                "average_check": 1410,
                "growth_percent": 12,
                "amount_growth_percent": 8
            },
            "pagination": {
                "limit": 10,
                "offset": 0,
                "total": 19,
                "has_more": False
            }
        }
        
        mock_cache_manager.get_cached_data.return_value = mock_orders_data
        
        result = await bot_service.get_recent_orders(sample_cabinet, limit=10, offset=0)
        
        assert result["success"] is True
        assert "data" in result
        assert "telegram_text" in result
        assert len(result["data"]["orders"]) == 1
        assert result["data"]["orders"][0]["id"] == 154

    @pytest.mark.asyncio
    async def test_get_critical_stocks_success(self, bot_service, mock_db_session, sample_cabinet, mock_cache_manager):
        """Тест успешного получения критичных остатков"""
        mock_stocks_data = {
            "critical_products": [
                {
                    "nm_id": 270591287,
                    "name": "Test Product",
                    "brand": "Test Brand",
                    "stocks": {"S": 13, "M": 1, "L": 0, "XL": 0},
                    "critical_sizes": ["M"],
                    "zero_sizes": ["L", "XL"],
                    "sales_per_day": 29.29,
                    "price": 1410,
                    "commission_percent": 29.5,
                    "days_left": {"M": 0, "S": 1}
                }
            ],
            "zero_products": [],
            "summary": {
                "critical_count": 1,
                "zero_count": 0,
                "attention_needed": 1,
                "potential_losses": 29.29
            },
            "recommendations": ["Test recommendation"]
        }
        
        mock_cache_manager.get_cached_data.return_value = mock_stocks_data
        
        result = await bot_service.get_critical_stocks(sample_cabinet, limit=20, offset=0)
        
        assert result["success"] is True
        assert "data" in result
        assert "telegram_text" in result
        assert len(result["data"]["critical_products"]) == 1
        assert result["data"]["critical_products"][0]["nm_id"] == 270591287

    @pytest.mark.asyncio
    async def test_get_reviews_summary_success(self, bot_service, mock_db_session, sample_cabinet, mock_cache_manager):
        """Тест успешного получения сводки отзывов"""
        mock_reviews_data = {
            "new_reviews": [
                {
                    "id": "154",
                    "product_name": "Test Product",
                    "rating": 5,
                    "text": "Great product!",
                    "time_ago": "2 часа назад",
                    "order_id": 154
                }
            ],
            "unanswered_questions": [
                {
                    "id": "q1",
                    "product_name": "Test Product 2",
                    "text": "What size should I choose?",
                    "time_ago": "3 часа назад"
                }
            ],
            "statistics": {
                "average_rating": 4.8,
                "total_reviews": 214,
                "answered_count": 212,
                "answered_percent": 99,
                "attention_needed": 1,
                "new_today": 5
            },
            "recommendations": ["Test recommendation"]
        }
        
        mock_cache_manager.get_cached_data.return_value = mock_reviews_data
        
        result = await bot_service.get_reviews_summary(sample_cabinet, limit=10, offset=0)
        
        assert result["success"] is True
        assert "data" in result
        assert "telegram_text" in result
        assert len(result["data"]["new_reviews"]) == 1
        assert result["data"]["new_reviews"][0]["id"] == "154"

    @pytest.mark.asyncio
    async def test_get_analytics_sales_success(self, bot_service, mock_db_session, sample_cabinet, mock_cache_manager):
        """Тест успешного получения аналитики продаж"""
        mock_analytics_data = {
            "sales_periods": {
                "today": {"count": 19, "amount": 26790},
                "yesterday": {"count": 24, "amount": 33840},
                "7_days": {"count": 156, "amount": 234500},
                "30_days": {"count": 541, "amount": 892300},
                "90_days": {"count": 686, "amount": 1156800}
            },
            "dynamics": {
                "yesterday_growth_percent": -21,
                "week_growth_percent": 12,
                "average_check": 1410,
                "conversion_percent": 3.2
            },
            "top_products": [
                {
                    "nm_id": 270591287,
                    "name": "Test Product",
                    "sales_count": 73,
                    "sales_amount": 46800,
                    "rating": 4.8,
                    "stocks": {"S": 13, "M": 1, "L": 0, "XL": 0}
                }
            ],
            "stocks_summary": {
                "critical_count": 3,
                "zero_count": 1,
                "attention_needed": 2,
                "total_products": 45
            },
            "recommendations": ["Test recommendation"]
        }
        
        mock_cache_manager.get_cached_data.return_value = mock_analytics_data
        
        result = await bot_service.get_analytics_sales(sample_cabinet, period="7d")
        
        assert result["success"] is True
        assert "data" in result
        assert "telegram_text" in result
        assert result["data"]["sales_periods"]["today"]["count"] == 19

    @pytest.mark.asyncio
    async def test_start_sync_success(self, bot_service, mock_db_session, sample_cabinet, mock_sync_service):
        """Тест успешного запуска синхронизации"""
        mock_sync_service.sync_cabinet.return_value = {
            "status": "success",
            "sync_id": "sync_12345",
            "message": "Синхронизация запущена"
        }
        
        result = await bot_service.start_sync(sample_cabinet)
        
        assert result["success"] is True
        assert "data" in result
        assert "telegram_text" in result
        assert result["data"]["status"] == "started"
        mock_sync_service.sync_cabinet.assert_called_once_with(sample_cabinet)

    @pytest.mark.asyncio
    async def test_get_sync_status_success(self, bot_service, mock_db_session, sample_cabinet, mock_sync_service):
        """Тест успешного получения статуса синхронизации"""
        mock_sync_status = {
            "last_sync": "2025-01-28T14:30:15",
            "status": "completed",
            "duration_seconds": 45,
            "cabinets_processed": 1,
            "updates": {
                "orders": {"new": 3, "total_today": 19},
                "stocks": {"updated": 12},
                "reviews": {"new": 2, "total_today": 5},
                "products": {"changed": 0},
                "analytics": {"recalculated": True}
            },
            "next_sync": "2025-01-28T14:31:00",
            "sync_mode": "automatic",
            "interval_seconds": 60,
            "statistics": {
                "successful_today": 1440,
                "errors_today": 0,
                "average_duration": 42,
                "last_error": None
            }
        }
        
        mock_sync_service.get_sync_status.return_value = mock_sync_status
        
        result = await bot_service.get_sync_status(sample_cabinet)
        
        assert result["success"] is True
        assert "data" in result
        assert "telegram_text" in result
        assert result["data"]["status"] == "completed"
        mock_sync_service.get_sync_status.assert_called_once_with()

    @pytest.mark.asyncio
    async def test_error_handling_wb_api_unavailable(self, bot_service, mock_db_session, sample_cabinet, mock_cache_manager):
        """Тест обработки ошибки недоступности WB API"""
        mock_cache_manager.get_cached_data.return_value = None
        
        with patch.object(bot_service, '_fetch_dashboard_from_db') as mock_fetch:
            mock_fetch.side_effect = Exception("WB API unavailable")
            
            result = await bot_service.get_dashboard_data(sample_cabinet)
            
            assert result["success"] is False
            assert "error" in result
            assert "WB API временно недоступен" in result["error"]

    @pytest.mark.asyncio
    async def test_error_handling_database_error(self, bot_service, mock_db_session, sample_cabinet, mock_cache_manager):
        """Тест обработки ошибки базы данных"""
        mock_cache_manager.get_cached_data.return_value = None
        
        with patch.object(bot_service, '_fetch_dashboard_from_db') as mock_fetch:
            mock_fetch.side_effect = Exception("Database connection failed")
            
            result = await bot_service.get_dashboard_data(sample_cabinet)
            
            assert result["success"] is False
            assert "error" in result
            assert "Ошибка сервера" in result["error"]

    @pytest.mark.asyncio
    async def test_error_handling_general_error(self, bot_service, mock_db_session, sample_cabinet, mock_cache_manager):
        """Тест обработки общей ошибки"""
        mock_cache_manager.get_cached_data.return_value = None
        
        with patch.object(bot_service, '_fetch_dashboard_from_db') as mock_fetch:
            mock_fetch.side_effect = Exception("Unknown error")
            
            result = await bot_service.get_dashboard_data(sample_cabinet)
            
            assert result["success"] is False
            assert "error" in result
            assert "Ошибка сервера" in result["error"]

    @pytest.mark.asyncio
    async def test_pagination_handling(self, bot_service, mock_db_session, sample_cabinet, mock_cache_manager):
        """Тест обработки пагинации"""
        mock_orders_data = {
            "orders": [{"id": i} for i in range(10)],
            "pagination": {
                "limit": 10,
                "offset": 0,
                "total": 50,
                "has_more": True
            }
        }
        
        mock_cache_manager.get_cached_data.return_value = mock_orders_data
        
        result = await bot_service.get_recent_orders(sample_cabinet, limit=10, offset=0)
        
        assert result["success"] is True
        assert result["data"]["pagination"]["has_more"] is True
        assert result["data"]["pagination"]["total"] == 50

    @pytest.mark.asyncio
    async def test_cache_fallback_behavior(self, bot_service, mock_db_session, sample_cabinet, mock_cache_manager):
        """Тест поведения при отсутствии кэша"""
        mock_cache_manager.get_cached_data.return_value = None
        
        with patch.object(bot_service, '_fetch_dashboard_from_db') as mock_fetch:
            mock_fetch.return_value = {"test": "data"}
            
            result = await bot_service.get_dashboard_data(sample_cabinet)
            
            assert result["success"] is True
            mock_fetch.assert_called_once_with(sample_cabinet)
            mock_cache_manager.set_cached_data.assert_called_once()