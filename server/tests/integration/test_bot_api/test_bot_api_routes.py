"""
Integration тесты для Bot API routes
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.features.user.models import User
from app.features.wb_api.models import WBCabinet
from app.features.bot_api.service import BotAPIService


class TestBotAPIRoutes:
    """Тесты для Bot API endpoints"""

    @pytest.fixture
    def client(self):
        """Фикстура для тестового клиента"""
        return TestClient(app)

    @pytest.fixture
    def sample_user(self):
        """Фикстура для тестового пользователя"""
        return User(
            id=1,
            telegram_id=123456789,
            username="testuser",
            first_name="Тест",
            last_name="Пользователь"
        )

    @pytest.fixture
    def sample_cabinet(self, sample_user):
        """Фикстура для тестового кабинета"""
        cabinet = WBCabinet(
            id=1,
            user_id=sample_user.id,
            api_key="test_api_key",
            cabinet_name="Test Cabinet",
            is_active=True
        )
        cabinet.user = sample_user
        return cabinet

    @pytest.fixture
    def mock_bot_service(self):
        """Фикстура для мока Bot API сервиса"""
        return AsyncMock(spec=BotAPIService)

    def test_get_dashboard_success(self, client, sample_user, sample_cabinet, mock_bot_service):
        """Тест успешного получения dashboard"""
        dashboard_data = {
            "success": True,
            "data": {
                "cabinet_name": "Test Cabinet",
                "last_sync": "2 мин назад",
                "status": "Активен",
                "products": {"total": 45, "active": 42, "moderation": 3, "critical_stocks": 3},
                "orders_today": {"count": 19, "amount": 26790, "yesterday_count": 24, "yesterday_amount": 33840, "growth_percent": 12},
                "stocks": {"critical_count": 3, "zero_count": 1, "attention_needed": 2, "top_product": "Test Product"},
                "reviews": {"new_count": 5, "average_rating": 4.8, "unanswered": 2, "total": 214},
                "recommendations": ["Test recommendation"]
            },
            "telegram_text": "📊 ВАШ КАБИНЕТ WB\n\nTest Cabinet\n..."
        }
        
        mock_bot_service.get_dashboard_data.return_value = dashboard_data
        
        with patch('app.features.bot_api.routes.get_bot_service') as mock_get_service:
            mock_get_service.return_value = mock_bot_service
            
            with patch('app.features.bot_api.routes.get_user_cabinet') as mock_get_cabinet:
                mock_get_cabinet.return_value = sample_cabinet
                
                response = client.get(
                    "/api/v1/bot/dashboard",
                    headers={"X-API-SECRET-KEY": "test-secret-key"},
                    params={"telegram_id": sample_user.telegram_id}
                )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["cabinet_name"] == "Test Cabinet"
        assert "telegram_text" in data

    def test_get_dashboard_user_not_found(self, client, mock_bot_service):
        """Тест получения dashboard для несуществующего пользователя"""
        with patch('app.features.bot_api.routes.get_user_cabinet') as mock_get_cabinet:
            mock_get_cabinet.return_value = None
            
            response = client.get(
                "/api/v1/bot/dashboard",
                headers={"X-API-SECRET-KEY": "test-secret-key"},
                params={"telegram_id": 999999999}
            )
        
        assert response.status_code == 404
        data = response.json()
        assert "WB кабинет не найден" in data["detail"]

    def test_get_dashboard_service_error(self, client, sample_user, sample_cabinet, mock_bot_service):
        """Тест обработки ошибки сервиса при получении dashboard"""
        mock_bot_service.get_dashboard_data.side_effect = Exception("Service error")
        
        with patch('app.features.bot_api.routes.get_bot_service') as mock_get_service:
            mock_get_service.return_value = mock_bot_service
            
            with patch('app.features.bot_api.routes.get_user_cabinet') as mock_get_cabinet:
                mock_get_cabinet.return_value = sample_cabinet
                
                response = client.get(
                    "/api/v1/bot/dashboard",
                    headers={"X-API-SECRET-KEY": "test-secret-key"},
                    params={"telegram_id": sample_user.telegram_id}
                )
        
        assert response.status_code == 500
        data = response.json()
        assert "Ошибка сервера" in data["detail"]

    def test_get_recent_orders_success(self, client, sample_user, sample_cabinet, mock_bot_service):
        """Тест успешного получения последних заказов"""
        orders_data = {
            "success": True,
            "data": {
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
            },
            "telegram_text": "🛒 ПОСЛЕДНИЕ ЗАКАЗЫ\n\n..."
        }
        
        mock_bot_service.get_recent_orders.return_value = orders_data
        
        with patch('app.features.bot_api.routes.get_bot_service') as mock_get_service:
            mock_get_service.return_value = mock_bot_service
            
            with patch('app.features.bot_api.routes.get_user_cabinet') as mock_get_cabinet:
                mock_get_cabinet.return_value = sample_cabinet
                
                response = client.get(
                    "/api/v1/bot/orders/recent",
                    headers={"X-API-SECRET-KEY": "test-secret-key"},
                    params={"telegram_id": sample_user.telegram_id, "limit": 10, "offset": 0}
                )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]["orders"]) == 1
        assert data["data"]["orders"][0]["id"] == 154

    def test_get_recent_orders_with_pagination(self, client, sample_user, sample_cabinet, mock_bot_service):
        """Тест получения заказов с пагинацией"""
        orders_data = {
            "success": True,
            "data": {
                "orders": [],
                "pagination": {
                    "limit": 5,
                    "offset": 10,
                    "total": 50,
                    "has_more": True
                }
            },
            "telegram_text": "🛒 ПОСЛЕДНИЕ ЗАКАЗЫ\n\n..."
        }
        
        mock_bot_service.get_recent_orders.return_value = orders_data
        
        with patch('app.features.bot_api.routes.get_bot_service') as mock_get_service:
            mock_get_service.return_value = mock_bot_service
            
            with patch('app.features.bot_api.routes.get_user_cabinet') as mock_get_cabinet:
                mock_get_cabinet.return_value = sample_cabinet
                
                response = client.get(
                    "/api/v1/bot/orders/recent",
                    headers={"X-API-SECRET-KEY": "test-secret-key"},
                    params={"telegram_id": sample_user.telegram_id, "limit": 5, "offset": 10}
                )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["pagination"]["has_more"] is True
        assert data["data"]["pagination"]["total"] == 50

    def test_get_critical_stocks_success(self, client, sample_user, sample_cabinet, mock_bot_service):
        """Тест успешного получения критичных остатков"""
        stocks_data = {
            "success": True,
            "data": {
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
            },
            "telegram_text": "📦 КРИТИЧНЫЕ ОСТАТКИ\n\n..."
        }
        
        mock_bot_service.get_critical_stocks.return_value = stocks_data
        
        with patch('app.features.bot_api.routes.get_bot_service') as mock_get_service:
            mock_get_service.return_value = mock_bot_service
            
            with patch('app.features.bot_api.routes.get_user_cabinet') as mock_get_cabinet:
                mock_get_cabinet.return_value = sample_cabinet
                
                response = client.get(
                    "/api/v1/bot/stocks/critical",
                    headers={"X-API-SECRET-KEY": "test-secret-key"},
                    params={"telegram_id": sample_user.telegram_id, "limit": 20, "offset": 0}
                )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]["critical_products"]) == 1
        assert data["data"]["critical_products"][0]["nm_id"] == 270591287

    def test_get_reviews_summary_success(self, client, sample_user, sample_cabinet, mock_bot_service):
        """Тест успешного получения сводки отзывов"""
        reviews_data = {
            "success": True,
            "data": {
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
            },
            "telegram_text": "⭐ ОТЗЫВЫ И ВОПРОСЫ\n\n..."
        }
        
        mock_bot_service.get_reviews_summary.return_value = reviews_data
        
        with patch('app.features.bot_api.routes.get_bot_service') as mock_get_service:
            mock_get_service.return_value = mock_bot_service
            
            with patch('app.features.bot_api.routes.get_user_cabinet') as mock_get_cabinet:
                mock_get_cabinet.return_value = sample_cabinet
                
                response = client.get(
                    "/api/v1/bot/reviews/summary",
                    headers={"X-API-SECRET-KEY": "test-secret-key"},
                    params={"telegram_id": sample_user.telegram_id, "limit": 10, "offset": 0}
                )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]["new_reviews"]) == 1
        assert data["data"]["new_reviews"][0]["id"] == "154"

    def test_get_analytics_sales_success(self, client, sample_user, sample_cabinet, mock_bot_service):
        """Тест успешного получения аналитики продаж"""
        analytics_data = {
            "success": True,
            "data": {
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
            },
            "telegram_text": "📈 АНАЛИТИКА ПРОДАЖ\n\n..."
        }
        
        mock_bot_service.get_analytics_sales.return_value = analytics_data
        
        with patch('app.features.bot_api.routes.get_bot_service') as mock_get_service:
            mock_get_service.return_value = mock_bot_service
            
            with patch('app.features.bot_api.routes.get_user_cabinet') as mock_get_cabinet:
                mock_get_cabinet.return_value = sample_cabinet
                
                response = client.get(
                    "/api/v1/bot/analytics/sales",
                    headers={"X-API-SECRET-KEY": "test-secret-key"},
                    params={"telegram_id": sample_user.telegram_id, "period": "7d"}
                )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["sales_periods"]["today"]["count"] == 19

    def test_start_sync_success(self, client, sample_user, sample_cabinet, mock_bot_service):
        """Тест успешного запуска синхронизации"""
        sync_data = {
            "success": True,
            "data": {
                "sync_id": "sync_12345",
                "status": "started",
                "message": "Синхронизация запущена"
            },
            "telegram_text": "🔄 СИНХРОНИЗАЦИЯ ЗАПУЩЕНА\n\n..."
        }
        
        mock_bot_service.start_sync.return_value = sync_data
        
        with patch('app.features.bot_api.routes.get_bot_service') as mock_get_service:
            mock_get_service.return_value = mock_bot_service
            
            with patch('app.features.bot_api.routes.get_user_cabinet') as mock_get_cabinet:
                mock_get_cabinet.return_value = sample_cabinet
                
                response = client.post(
                    "/api/v1/bot/sync/start",
                    headers={"X-API-SECRET-KEY": "test-secret-key"},
                    params={"telegram_id": sample_user.telegram_id}
                )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["status"] == "started"

    def test_get_sync_status_success(self, client, sample_user, sample_cabinet, mock_bot_service):
        """Тест успешного получения статуса синхронизации"""
        sync_status_data = {
            "success": True,
            "data": {
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
            },
            "telegram_text": "🔄 СИНХРОНИЗАЦИЯ ДАННЫХ\n\n..."
        }
        
        mock_bot_service.get_sync_status.return_value = sync_status_data
        
        with patch('app.features.bot_api.routes.get_bot_service') as mock_get_service:
            mock_get_service.return_value = mock_bot_service
            
            with patch('app.features.bot_api.routes.get_user_cabinet') as mock_get_cabinet:
                mock_get_cabinet.return_value = sample_cabinet
                
                response = client.get(
                    "/api/v1/bot/sync/status",
                    headers={"X-API-SECRET-KEY": "test-secret-key"},
                    params={"telegram_id": sample_user.telegram_id}
                )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["status"] == "completed"

    def test_missing_telegram_id_parameter(self, client):
        """Тест отсутствия обязательного параметра telegram_id"""
        response = client.get(
            "/api/v1/bot/dashboard",
            headers={"X-API-SECRET-KEY": "test-secret-key"}
        )
        
        assert response.status_code == 422
        data = response.json()
        assert "telegram_id" in str(data)

    def test_invalid_telegram_id_parameter(self, client):
        """Тест неверного типа параметра telegram_id"""
        response = client.get(
            "/api/v1/bot/dashboard",
            headers={"X-API-SECRET-KEY": "test-secret-key"},
            params={"telegram_id": "invalid"}
        )
        
        assert response.status_code == 422
        data = response.json()
        assert "telegram_id" in str(data)

    def test_missing_api_secret_key(self, client):
        """Тест отсутствия API Secret Key"""
        response = client.get(
            "/api/v1/bot/dashboard",
            params={"telegram_id": 123456789}
        )
        
        assert response.status_code == 403
        data = response.json()
        assert "Invalid or missing API Secret Key" in data["detail"]

    def test_invalid_api_secret_key(self, client):
        """Тест неверного API Secret Key"""
        response = client.get(
            "/api/v1/bot/dashboard",
            headers={"X-API-SECRET-KEY": "invalid-key"},
            params={"telegram_id": 123456789}
        )
        
        assert response.status_code == 403
        data = response.json()
        assert "Invalid or missing API Secret Key" in data["detail"]

    def test_unauthorized_access(self, client):
        """Тест неавторизованного доступа"""
        response = client.get(
            "/api/v1/bot/dashboard",
            params={"telegram_id": 123456789}
        )
        
        assert response.status_code == 403