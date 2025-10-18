"""
Тесты для Notification Generator системы уведомлений S3
"""

import pytest
from datetime import datetime, timezone
from typing import List, Dict, Any
from unittest.mock import Mock

from app.features.notifications.notification_generator import NotificationGenerator


class TestNotificationGenerator:
    """Тесты для Notification Generator"""
    
    def test_generate_new_order_notification(self):
        """Тест генерации уведомления о новом заказе"""
        generator = NotificationGenerator()
        
        event_data = {
            "type": "new_order",
            "user_id": 123456789,
            "order_id": 98765,
            "amount": 2500,
            "product_name": "Тестовый товар",
            "brand": "Test Brand",
            "detected_at": datetime.now(timezone.utc)
        }
        
        user_settings = {
            "notifications_enabled": True,
            "new_orders_enabled": True,
            "grouping_enabled": False
        }
        
        notification = generator.generate_notification(event_data, user_settings)
        
        assert notification is not None
        assert notification["type"] == "new_order"
        assert notification["user_id"] == 123456789
        assert notification["order_id"] == 98765
        assert notification["amount"] == 2500
        assert "Новый заказ" in notification["title"]
        assert "Тестовый товар" in notification["content"]
        assert "Test Brand" in notification["content"]
        assert notification["priority"] == "HIGH"
        assert notification["grouping_enabled"] is False
    
    def test_generate_order_buyout_notification(self):
        """Тест генерации уведомления о выкупе заказа"""
        generator = NotificationGenerator()
        
        event_data = {
            "type": "order_buyout",
            "user_id": 123456789,
            "order_id": 54321,
            "previous_status": "active",
            "current_status": "buyout",
            "amount": 1800,
            "product_name": "Товар выкуплен",
            "brand": "Brand Name",
            "detected_at": datetime.now(timezone.utc)
        }
        
        user_settings = {
            "notifications_enabled": True,
            "order_buyouts_enabled": True,
            "grouping_enabled": True
        }
        
        notification = generator.generate_notification(event_data, user_settings)
        
        assert notification is not None
        assert notification["type"] == "order_buyout"
        assert notification["user_id"] == 123456789
        assert notification["order_id"] == 54321
        assert "выкуплен" in notification["title"]
        assert "Товар выкуплен" in notification["content"]
        assert "Brand Name" in notification["content"]
        assert notification["priority"] == "HIGH"
        assert notification["grouping_enabled"] is True
    
    def test_generate_order_cancellation_notification(self):
        """Тест генерации уведомления об отмене заказа"""
        generator = NotificationGenerator()
        
        event_data = {
            "type": "order_cancellation",
            "user_id": 123456789,
            "order_id": 11111,
            "previous_status": "active",
            "current_status": "cancelled",
            "amount": 1200,
            "product_name": "Отмененный товар",
            "brand": "Cancel Brand",
            "detected_at": datetime.now(timezone.utc)
        }
        
        user_settings = {
            "notifications_enabled": True,
            "order_cancellations_enabled": True,
            "grouping_enabled": False
        }
        
        notification = generator.generate_notification(event_data, user_settings)
        
        assert notification is not None
        assert notification["type"] == "order_cancellation"
        assert notification["user_id"] == 123456789
        assert notification["order_id"] == 11111
        assert "отменен" in notification["title"]
        assert "Отмененный товар" in notification["content"]
        assert "Cancel Brand" in notification["content"]
        assert notification["priority"] == "HIGH"
    
    def test_generate_order_return_notification(self):
        """Тест генерации уведомления о возврате заказа"""
        generator = NotificationGenerator()
        
        event_data = {
            "type": "order_return",
            "user_id": 123456789,
            "order_id": 22222,
            "previous_status": "buyout",
            "current_status": "return",
            "amount": 3000,
            "product_name": "Возвращенный товар",
            "brand": "Return Brand",
            "detected_at": datetime.now(timezone.utc)
        }
        
        user_settings = {
            "notifications_enabled": True,
            "order_returns_enabled": True,
            "grouping_enabled": True
        }
        
        notification = generator.generate_notification(event_data, user_settings)
        
        assert notification is not None
        assert notification["type"] == "order_return"
        assert notification["user_id"] == 123456789
        assert notification["order_id"] == 22222
        assert "возвращен" in notification["title"]
        assert "Возвращенный товар" in notification["content"]
        assert "Return Brand" in notification["content"]
        assert notification["priority"] == "HIGH"
    
    def test_generate_negative_review_notification(self):
        """Тест генерации уведомления о негативном отзыве"""
        generator = NotificationGenerator()
        
        event_data = {
            "type": "negative_review",
            "user_id": 123456789,
            "review_id": 33333,
            "rating": 2,
            "text": "Плохой товар",
            "product_name": "Товар с плохим отзывом",
            "order_id": 44444,
            "detected_at": datetime.now(timezone.utc)
        }
        
        user_settings = {
            "notifications_enabled": True,
            "negative_reviews_enabled": True,
            "grouping_enabled": False
        }
        
        notification = generator.generate_notification(event_data, user_settings)
        
        assert notification is not None
        assert notification["type"] == "negative_review"
        assert notification["user_id"] == 123456789
        assert notification["review_id"] == 33333
        assert "Негативный отзыв" in notification["title"]
        assert "Товар с плохим отзывом" in notification["content"]
        assert "Плохой товар" in notification["content"]
        assert notification["rating"] == 2
        assert notification["priority"] == "CRITICAL"
    
    def test_generate_critical_stocks_notification(self):
        """Тест генерации уведомления о критичных остатках"""
        generator = NotificationGenerator()
        
        event_data = {
            "type": "critical_stocks",
            "user_id": 123456789,
            "nm_id": 55555,
            "name": "Товар с критичными остатками",
            "brand": "Stock Brand",
            "stocks": {"S": 1, "M": 0, "L": 0},
            "critical_sizes": ["M", "L"],
            "zero_sizes": ["L"],
            "detected_at": datetime.now(timezone.utc)
        }
        
        user_settings = {
            "notifications_enabled": True,
            "critical_stocks_enabled": True,
            "grouping_enabled": True
        }
        
        notification = generator.generate_notification(event_data, user_settings)
        
        assert notification is not None
        assert notification["type"] == "critical_stocks"
        assert notification["user_id"] == 123456789
        assert notification["nm_id"] == 55555
        assert "Критичные остатки" in notification["title"]
        assert "Товар с критичными остатками" in notification["content"]
        assert "Stock Brand" in notification["content"]
        assert "M, L" in notification["content"]  # критичные размеры
        assert notification["priority"] == "HIGH"
    
    def test_notification_filtering_by_settings(self):
        """Тест фильтрации уведомлений на основе настроек пользователя"""
        generator = NotificationGenerator()
        
        # Событие о новом заказе
        event_data = {
            "type": "new_order",
            "user_id": 123456789,
            "order_id": 99999,
            "amount": 1000,
            "product_name": "Тестовый товар",
            "detected_at": datetime.now(timezone.utc)
        }
        
        # Настройки с отключенными уведомлениями о новых заказах
        user_settings = {
            "notifications_enabled": True,
            "new_orders_enabled": False,  # отключено
            "grouping_enabled": False
        }
        
        # Уведомление не должно быть сгенерировано
        notification = generator.generate_notification(event_data, user_settings)
        
        assert notification is None
    
    def test_notification_filtering_disabled_notifications(self):
        """Тест фильтрации при отключенных уведомлениях"""
        generator = NotificationGenerator()
        
        event_data = {
            "type": "order_buyout",
            "user_id": 123456789,
            "order_id": 88888,
            "amount": 2000,
            "product_name": "Товар",
            "detected_at": datetime.now(timezone.utc)
        }
        
        # Общие уведомления отключены
        user_settings = {
            "notifications_enabled": False,  # отключено
            "order_buyouts_enabled": True,
            "grouping_enabled": False
        }
        
        # Уведомление не должно быть сгенерировано
        notification = generator.generate_notification(event_data, user_settings)
        
        assert notification is None
    
    def test_notification_content_formatting(self):
        """Тест форматирования контента уведомлений"""
        generator = NotificationGenerator()
        
        event_data = {
            "type": "new_order",
            "user_id": 123456789,
            "order_id": 77777,
            "amount": 3500,
            "product_name": "Длинное название товара для тестирования",
            "brand": "Очень длинное название бренда",
            "detected_at": datetime.now(timezone.utc)
        }
        
        user_settings = {
            "notifications_enabled": True,
            "new_orders_enabled": True,
            "grouping_enabled": False
        }
        
        notification = generator.generate_notification(event_data, user_settings)
        
        # Проверяем форматирование контента
        assert notification is not None
        content = notification["content"]
        
        # Должны быть все ключевые элементы
        assert "77777" in content  # ID заказа
        assert "3,500" in content  # Сумма (с форматированием)
        assert "Длинное название товара для тестирования" in content
        assert "Очень длинное название бренда" in content
        
        # Проверяем структуру контента
        assert "💰" in content  # Эмодзи для суммы
        assert "📦" in content  # Эмодзи для товара
        assert "🏷️" in content  # Эмодзи для бренда
    
    def test_notification_priority_assignment(self):
        """Тест назначения приоритетов уведомлениям"""
        generator = NotificationGenerator()
        
        # Тестируем разные типы событий и их приоритеты
        test_cases = [
            ("new_order", "HIGH"),
            ("order_buyout", "HIGH"),
            ("order_cancellation", "HIGH"),
            ("order_return", "HIGH"),
            ("negative_review", "CRITICAL"),
            ("critical_stocks", "HIGH")
        ]
        
        for event_type, expected_priority in test_cases:
            event_data = {
                "type": event_type,
                "user_id": 123456789,
                "detected_at": datetime.now(timezone.utc)
            }
            
            user_settings = {
                "notifications_enabled": True,
                f"{event_type.replace('_', '_')}s_enabled": True,
                "grouping_enabled": False
            }
            
            notification = generator.generate_notification(event_data, user_settings)
            
            if notification:  # Если уведомление не отфильтровано
                assert notification["priority"] == expected_priority, f"Wrong priority for {event_type}"
    
    def test_grouping_settings_propagation(self):
        """Тест передачи настроек группировки"""
        generator = NotificationGenerator()
        
        event_data = {
            "type": "new_order",
            "user_id": 123456789,
            "order_id": 66666,
            "amount": 1500,
            "product_name": "Товар",
            "detected_at": datetime.now(timezone.utc)
        }
        
        # Тестируем с включенной группировкой
        user_settings_grouped = {
            "notifications_enabled": True,
            "new_orders_enabled": True,
            "grouping_enabled": True,
            "max_group_size": 5,
            "group_timeout": 300
        }
        
        notification_grouped = generator.generate_notification(event_data, user_settings_grouped)
        
        assert notification_grouped is not None
        assert notification_grouped["grouping_enabled"] is True
        assert notification_grouped["max_group_size"] == 5
        assert notification_grouped["group_timeout"] == 300
        
        # Тестируем с отключенной группировкой
        user_settings_ungrouped = {
            "notifications_enabled": True,
            "new_orders_enabled": True,
            "grouping_enabled": False
        }
        
        notification_ungrouped = generator.generate_notification(event_data, user_settings_ungrouped)
        
        assert notification_ungrouped is not None
        assert notification_ungrouped["grouping_enabled"] is False
