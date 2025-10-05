"""
Интеграционные тесты для Bot API - WB кабинеты
"""

import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from main import app


class TestBotAPICabinetRoutes:
    """Тесты для API endpoints WB кабинетов"""

    @pytest.fixture
    def client(self):
        """FastAPI test client"""
        return TestClient(app)

    @pytest.fixture
    def sample_user(self):
        """Тестовый пользователь"""
        from app.features.user.models import User
        return User(
            id=1,
            telegram_id=123456789,
            username="testuser",
            first_name="Тест"
        )

    @pytest.fixture
    def sample_cabinet(self):
        """Тестовый кабинет"""
        from app.features.wb_api.models import WBCabinet
        return WBCabinet(
            id=1,
            user_id=1,
            api_key="test_api_key_123",
            cabinet_name="SLAVALOOK BRAND",
            is_active=True
        )

    @pytest.fixture
    def mock_bot_service(self):
        """Мок BotAPIService"""
        service = AsyncMock()
        return service

    def test_get_cabinet_status_success(self, client, sample_user, sample_cabinet, mock_bot_service):
        """Тест успешного получения статуса кабинетов"""
        cabinet_status_data = {
            "success": True,
            "data": {
                "cabinets": [
                    {
                        "id": "cabinet_123",
                        "name": "SLAVALOOK BRAND",
                        "status": "active",
                        "connected_at": "2025-01-28T10:15:30",
                        "last_sync": "2025-01-28T14:30:15",
                        "api_key_status": "valid",
                        "permissions": ["read_orders", "read_stocks", "read_reviews"],
                        "statistics": {
                            "products_count": 45,
                            "orders_today": 19,
                            "reviews_today": 5
                        }
                    }
                ],
                "total_cabinets": 1,
                "active_cabinets": 1,
                "last_check": "2025-01-28T14:30:15"
            },
            "telegram_text": "🔑 СТАТУС WB КАБИНЕТОВ\n\n✅ ПОДКЛЮЧЕННЫЕ КАБИНЕТЫ (1):\n🏢 SLAVALOOK BRAND\n• Статус: Активен\n• Подключен: 28.01.2025 10:15\n• Последняя синхронизация: 2 мин назад\n• API ключ: Валидный\n• Права: Чтение заказов, остатков, отзывов\n\n📊 СТАТИСТИКА КАБИНЕТА\n• Товаров: 45\n• Заказов сегодня: 19\n• Отзывов сегодня: 5\n\n💡 Кабинет работает корректно"
        }
        
        with patch('app.features.bot_api.routes.get_bot_service') as mock_get_service:
            mock_get_service.return_value = mock_bot_service
            
            with patch('app.features.bot_api.service.BotAPIService.get_user_cabinet', return_value=sample_user):
                with patch('app.features.bot_api.service.BotAPIService.get_cabinet_status', return_value=cabinet_status_data):
                    response = client.get(
                        "/api/v1/bot/cabinets/status",
                        headers={"X-API-SECRET-KEY": "CnWvwoDwwGKh"},
                        params={"telegram_id": sample_user.telegram_id}
                    )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "cabinets" in data
        assert len(data["cabinets"]) == 1
        assert data["cabinets"][0]["name"] == "SLAVALOOK BRAND"

    def test_get_cabinet_status_no_cabinets(self, client, sample_user, mock_bot_service):
        """Тест получения статуса когда кабинетов нет"""
        no_cabinets_data = {
            "success": True,
            "data": {
                "cabinets": [],
                "total_cabinets": 0,
                "active_cabinets": 0,
                "last_check": "2025-01-28T14:30:15"
            },
            "telegram_text": "🔑 СТАТУС WB КАБИНЕТОВ\n\n❌ Нет подключенных кабинетов\n\n💡 Для использования бота необходимо подключить WB кабинет:\n1. Получите API ключ в личном кабинете WB\n2. Используйте команду /connect для подключения\n3. После подключения все функции станут доступны"
        }
        
        mock_bot_service.get_cabinet_status.return_value = no_cabinets_data
        
        with patch('app.features.bot_api.routes.get_bot_service') as mock_get_service:
            mock_get_service.return_value = mock_bot_service
            
            with patch('app.features.bot_api.service.BotAPIService.get_user_cabinet') as mock_get_cabinet:
                mock_get_cabinet.return_value = sample_user
                
                response = client.get(
                    "/api/v1/bot/cabinets/status",
                    headers={"X-API-SECRET-KEY": "CnWvwoDwwGKh"},
                    params={"telegram_id": sample_user.telegram_id}
                )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["total_cabinets"] == 0
        assert data["cabinets"] == []

    def test_connect_cabinet_success(self, client, sample_user, mock_bot_service):
        """Тест успешного подключения кабинета"""
        connect_data = {
            "success": True,
            "data": {
                "cabinet_id": "cabinet_123",
                "cabinet_name": "SLAVALOOK BRAND",
                "status": "connected",
                "connected_at": "2025-01-28T14:30:15",
                "api_key_status": "valid",
                "permissions": ["read_orders", "read_stocks", "read_reviews"],
                "validation": {
                    "api_key_valid": True,
                    "permissions_ok": True,
                    "connection_test": "success",
                    "data_access": "confirmed"
                }
            },
            "telegram_text": "✅ КАБИНЕТ ПОДКЛЮЧЕН!\n\n🏢 SLAVALOOK BRAND\n• Статус: Активен\n• Подключен: 28.01.2025 14:30\n• API ключ: Валидный\n• Права: Чтение заказов, остатков, отзывов\n\n🔍 ПРОВЕРКА ПОДКЛЮЧЕНИЯ\n• API ключ: ✅ Валидный\n• Права доступа: ✅ Подтверждены\n• Тест соединения: ✅ Успешно\n• Доступ к данным: ✅ Подтвержден\n\n🎉 Теперь вы можете пользоваться всеми функциями бота!"
        }
        
        with patch('app.features.bot_api.routes.get_bot_service') as mock_get_service:
            mock_get_service.return_value = mock_bot_service
            
            with patch('app.features.bot_api.service.BotAPIService.get_user_cabinet', return_value=sample_user):
                with patch('app.features.bot_api.service.BotAPIService.connect_cabinet', return_value=connect_data):
                    response = client.post(
                        "/api/v1/bot/cabinets/connect",
                        headers={"X-API-SECRET-KEY": "CnWvwoDwwGKh"},
                        params={"telegram_id": sample_user.telegram_id},
                        json={"api_key": "new_api_key_123"}
                    )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["cabinet_name"] == "SLAVALOOK BRAND"
        assert data["validation"]["api_key_valid"] is True

    def test_connect_cabinet_invalid_key(self, client, sample_user, mock_bot_service):
        """Тест подключения с невалидным API ключом"""
        error_data = {
            "success": False,
            "error": "Invalid API key",
            "status_code": 400,
            "telegram_text": "❌ ОШИБКА ПОДКЛЮЧЕНИЯ\n\n🔑 API ключ недействителен\n\n💡 Возможные причины:\n• Неправильный API ключ\n• Ключ отозван в WB\n• Недостаточно прав доступа\n\n🔄 Попробуйте еще раз:\n1. Проверьте правильность ключа\n2. Убедитесь, что ключ активен\n3. Создайте новый ключ в WB\n\n📞 Если проблема повторяется, обратитесь в поддержку WB"
        }
        
        with patch('app.features.bot_api.routes.get_bot_service') as mock_get_service:
            mock_get_service.return_value = mock_bot_service
            
            with patch('app.features.bot_api.service.BotAPIService.get_user_cabinet', return_value=sample_user):
                with patch('app.features.bot_api.service.BotAPIService.connect_cabinet', return_value=error_data):
                    response = client.post(
                    "/api/v1/bot/cabinets/connect",
                    headers={"X-API-SECRET-KEY": "CnWvwoDwwGKh"},
                    params={"telegram_id": sample_user.telegram_id},
                    json={"api_key": "invalid_key"}
                )
        
        assert response.status_code == 400
        data = response.json()
        assert data["detail"] == "Invalid API key"

    def test_connect_cabinet_already_exists(self, client, sample_user, sample_cabinet, mock_bot_service):
        """Тест подключения когда кабинет уже существует"""
        error_data = {
            "success": False,
            "error": "Cabinet already connected",
            "status_code": 409,
            "telegram_text": "⚠️ КАБИНЕТ УЖЕ ПОДКЛЮЧЕН\n\n🏢 У вас уже есть подключенный WB кабинет\n\n💡 Для подключения нового кабинета:\n1. Сначала отключите текущий кабинет\n2. Затем подключите новый\n\n🔄 Или используйте существующий кабинет для работы с ботом"
        }
        
        with patch('app.features.bot_api.routes.get_bot_service') as mock_get_service:
            mock_get_service.return_value = mock_bot_service
            
            with patch('app.features.bot_api.service.BotAPIService.get_user_cabinet', return_value=sample_user):
                with patch('app.features.bot_api.service.BotAPIService.connect_cabinet', return_value=error_data):
                    response = client.post(
                    "/api/v1/bot/cabinets/connect",
                    headers={"X-API-SECRET-KEY": "CnWvwoDwwGKh"},
                    params={"telegram_id": sample_user.telegram_id},
                    json={"api_key": "another_api_key"}
                )
        
        assert response.status_code == 409
        data = response.json()
        assert data["detail"] == "Cabinet already connected"

    def test_connect_cabinet_missing_api_key(self, client, sample_user):
        """Тест подключения без API ключа"""
        response = client.post(
            "/api/v1/bot/cabinets/connect",
            headers={"X-API-SECRET-KEY": "CnWvwoDwwGKh"},
            params={"telegram_id": sample_user.telegram_id},
            json={}
        )
        
        assert response.status_code == 422

    def test_connect_cabinet_invalid_telegram_id(self, client):
        """Тест подключения с невалидным telegram_id"""
        response = client.post(
            "/api/v1/bot/cabinets/connect",
            headers={"X-API-SECRET-KEY": "CnWvwoDwwGKh"},
            params={"telegram_id": "invalid"},
            json={"api_key": "test_key"}
        )
        
        assert response.status_code == 422

    def test_get_cabinet_status_invalid_telegram_id(self, client):
        """Тест получения статуса с невалидным telegram_id"""
        response = client.get(
            "/api/v1/bot/cabinets/status",
            headers={"X-API-SECRET-KEY": "CnWvwoDwwGKh"},
            params={"telegram_id": "invalid"}
        )
        
        assert response.status_code == 422

    def test_cabinet_endpoints_missing_api_key(self, client, sample_user):
        """Тест endpoints без API ключа"""
        # Тест без заголовка X-API-SECRET-KEY
        response = client.get(
            "/api/v1/bot/cabinets/status",
            params={"telegram_id": sample_user.telegram_id}
        )
        
        assert response.status_code == 403

    def test_cabinet_endpoints_invalid_api_key(self, client, sample_user):
        """Тест endpoints с невалидным API ключом"""
        response = client.get(
            "/api/v1/bot/cabinets/status",
            headers={"X-API-SECRET-KEY": "invalid_key"},
            params={"telegram_id": sample_user.telegram_id}
        )
        
        assert response.status_code == 403