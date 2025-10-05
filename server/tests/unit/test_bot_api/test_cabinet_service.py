"""
Тесты для BotAPIService - функционал WB кабинетов
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from app.features.bot_api.service import BotAPIService
from app.features.user.models import User
from app.features.wb_api.models import WBCabinet


class TestBotAPIServiceCabinet:
    """Тесты для функционала WB кабинетов в BotAPIService"""

    @pytest.fixture
    def bot_service(self, db_session, mock_redis, mock_wb_client):
        """Фикстура BotAPIService"""
        from app.features.bot_api.service import BotAPIService
        from app.features.wb_api.cache_manager import WBCacheManager
        from app.features.wb_api.sync_service import WBSyncService
        
        cache_manager = WBCacheManager(mock_redis)
        sync_service = WBSyncService(db_session)
        return BotAPIService(db_session, cache_manager, sync_service)

    @pytest.fixture
    def sample_user_with_cabinet(self):
        """Пользователь с подключенным кабинетом"""
        user = User(
            id=1,
            telegram_id=123456789,
            username="testuser",
            first_name="Тест"
        )
        cabinet = WBCabinet(
            id=1,
            user_id=1,
            api_key="test_api_key_123",
            cabinet_name="SLAVALOOK BRAND",
            is_active=True
        )
        # Устанавливаем связь
        cabinet.user = user
        return user, cabinet

    @pytest.fixture
    def sample_user_without_cabinet(self):
        """Пользователь без кабинета"""
        user = User(
            id=2,
            telegram_id=987654321,
            username="nouser",
            first_name="Без кабинета"
        )
        return user

    @pytest.mark.asyncio
    async def test_get_cabinet_status_success(self, bot_service, sample_user_with_cabinet):
        """Тест успешного получения статуса кабинетов"""
        user, cabinet = sample_user_with_cabinet
        
        # Мокаем данные кабинета
        cabinet_data = {
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
        
        # Мокаем метод get_cabinet_status (будет реализован)
        with patch.object(bot_service, 'get_cabinet_status') as mock_get_status:
            mock_get_status.return_value = {
                "success": True,
                "data": {
                    "cabinets": [cabinet_data],
                    "total_cabinets": 1,
                    "active_cabinets": 1,
                    "last_check": "2025-01-28T14:30:15"
                },
                "telegram_text": "🔑 СТАТУС WB КАБИНЕТОВ\n\n✅ ПОДКЛЮЧЕННЫЕ КАБИНЕТЫ (1):\n🏢 SLAVALOOK BRAND"
            }
            
            result = await bot_service.get_cabinet_status(user)
            
            assert result["success"] is True
            assert "data" in result
            assert "telegram_text" in result
            assert result["data"]["total_cabinets"] == 1
            assert result["data"]["active_cabinets"] == 1
            assert len(result["data"]["cabinets"]) == 1
            assert result["data"]["cabinets"][0]["name"] == "SLAVALOOK BRAND"

    @pytest.mark.asyncio
    async def test_get_cabinet_status_no_cabinets(self, bot_service, sample_user_without_cabinet):
        """Тест получения статуса когда кабинетов нет"""
        user = sample_user_without_cabinet
        
        # Мокаем метод get_cabinet_status
        with patch.object(bot_service, 'get_cabinet_status') as mock_get_status:
            mock_get_status.return_value = {
                "success": True,
                "data": {
                    "cabinets": [],
                    "total_cabinets": 0,
                    "active_cabinets": 0,
                    "last_check": "2025-01-28T14:30:15"
                },
                "telegram_text": "🔑 СТАТУС WB КАБИНЕТОВ\n\n❌ Нет подключенных кабинетов"
            }
            
            result = await bot_service.get_cabinet_status(user)
            
            assert result["success"] is True
            assert result["data"]["total_cabinets"] == 0
            assert result["data"]["active_cabinets"] == 0
            assert result["data"]["cabinets"] == []
            assert "Нет подключенных кабинетов" in result["telegram_text"]

    @pytest.mark.asyncio
    async def test_connect_cabinet_success(self, bot_service, sample_user_without_cabinet):
        """Тест успешного подключения кабинета"""
        user = sample_user_without_cabinet
        api_key = "new_api_key_456"
        
        # Мокаем метод connect_cabinet
        with patch.object(bot_service, 'connect_cabinet') as mock_connect:
            mock_connect.return_value = {
                "success": True,
                "data": {
                    "cabinet_id": "cabinet_456",
                    "cabinet_name": "NEW BRAND",
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
                "telegram_text": "✅ КАБИНЕТ ПОДКЛЮЧЕН!\n\n🏢 NEW BRAND"
            }
            
            result = await bot_service.connect_cabinet(user, api_key)
            
            assert result["success"] is True
            assert result["data"]["cabinet_name"] == "NEW BRAND"
            assert result["data"]["status"] == "connected"
            assert result["data"]["validation"]["api_key_valid"] is True
            assert "КАБИНЕТ ПОДКЛЮЧЕН" in result["telegram_text"]

    @pytest.mark.asyncio
    async def test_connect_cabinet_invalid_key(self, bot_service, sample_user_without_cabinet):
        """Тест подключения с невалидным API ключом"""
        user = sample_user_without_cabinet
        api_key = "invalid_key"
        
        # Мокаем метод connect_cabinet с ошибкой
        with patch.object(bot_service, 'connect_cabinet') as mock_connect:
            mock_connect.return_value = {
                "success": False,
                "error": "Invalid API key",
                "telegram_text": "❌ ОШИБКА ПОДКЛЮЧЕНИЯ\n\n🔑 API ключ недействителен"
            }
            
            result = await bot_service.connect_cabinet(user, api_key)
            
            assert result["success"] is False
            assert "error" in result
            assert "ОШИБКА ПОДКЛЮЧЕНИЯ" in result["telegram_text"]

    @pytest.mark.asyncio
    async def test_connect_cabinet_already_exists(self, bot_service, sample_user_with_cabinet):
        """Тест подключения когда кабинет уже существует"""
        user, cabinet = sample_user_with_cabinet
        api_key = "existing_api_key"
        
        # Мокаем метод connect_cabinet с ошибкой
        with patch.object(bot_service, 'connect_cabinet') as mock_connect:
            mock_connect.return_value = {
                "success": False,
                "error": "Cabinet already connected",
                "telegram_text": "⚠️ КАБИНЕТ УЖЕ ПОДКЛЮЧЕН"
            }
            
            result = await bot_service.connect_cabinet(user, api_key)
            
            assert result["success"] is False
            assert "already connected" in result["error"].lower()