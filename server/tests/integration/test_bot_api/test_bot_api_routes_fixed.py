"""
Integration тесты для Bot API routes (исправленная версия)
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from main import app
from app.features.user.models import User
from app.features.wb_api.models import WBCabinet
from app.features.bot_api.service import BotAPIService


class TestBotAPIRoutes:
    """Тесты для Bot API routes"""

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
        return WBCabinet(
            id=1,
            user_id=sample_user.id,
            api_key="test_api_key",
            cabinet_name="Test Cabinet",
            is_active=True
        )

    @pytest.fixture
    def mock_bot_service(self):
        """Фикстура для мока BotAPIService"""
        return AsyncMock(spec=BotAPIService)

    def test_dashboard_success(self, client, sample_user, sample_cabinet, mock_bot_service):
        """Тест успешного получения dashboard"""
        dashboard_data = {
            "success": True,
            "data": {
                "cabinet_name": "Test Cabinet",
                "last_sync": "2025-01-28T14:30:15",
                "status": "active",
                "products": {"total": 150, "active": 120, "moderation": 5, "critical_stocks": 3},
                "orders_today": {"count": 25, "amount": 45000.0, "growth_percent": 15.5, "yesterday_amount": 39000.0},
                "stocks": {"total_quantity": 1250, "critical_count": 3, "zero_count": 1, "attention_needed": 4},
                "reviews": {"total": 89, "average_rating": 4.2, "unanswered": 12, "new_today": 3},
                "recommendations": ["Пополнить остатки 3 товаров", "Ответить на 12 отзывов"]
            },
            "telegram_text": "📊 ДАШБОРД КАБИНЕТА\n\n..."
        }
        
        mock_bot_service.get_dashboard_data.return_value = dashboard_data
        
        with patch('app.features.bot_api.routes.get_bot_service') as mock_get_service:
            mock_get_service.return_value = mock_bot_service
            
            response = client.get(
                "/api/v1/bot/dashboard",
                headers={"X-API-SECRET-KEY": "CnWvwoDwwGKh"},
                params={"telegram_id": sample_user.telegram_id}
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "dashboard" in data

    def test_orders_recent_success(self, client, sample_user, sample_cabinet, mock_bot_service):
        """Тест успешного получения последних заказов"""
        orders_data = {
            "success": True,
            "data": {
                "orders": [
                    {
                        "id": 1,
                        "date": "2025-01-28T14:25:30",
                        "amount": 2500.0,
                        "product_name": "Тестовый товар 1",
                        "brand": "Test Brand",
                        "warehouse_from": "Склад 1",
                        "warehouse_to": "Покупатель",
                        "commission_percent": 5.0,
                        "rating": 4.5
                    }
                ],
                "statistics": {
                    "today_count": 25,
                    "today_amount": 45000.0,
                    "average_check": 1800.0,
                    "growth_percent": 15.5,
                    "amount_growth_percent": 18.2
                },
                "pagination": {
                    "limit": 10,
                    "offset": 0,
                    "total": 25,
                    "has_more": True
                }
            },
            "telegram_text": "📦 ПОСЛЕДНИЕ ЗАКАЗЫ\n\n..."
        }
        
        mock_bot_service.get_recent_orders.return_value = orders_data
        
        with patch('app.features.bot_api.routes.get_bot_service') as mock_get_service:
            mock_get_service.return_value = mock_bot_service
            
            response = client.get(
                "/api/v1/bot/orders/recent",
                headers={"X-API-SECRET-KEY": "CnWvwoDwwGKh"},
                params={"telegram_id": sample_user.telegram_id, "limit": 10}
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "orders" in data

    def test_critical_stocks_success(self, client, sample_user, sample_cabinet, mock_bot_service):
        """Тест успешного получения критических остатков"""
        stocks_data = {
            "success": True,
            "data": {
                "critical_products": [
                    {
                        "nm_id": 12345,
                        "name": "Критичный товар",
                        "brand": "Test Brand",
                        "stocks": {"S": 0, "M": 2, "L": 0, "XL": 1},
                        "critical_sizes": ["S", "L"],
                        "zero_sizes": ["S"],
                        "sales_per_day": 1.5,
                        "price": 1500.0,
                        "commission_percent": 5.0,
                        "days_left": {"S": 0, "L": 0}
                    }
                ],
                "zero_products": [
                    {
                        "nm_id": 67890,
                        "name": "Товар без остатков",
                        "brand": "Test Brand",
                        "stocks": {"S": 0, "M": 0, "L": 0, "XL": 0},
                        "sales_per_day": 0.8,
                        "price": 2000.0,
                        "commission_percent": 5.0
                    }
                ],
                "summary": {
                    "critical_count": 1,
                    "zero_count": 1,
                    "attention_needed": 2,
                    "potential_losses": 5000.0
                },
                "recommendations": ["Срочно пополнить 1 критичных товаров", "Проанализировать 1 товаров с низкими остатками"]
            },
            "telegram_text": "⚠️ КРИТИЧНЫЕ ОСТАТКИ\n\n..."
        }
        
        mock_bot_service.get_critical_stocks.return_value = stocks_data
        
        with patch('app.features.bot_api.routes.get_bot_service') as mock_get_service:
            mock_get_service.return_value = mock_bot_service
            
            response = client.get(
                "/api/v1/bot/stocks/critical",
                headers={"X-API-SECRET-KEY": "CnWvwoDwwGKh"},
                params={"telegram_id": sample_user.telegram_id}
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "stocks" in data

    def test_reviews_summary_success(self, client, sample_user, sample_cabinet, mock_bot_service):
        """Тест успешного получения сводки отзывов"""
        reviews_data = {
            "success": True,
            "data": {
                "new_reviews": [
                    {
                        "id": "rev_001",
                        "product_name": "Тестовый товар 1",
                        "rating": 5,
                        "text": "Отличный товар!",
                        "time_ago": "2 часа назад",
                        "order_id": 12345
                    }
                ],
                "unanswered_questions": [
                    {
                        "id": "q_001",
                        "product_name": "Тестовый товар 2",
                        "text": "Какой размер выбрать?",
                        "time_ago": "1 день назад"
                    }
                ],
                "statistics": {
                    "average_rating": 4.2,
                    "total_reviews": 89,
                    "answered_count": 77,
                    "answered_percent": 86.5,
                    "attention_needed": 12,
                    "new_today": 3
                },
                "recommendations": ["Ответить на 12 отзывов", "Проверить качество товаров с низким рейтингом"]
            },
            "telegram_text": "⭐ ОТЗЫВЫ И ВОПРОСЫ\n\n..."
        }
        
        mock_bot_service.get_reviews_summary.return_value = reviews_data
        
        with patch('app.features.bot_api.routes.get_bot_service') as mock_get_service:
            mock_get_service.return_value = mock_bot_service
            
            response = client.get(
                "/api/v1/bot/reviews/summary",
                headers={"X-API-SECRET-KEY": "CnWvwoDwwGKh"},
                params={"telegram_id": sample_user.telegram_id}
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "reviews" in data

    def test_analytics_sales_success(self, client, sample_user, sample_cabinet, mock_bot_service):
        """Тест успешного получения аналитики продаж"""
        analytics_data = {
            "success": True,
            "data": {
                "sales_periods": {
                    "today": {"count": 25, "amount": 45000.0},
                    "yesterday": {"count": 22, "amount": 39000.0},
                    "7_days": {"count": 180, "amount": 320000.0},
                    "30_days": {"count": 750, "amount": 1350000.0},
                    "90_days": {"count": 2200, "amount": 3950000.0}
                },
                "dynamics": {
                    "yesterday_growth_percent": 15.4,
                    "week_growth_percent": 12.8,
                    "average_check": 1800.0,
                    "conversion_percent": 3.2
                },
                "top_products": [
                    {
                        "nm_id": 12345,
                        "name": "Топ товар 1",
                        "sales_count": 45,
                        "sales_amount": 67500.0,
                        "rating": 4.8,
                        "stocks": {"S": 10, "M": 15, "L": 8, "XL": 5}
                    }
                ],
                "stocks_summary": {
                    "critical_count": 3,
                    "zero_count": 1,
                    "attention_needed": 4,
                    "total_products": 150
                },
                "recommendations": ["Все показатели в норме!", "Рассмотреть увеличение остатков топ-товаров"]
            },
            "telegram_text": "📈 АНАЛИТИКА ПРОДАЖ\n\n..."
        }
        
        mock_bot_service.get_analytics_sales.return_value = analytics_data
        
        with patch('app.features.bot_api.routes.get_bot_service') as mock_get_service:
            mock_get_service.return_value = mock_bot_service
            
            response = client.get(
                "/api/v1/bot/analytics/sales",
                headers={"X-API-SECRET-KEY": "CnWvwoDwwGKh"},
                params={"telegram_id": sample_user.telegram_id, "period": "7d"}
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "analytics" in data

    def test_order_detail_success(self, client, sample_user, sample_cabinet, mock_bot_service):
        """Тест успешного получения деталей заказа"""
        order_detail_data = {
            "success": True,
            "data": {
                "order": {
                    "id": 12345,
                    "date": "2025-01-28T14:25:30",
                    "amount": 2500.0,
                    "product_name": "Тестовый товар 1",
                    "brand": "Test Brand",
                    "warehouse_from": "Склад 1",
                    "warehouse_to": "Покупатель",
                    "commission_percent": 5.0,
                    "rating": 4.5
                }
            },
            "telegram_text": "📦 ДЕТАЛИ ЗАКАЗА #12345\n\n..."
        }
        
        mock_bot_service.get_order_detail.return_value = order_detail_data
        
        with patch('app.features.bot_api.routes.get_bot_service') as mock_get_service:
            mock_get_service.return_value = mock_bot_service
            
            response = client.get(
                "/api/v1/bot/orders/12345",
                headers={"X-API-SECRET-KEY": "CnWvwoDwwGKh"},
                params={"telegram_id": sample_user.telegram_id}
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "order" in data

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
            
            response = client.post(
                "/api/v1/bot/sync/start",
                headers={"X-API-SECRET-KEY": "CnWvwoDwwGKh"},
                params={"telegram_id": sample_user.telegram_id}
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "sync_id" in data

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
            
            response = client.get(
                "/api/v1/bot/sync/status",
                headers={"X-API-SECRET-KEY": "CnWvwoDwwGKh"},
                params={"telegram_id": sample_user.telegram_id}
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "sync_status" in data

    def test_missing_telegram_id_parameter(self, client):
        """Тест отсутствия обязательного параметра telegram_id"""
        response = client.get(
            "/api/v1/bot/dashboard",
            headers={"X-API-SECRET-KEY": "CnWvwoDwwGKh"}
        )
        
        assert response.status_code == 422
        data = response.json()
        assert "telegram_id" in str(data)

    def test_invalid_telegram_id_parameter(self, client):
        """Тест неверного типа параметра telegram_id"""
        response = client.get(
            "/api/v1/bot/dashboard",
            headers={"X-API-SECRET-KEY": "CnWvwoDwwGKh"},
            params={"telegram_id": "invalid"}
        )
        
        assert response.status_code == 422
        data = response.json()
        assert "telegram_id" in str(data)