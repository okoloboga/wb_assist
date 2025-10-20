"""
Тесты для Event Detector системы уведомлений S3
"""

import pytest
from datetime import datetime, timezone
from typing import List, Dict, Any

from app.features.notifications.event_detector import EventDetector


class TestEventDetector:
    """Тесты для Event Detector"""
    
    def test_detect_new_orders(self):
        """Тест обнаружения новых заказов"""
        detector = EventDetector()
        
        # Предыдущие заказы
        previous_orders = [
            {"order_id": 1, "status": "active", "amount": 1000},
            {"order_id": 2, "status": "active", "amount": 1500}
        ]
        
        # Текущие заказы (добавился новый)
        current_orders = [
            {"order_id": 1, "status": "active", "amount": 1000},
            {"order_id": 2, "status": "active", "amount": 1500},
            {"order_id": 3, "status": "active", "amount": 2000}  # новый заказ
        ]
        
        events = detector.detect_new_orders(123456789, current_orders, previous_orders)
        
        assert len(events) == 1
        assert events[0]["type"] == "new_order"
        assert events[0]["order_id"] == 3
        assert events[0]["amount"] == 2000
    
    def test_detect_no_new_orders(self):
        """Тест отсутствия новых заказов"""
        detector = EventDetector()
        
        # Одинаковые списки заказов
        orders = [
            {"order_id": 1, "status": "active", "amount": 1000},
            {"order_id": 2, "status": "active", "amount": 1500}
        ]
        
        events = detector.detect_new_orders(123456789, orders, orders)
        
        assert len(events) == 0
    
    def test_detect_order_status_changes(self):
        """Тест обнаружения изменений статуса заказов"""
        detector = EventDetector()
        
        # Предыдущие заказы
        previous_orders = [
            {"order_id": 1, "status": "active", "amount": 1000},
            {"order_id": 2, "status": "active", "amount": 1500}
        ]
        
        # Текущие заказы (статус изменился)
        current_orders = [
            {"order_id": 1, "status": "buyout", "amount": 1000},  # статус изменился
            {"order_id": 2, "status": "active", "amount": 1500}
        ]
        
        events = detector.detect_status_changes(123456789, current_orders, previous_orders)
        
        assert len(events) == 1
        assert events[0]["type"] == "order_buyout"
        assert events[0]["order_id"] == 1
        assert events[0]["previous_status"] == "active"
        assert events[0]["current_status"] == "buyout"
    
    def test_detect_multiple_status_changes(self):
        """Тест обнаружения нескольких изменений статуса"""
        detector = EventDetector()
        
        # Предыдущие заказы
        previous_orders = [
            {"order_id": 1, "status": "active", "amount": 1000},
            {"order_id": 2, "status": "active", "amount": 1500},
            {"order_id": 3, "status": "buyout", "amount": 2000}
        ]
        
        # Текущие заказы (несколько изменений)
        current_orders = [
            {"order_id": 1, "status": "buyout", "amount": 1000},  # active -> buyout
            {"order_id": 2, "status": "cancelled", "amount": 1500},  # active -> cancelled
            {"order_id": 3, "status": "return", "amount": 2000}  # buyout -> return
        ]
        
        events = detector.detect_status_changes(123456789, current_orders, previous_orders)
        
        assert len(events) == 3
        
        # Проверяем типы событий
        event_types = [event["type"] for event in events]
        assert "order_buyout" in event_types
        assert "order_cancellation" in event_types
        assert "order_return" in event_types
    
    def test_detect_negative_reviews(self):
        """Тест обнаружения негативных отзывов"""
        detector = EventDetector()
        
        # Предыдущие отзывы
        previous_reviews = [
            {"id": 1, "rating": 5, "text": "Отлично!"},
            {"id": 2, "rating": 4, "text": "Хорошо"}
        ]
        
        # Текущие отзывы (добавился негативный)
        current_reviews = [
            {"id": 1, "rating": 5, "text": "Отлично!"},
            {"id": 2, "rating": 4, "text": "Хорошо"},
            {"id": 3, "rating": 2, "text": "Плохо"},  # негативный отзыв
            {"id": 4, "rating": 1, "text": "Ужасно"}  # негативный отзыв
        ]
        
        events = detector.detect_negative_reviews(123456789, current_reviews, previous_reviews)
        
        assert len(events) == 2
        assert all(event["type"] == "negative_review" for event in events)
        assert any(event["rating"] == 2 for event in events)
        assert any(event["rating"] == 1 for event in events)
    
    def test_detect_critical_stocks(self):
        """Тест обнаружения критичных остатков"""
        detector = EventDetector()
        
        # Предыдущие остатки
        previous_stocks = [
            {"nm_id": 1, "name": "Товар 1", "stocks": {"S": 10, "M": 5, "L": 3}},
            {"nm_id": 2, "name": "Товар 2", "stocks": {"S": 8, "M": 6, "L": 4}}
        ]
        
        # Текущие остатки (стали критичными)
        current_stocks = [
            {"nm_id": 1, "name": "Товар 1", "stocks": {"S": 2, "M": 1, "L": 0}},  # критично
            {"nm_id": 2, "name": "Товар 2", "stocks": {"S": 3, "M": 2, "L": 1}}   # критично
        ]
        
        events = detector.detect_critical_stocks(123456789, current_stocks, previous_stocks)
        
        assert len(events) == 2
        assert all(event["type"] == "critical_stocks" for event in events)
        assert any(event["nm_id"] == 1 for event in events)
        assert any(event["nm_id"] == 2 for event in events)
    
    def test_ignore_duplicate_events(self):
        """Тест игнорирования дубликатов событий"""
        detector = EventDetector()
        
        # Создаем одинаковые данные
        orders = [
            {"order_id": 1, "status": "active", "amount": 1000}
        ]
        
        # Детектор не должен создавать события для одинаковых данных
        new_order_events = detector.detect_new_orders(123456789, orders, orders)
        status_change_events = detector.detect_status_changes(123456789, orders, orders)
        
        assert len(new_order_events) == 0
        assert len(status_change_events) == 0
    
    def test_detect_mixed_events(self):
        """Тест обнаружения смешанных событий"""
        detector = EventDetector()
        
        # Предыдущее состояние
        previous_orders = [{"order_id": 1, "status": "active", "amount": 1000}]
        previous_reviews = [{"id": 1, "rating": 5, "text": "Отлично!"}]
        previous_stocks = [{"nm_id": 1, "name": "Товар 1", "stocks": {"S": 10, "M": 5}}]
        
        # Текущее состояние (множественные изменения)
        current_orders = [
            {"order_id": 1, "status": "buyout", "amount": 1000},  # статус изменился
            {"order_id": 2, "status": "active", "amount": 2000}    # новый заказ
        ]
        current_reviews = [
            {"id": 1, "rating": 5, "text": "Отлично!"},
            {"id": 2, "rating": 2, "text": "Плохо"}  # негативный отзыв
        ]
        current_stocks = [
            {"nm_id": 1, "name": "Товар 1", "stocks": {"S": 1, "M": 0}}  # критично
        ]
        
        # Обнаруживаем все типы событий
        new_order_events = detector.detect_new_orders(123456789, current_orders, previous_orders)
        status_change_events = detector.detect_status_changes(123456789, current_orders, previous_orders)
        negative_review_events = detector.detect_negative_reviews(123456789, current_reviews, previous_reviews)
        critical_stocks_events = detector.detect_critical_stocks(123456789, current_stocks, previous_stocks)
        
        assert len(new_order_events) == 1
        assert len(status_change_events) == 1
        assert len(negative_review_events) == 1
        assert len(critical_stocks_events) == 1
        
        # Проверяем типы событий
        assert new_order_events[0]["type"] == "new_order"
        assert status_change_events[0]["type"] == "order_buyout"
        assert negative_review_events[0]["type"] == "negative_review"
        assert critical_stocks_events[0]["type"] == "critical_stocks"
