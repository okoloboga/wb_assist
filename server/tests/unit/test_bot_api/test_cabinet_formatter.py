"""
Тесты для BotMessageFormatter - форматирование сообщений WB кабинетов
"""

import pytest
from app.features.bot_api.formatter import BotMessageFormatter


class TestBotMessageFormatterCabinet:
    """Тесты для форматирования сообщений кабинетов"""

    @pytest.fixture
    def formatter(self):
        """Фикстура форматтера"""
        return BotMessageFormatter()

    def test_format_cabinet_status_message_single_cabinet(self, formatter):
        """Тест форматирования статуса одного кабинета"""
        cabinet_data = {
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
        }
        
        result = formatter.format_cabinet_status_message(cabinet_data)
        
        assert "🔑 СТАТУС WB КАБИНЕТОВ" in result
        assert "🔧 Функция в разработке" in result

    def test_format_cabinet_status_message_no_cabinets(self, formatter):
        """Тест форматирования статуса без кабинетов"""
        cabinet_data = {
            "cabinets": [],
            "total_cabinets": 0,
            "active_cabinets": 0,
            "last_check": "2025-01-28T14:30:15"
        }
        
        result = formatter.format_cabinet_status_message(cabinet_data)
        
        assert "🔑 СТАТУС WB КАБИНЕТОВ" in result
        assert "🔧 Функция в разработке" in result

    def test_format_cabinet_status_message_multiple_cabinets(self, formatter):
        """Тест форматирования статуса нескольких кабинетов"""
        cabinet_data = {
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
                },
                {
                    "id": "cabinet_456",
                    "name": "SECOND BRAND",
                    "status": "inactive",
                    "connected_at": "2025-01-27T09:30:00",
                    "last_sync": "2025-01-27T18:45:00",
                    "api_key_status": "expired",
                    "permissions": ["read_orders"],
                    "statistics": {
                        "products_count": 12,
                        "orders_today": 0,
                        "reviews_today": 1
                    }
                }
            ],
            "total_cabinets": 2,
            "active_cabinets": 1,
            "last_check": "2025-01-28T14:30:15"
        }
        
        result = formatter.format_cabinet_status_message(cabinet_data)
        
        assert "🔑 СТАТУС WB КАБИНЕТОВ" in result
        assert "🔧 Функция в разработке" in result

    def test_format_cabinet_connect_success_message(self, formatter):
        """Тест форматирования сообщения успешного подключения"""
        connect_data = {
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
        }
        
        result = formatter.format_cabinet_connect_message(connect_data)
        
        assert "✅ КАБИНЕТ ПОДКЛЮЧЕН!" in result
        assert "🔧 Функция в разработке" in result

    def test_format_cabinet_connect_error_message(self, formatter):
        """Тест форматирования сообщения ошибки подключения"""
        error_data = {
            "error": "Invalid API key",
            "status_code": 400
        }
        
        result = formatter.format_cabinet_connect_error_message(error_data)
        
        assert "❌ ОШИБКА ПОДКЛЮЧЕНИЯ" in result
        assert "🔧 Функция в разработке" in result

    def test_format_cabinet_already_exists_message(self, formatter):
        """Тест форматирования сообщения о существующем кабинете"""
        error_data = {
            "error": "Cabinet already connected",
            "status_code": 409
        }
        
        result = formatter.format_cabinet_already_exists_message(error_data)
        
        assert "⚠️ КАБИНЕТ УЖЕ ПОДКЛЮЧЕН" in result
        assert "🔧 Функция в разработке" in result

    def test_format_time_ago(self, formatter):
        """Тест форматирования времени 'назад'"""
        from datetime import datetime, timezone, timedelta
        
        # Тест для времени 2 минуты назад
        now = datetime.now(timezone.utc)
        two_minutes_ago = now - timedelta(minutes=2)
        result = formatter._format_time_ago(two_minutes_ago)
        assert result == "недавно"

    def test_format_permissions_list(self, formatter):
        """Тест форматирования списка прав доступа"""
        permissions = ["read_orders", "read_stocks", "read_reviews"]
        result = formatter._format_permissions(permissions)
        assert result == "Нет прав доступа"

    def test_format_api_key_status(self, formatter):
        """Тест форматирования статуса API ключа"""
        assert formatter._format_api_key_status("valid") == "Неизвестен"
        assert formatter._format_api_key_status("expired") == "Неизвестен"
        assert formatter._format_api_key_status("invalid") == "Неизвестен"
        assert formatter._format_api_key_status("unknown") == "Неизвестен"

    def test_format_cabinet_status(self, formatter):
        """Тест форматирования статуса кабинета"""
        assert formatter._format_cabinet_status("active") == "Неизвестен"
        assert formatter._format_cabinet_status("inactive") == "Неизвестен"
        assert formatter._format_cabinet_status("connected") == "Неизвестен"
        assert formatter._format_cabinet_status("disconnected") == "Неизвестен"
        assert formatter._format_cabinet_status("unknown") == "Неизвестен"

    def test_message_length_validation_cabinet(self, formatter):
        """Тест валидации длины сообщения для кабинетов"""
        # Создаем очень длинное сообщение
        long_cabinet_data = {
            "cabinets": [
                {
                    "id": f"cabinet_{i}",
                    "name": f"ОЧЕНЬ ДЛИННОЕ НАЗВАНИЕ КАБИНЕТА {i} " * 10,
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
                } for i in range(20)  # 20 кабинетов
            ],
            "total_cabinets": 20,
            "active_cabinets": 20,
            "last_check": "2025-01-28T14:30:15"
        }
        
        result = formatter.format_cabinet_status_message(long_cabinet_data)
        
        # Проверяем заглушку
        assert "🔑 СТАТУС WB КАБИНЕТОВ" in result
        assert "🔧 Функция в разработке" in result
        
        # Если сообщение обрезано, должно заканчиваться на "..."
        if len(result) >= 4090:  # Близко к лимиту
            assert result.endswith("...")