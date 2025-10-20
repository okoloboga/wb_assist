"""
Unit тесты для EventDetector - методы для продаж
"""
import pytest
from datetime import datetime, timezone

from app.features.notifications.event_detector import EventDetector


class TestEventDetectorSales:
    """Тесты для EventDetector - методы продаж"""
    
    @pytest.fixture
    def event_detector(self):
        """Экземпляр EventDetector"""
        return EventDetector()
    
    def test_detect_sales_changes_new_buyout(self, event_detector):
        """Тест обнаружения нового выкупа"""
        current_sales = [
            {
                "sale_id": "sale_1",
                "type": "buyout",
                "order_id": "order_1",
                "product_name": "Product 1",
                "amount": 1000.0,
                "sale_date": "2025-01-28T12:00:00",
                "nm_id": 12345,
                "brand": "Brand 1",
                "size": "M"
            }
        ]
        previous_sales = []
        
        events = event_detector.detect_sales_changes(123, current_sales, previous_sales)
        
        assert len(events) == 1
        assert events[0]["type"] == "new_buyout"
        assert events[0]["user_id"] == 123
        assert events[0]["sale_id"] == "sale_1"
        assert events[0]["order_id"] == "order_1"
        assert events[0]["product_name"] == "Product 1"
        assert events[0]["amount"] == 1000.0
    
    def test_detect_sales_changes_new_return(self, event_detector):
        """Тест обнаружения нового возврата"""
        current_sales = [
            {
                "sale_id": "sale_1",
                "type": "return",
                "order_id": "order_1",
                "product_name": "Product 1",
                "amount": 1000.0,
                "sale_date": "2025-01-28T12:00:00",
                "nm_id": 12345,
                "brand": "Brand 1",
                "size": "M"
            }
        ]
        previous_sales = []
        
        events = event_detector.detect_sales_changes(123, current_sales, previous_sales)
        
        assert len(events) == 1
        assert events[0]["type"] == "new_return"
        assert events[0]["user_id"] == 123
        assert events[0]["sale_id"] == "sale_1"
        assert events[0]["order_id"] == "order_1"
    
    def test_detect_sales_changes_status_change(self, event_detector):
        """Тест обнаружения изменения статуса продажи"""
        current_sales = [
            {
                "sale_id": "sale_1",
                "type": "buyout",
                "order_id": "order_1",
                "product_name": "Product 1",
                "amount": 1000.0,
                "status": "completed",
                "sale_date": "2025-01-28T12:00:00"
            }
        ]
        previous_sales = [
            {
                "sale_id": "sale_1",
                "type": "buyout",
                "order_id": "order_1",
                "product_name": "Product 1",
                "amount": 1000.0,
                "status": "pending",
                "sale_date": "2025-01-28T12:00:00"
            }
        ]
        
        events = event_detector.detect_sales_changes(123, current_sales, previous_sales)
        
        assert len(events) == 1
        assert events[0]["type"] == "sale_status_change"
        assert events[0]["sale_id"] == "sale_1"
        assert events[0]["previous_status"] == "pending"
        assert events[0]["current_status"] == "completed"
    
    def test_detect_sales_changes_cancellation_change(self, event_detector):
        """Тест обнаружения изменения отмены продажи"""
        current_sales = [
            {
                "sale_id": "sale_1",
                "type": "buyout",
                "order_id": "order_1",
                "product_name": "Product 1",
                "amount": 1000.0,
                "is_cancel": True,
                "sale_date": "2025-01-28T12:00:00"
            }
        ]
        previous_sales = [
            {
                "sale_id": "sale_1",
                "type": "buyout",
                "order_id": "order_1",
                "product_name": "Product 1",
                "amount": 1000.0,
                "is_cancel": False,
                "sale_date": "2025-01-28T12:00:00"
            }
        ]
        
        events = event_detector.detect_sales_changes(123, current_sales, previous_sales)
        
        assert len(events) == 1
        assert events[0]["type"] == "sale_cancellation_change"
        assert events[0]["sale_id"] == "sale_1"
        assert events[0]["was_cancelled"] == False
        assert events[0]["is_cancelled"] == True
    
    def test_detect_sales_changes_no_changes(self, event_detector):
        """Тест обнаружения без изменений"""
        current_sales = [
            {
                "sale_id": "sale_1",
                "type": "buyout",
                "order_id": "order_1",
                "product_name": "Product 1",
                "amount": 1000.0,
                "status": "completed",
                "is_cancel": False
            }
        ]
        previous_sales = [
            {
                "sale_id": "sale_1",
                "type": "buyout",
                "order_id": "order_1",
                "product_name": "Product 1",
                "amount": 1000.0,
                "status": "completed",
                "is_cancel": False
            }
        ]
        
        events = event_detector.detect_sales_changes(123, current_sales, previous_sales)
        
        assert len(events) == 0
    
    def test_detect_sales_changes_multiple_changes(self, event_detector):
        """Тест обнаружения множественных изменений"""
        current_sales = [
            {
                "sale_id": "sale_1",
                "type": "buyout",
                "order_id": "order_1",
                "product_name": "Product 1",
                "amount": 1000.0,
                "status": "completed",
                "is_cancel": False
            },
            {
                "sale_id": "sale_2",
                "type": "return",
                "order_id": "order_2",
                "product_name": "Product 2",
                "amount": 500.0,
                "status": "completed",
                "is_cancel": False
            }
        ]
        previous_sales = [
            {
                "sale_id": "sale_1",
                "type": "buyout",
                "order_id": "order_1",
                "product_name": "Product 1",
                "amount": 1000.0,
                "status": "pending",
                "is_cancel": False
            }
        ]
        
        events = event_detector.detect_sales_changes(123, current_sales, previous_sales)
        
        assert len(events) == 2
        
        # Проверяем новый возврат
        new_return_event = next(e for e in events if e["type"] == "new_return")
        assert new_return_event["sale_id"] == "sale_2"
        
        # Проверяем изменение статуса
        status_change_event = next(e for e in events if e["type"] == "sale_status_change")
        assert status_change_event["sale_id"] == "sale_1"
        assert status_change_event["previous_status"] == "pending"
        assert status_change_event["current_status"] == "completed"
    
    def test_detect_sales_changes_empty_previous(self, event_detector):
        """Тест обнаружения изменений при пустом предыдущем состоянии"""
        current_sales = [
            {
                "sale_id": "sale_1",
                "type": "buyout",
                "order_id": "order_1",
                "product_name": "Product 1",
                "amount": 1000.0
            }
        ]
        previous_sales = []
        
        events = event_detector.detect_sales_changes(123, current_sales, previous_sales)
        
        assert len(events) == 1
        assert events[0]["type"] == "new_buyout"
        assert events[0]["sale_id"] == "sale_1"
    
    def test_detect_sales_changes_empty_current(self, event_detector):
        """Тест обнаружения изменений при пустом текущем состоянии"""
        current_sales = []
        previous_sales = [
            {
                "sale_id": "sale_1",
                "type": "buyout",
                "order_id": "order_1",
                "product_name": "Product 1",
                "amount": 1000.0
            }
        ]
        
        events = event_detector.detect_sales_changes(123, current_sales, previous_sales)
        
        assert len(events) == 0
