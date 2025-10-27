"""
Unit тесты для NotificationGenerator - методы для продаж
"""
import pytest
from datetime import datetime, timezone

from app.features.notifications.notification_generator import NotificationGenerator


class TestNotificationGeneratorSales:
    """Тесты для NotificationGenerator - методы продаж"""
    
    @pytest.fixture
    def notification_generator(self):
        """Экземпляр NotificationGenerator"""
        return NotificationGenerator()
    
    def test_generate_sales_notification_new_buyout(self, notification_generator):
        """Тест генерации уведомления о новом выкупе"""
        event = {
            "type": "new_buyout",
            "sale_id": "sale_1",
            "order_id": "order_1",
            "product_name": "Product 1",
            "amount": 1000.0,
            "brand": "Brand 1",
            "size": "M"
        }
        
        notification = notification_generator.generate_sales_notification(event)
        
        assert notification["type"] == "new_buyout"
        assert "💰 Выкуп #order_1" in notification["title"]
        assert "Новый выкуп #order_1" in notification["content"]
        assert "Product 1" in notification["content"]
        assert "Brand 1" in notification["content"]
        assert "1 000₽" in notification["content"]
        assert notification["priority"] == "HIGH"
    
    def test_generate_sales_notification_new_return(self, notification_generator):
        """Тест генерации уведомления о новом возврате"""
        event = {
            "type": "new_return",
            "sale_id": "sale_1",
            "order_id": "order_1",
            "product_name": "Product 1",
            "amount": 500.0,
            "brand": "Brand 1",
            "size": "L"
        }
        
        notification = notification_generator.generate_sales_notification(event)
        
        assert notification["type"] == "new_return"
        assert "🔄 Возврат #order_1" in notification["title"]
        assert "Новый возврат #order_1" in notification["content"]
        assert "Product 1" in notification["content"]
        assert "Brand 1" in notification["content"]
        assert "500₽" in notification["content"]
        assert notification["priority"] == "HIGH"
    
    def test_generate_sales_notification_status_change(self, notification_generator):
        """Тест генерации уведомления об изменении статуса продажи"""
        event = {
            "type": "sale_status_change",
            "sale_id": "sale_1",
            "order_id": "order_1",
            "product_name": "Product 1",
            "previous_status": "pending",
            "current_status": "completed",
            "amount": 1000.0
        }
        
        notification = notification_generator.generate_sales_notification(event)
        
        assert notification["type"] == "sale_status_change"
        assert "📊 Статус изменен #order_1" in notification["title"]
        assert "Статус изменен #order_1" in notification["content"]
        assert "pending -> completed" in notification["content"]
        assert notification["priority"] == "MEDIUM"
    
    def test_generate_sales_notification_cancellation_change(self, notification_generator):
        """Тест генерации уведомления об изменении отмены продажи"""
        event = {
            "type": "sale_cancellation_change",
            "sale_id": "sale_1",
            "order_id": "order_1",
            "product_name": "Product 1",
            "was_cancelled": False,
            "is_cancelled": True,
            "amount": 1000.0
        }
        
        notification = notification_generator.generate_sales_notification(event)
        
        assert notification["type"] == "sale_cancellation_change"
        assert "❌ Отмена изменена #order_1" in notification["title"]
        assert "Продажа отменена #order_1" in notification["content"]
        assert "Статус: Отменена" in notification["content"]
        assert notification["priority"] == "MEDIUM"
    
    def test_generate_sales_notification_unknown_event(self, notification_generator):
        """Тест генерации уведомления о неизвестном событии"""
        event = {
            "type": "unknown_event",
            "sale_id": "sale_1"
        }
        
        notification = notification_generator.generate_sales_notification(event)
        
        assert notification["type"] == "unknown_sales_event"
        assert "❓ Неизвестное событие продажи" in notification["title"]
        assert "unknown_event" in notification["content"]
        assert notification["priority"] == "LOW"
    
    def test_format_new_buyout_content(self, notification_generator):
        """Тест форматирования контента уведомления о новом выкупе"""
        content = notification_generator._format_new_buyout_content(
            "order_1", 1000.0, "Product 1", "Brand 1", "M"
        )
        
        assert "💰 Новый выкуп #order_1" in content
        assert "1 000₽" in content
        assert "Product 1" in content
        assert "Brand 1" in content
        assert "M" in content
    
    def test_format_new_return_content(self, notification_generator):
        """Тест форматирования контента уведомления о новом возврате"""
        content = notification_generator._format_new_return_content(
            "order_1", 500.0, "Product 1", "Brand 1", "L"
        )
        
        assert "🔄 Новый возврат #order_1" in content
        assert "500₽" in content
        assert "Product 1" in content
        assert "Brand 1" in content
        assert "L" in content
    
    def test_format_sale_status_change_content(self, notification_generator):
        """Тест форматирования контента уведомления об изменении статуса"""
        content = notification_generator._format_sale_status_change_content(
            "order_1", "Product 1", "pending", "completed", 1000.0
        )
        
        assert "📊 Статус изменен #order_1" in content
        assert "Product 1" in content
        assert "1 000₽" in content
        assert "pending -> completed" in content
    
    def test_format_sale_cancellation_change_content_cancelled(self, notification_generator):
        """Тест форматирования контента уведомления об отмене продажи"""
        content = notification_generator._format_sale_cancellation_change_content(
            "order_1", "Product 1", False, True, 1000.0
        )
        
        assert "❌ Продажа отменена #order_1" in content
        assert "Product 1" in content
        assert "1 000₽" in content
        assert "Статус: Отменена" in content
    
    def test_format_sale_cancellation_change_content_restored(self, notification_generator):
        """Тест форматирования контента уведомления о восстановлении продажи"""
        content = notification_generator._format_sale_cancellation_change_content(
            "order_1", "Product 1", True, False, 1000.0
        )
        
        assert "❌ Продажа восстановлена #order_1" in content
        assert "Product 1" in content
        assert "1 000₽" in content
        assert "Статус: Активна" in content
