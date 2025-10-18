"""
Тесты для Status Change Monitor системы уведомлений S3
"""

import pytest
import json
from datetime import datetime, timezone
from typing import List, Dict, Any
from unittest.mock import Mock, AsyncMock

from app.features.notifications.status_monitor import StatusChangeMonitor


class TestStatusChangeMonitor:
    """Тесты для Status Change Monitor"""
    
    def test_track_order_changes(self):
        """Тест отслеживания изменений заказов"""
        monitor = StatusChangeMonitor()
        
        # Текущие заказы
        orders = [
            {"order_id": 1, "status": "buyout", "amount": 1000, "product_name": "Товар 1"},
            {"order_id": 2, "status": "cancelled", "amount": 1500, "product_name": "Товар 2"},
            {"order_id": 3, "status": "active", "amount": 2000, "product_name": "Товар 3"}
        ]
        
        # Мокаем Redis для получения предыдущего состояния
        mock_redis = Mock()
        mock_redis.get.return_value = None  # Нет предыдущего состояния
        
        changes = monitor.track_order_changes(123456789, orders, mock_redis)
        
        # Должны быть обнаружены изменения для всех заказов
        assert len(changes) == 3
        assert any(change["order_id"] == 1 and change["current_status"] == "buyout" for change in changes)
        assert any(change["order_id"] == 2 and change["current_status"] == "cancelled" for change in changes)
        assert any(change["order_id"] == 3 and change["current_status"] == "active" for change in changes)
    
    def test_track_order_changes_with_previous_state(self):
        """Тест отслеживания изменений с предыдущим состоянием"""
        monitor = StatusChangeMonitor()
        
        # Текущие заказы
        current_orders = [
            {"order_id": 1, "status": "buyout", "amount": 1000},
            {"order_id": 2, "status": "cancelled", "amount": 1500}
        ]
        
        # Предыдущее состояние (заказ 1 был active, заказ 2 был active)
        previous_state = {
            "1": "active",
            "2": "active"
        }
        
        # Мокаем Redis
        mock_redis = Mock()
        mock_redis.get.return_value = previous_state  # Возвращаем словарь напрямую
        
        changes = monitor.track_order_changes(123456789, current_orders, mock_redis)
        
        # Должны быть обнаружены изменения статуса
        assert len(changes) == 2
        assert any(change["order_id"] == 1 and change["previous_status"] == "active" and change["current_status"] == "buyout" for change in changes)
        assert any(change["order_id"] == 2 and change["previous_status"] == "active" and change["current_status"] == "cancelled" for change in changes)
    
    def test_get_previous_state(self):
        """Тест получения предыдущего состояния"""
        monitor = StatusChangeMonitor()
        
        # Мокаем Redis
        mock_redis = Mock()
        previous_state = {"1": "active", "2": "buyout"}
        mock_redis.get.return_value = previous_state  # Возвращаем словарь напрямую
        
        result = monitor.get_previous_state(123456789, mock_redis)
        
        assert result == previous_state
        mock_redis.get.assert_called_once_with("notifications:order_status:123456789")
    
    def test_get_previous_state_empty(self):
        """Тест получения пустого предыдущего состояния"""
        monitor = StatusChangeMonitor()
        
        # Мокаем Redis (нет данных)
        mock_redis = Mock()
        mock_redis.get.return_value = None
        
        result = monitor.get_previous_state(123456789, mock_redis)
        
        assert result == {}
    
    def test_save_current_state(self):
        """Тест сохранения текущего состояния"""
        monitor = StatusChangeMonitor()
        
        # Текущее состояние
        current_state = {
            "1": "buyout",
            "2": "cancelled",
            "3": "active"
        }
        
        # Мокаем Redis
        mock_redis = Mock()
        
        result = monitor.save_current_state(123456789, current_state, mock_redis)
        
        assert result is True
        mock_redis.set.assert_called_once_with(
            "notifications:order_status:123456789",
            json.dumps(current_state),  # JSON строка
            ex=3600  # TTL 1 час
        )
    
    def test_compare_order_states(self):
        """Тест сравнения состояний заказов"""
        monitor = StatusChangeMonitor()
        
        # Предыдущее состояние
        previous_state = {
            "1": "active",
            "2": "active",
            "3": "buyout"
        }
        
        # Текущее состояние
        current_orders = [
            {"order_id": 1, "status": "buyout", "amount": 1000},
            {"order_id": 2, "status": "cancelled", "amount": 1500},
            {"order_id": 3, "status": "return", "amount": 2000},
            {"order_id": 4, "status": "active", "amount": 2500}  # новый заказ
        ]
        
        changes = monitor.compare_order_states(previous_state, current_orders)
        
        # Должны быть обнаружены изменения
        assert len(changes) == 4
        
        # Проверяем конкретные изменения
        change_1 = next(c for c in changes if c["order_id"] == 1)
        assert change_1["previous_status"] == "active"
        assert change_1["current_status"] == "buyout"
        
        change_2 = next(c for c in changes if c["order_id"] == 2)
        assert change_2["previous_status"] == "active"
        assert change_2["current_status"] == "cancelled"
        
        change_3 = next(c for c in changes if c["order_id"] == 3)
        assert change_3["previous_status"] == "buyout"
        assert change_3["current_status"] == "return"
        
        change_4 = next(c for c in changes if c["order_id"] == 4)
        assert change_4["previous_status"] is None  # новый заказ
        assert change_4["current_status"] == "active"
    
    def test_detect_buyout_changes(self):
        """Тест обнаружения выкупов заказов"""
        monitor = StatusChangeMonitor()
        
        changes = [
            {"order_id": 1, "previous_status": "active", "current_status": "buyout"},
            {"order_id": 2, "previous_status": "active", "current_status": "cancelled"},
            {"order_id": 3, "previous_status": "buyout", "current_status": "return"}
        ]
        
        buyout_changes = monitor.detect_buyout_changes(changes)
        
        assert len(buyout_changes) == 1
        assert buyout_changes[0]["order_id"] == 1
        assert buyout_changes[0]["current_status"] == "buyout"
    
    def test_detect_cancellation_changes(self):
        """Тест обнаружения отмен заказов"""
        monitor = StatusChangeMonitor()
        
        changes = [
            {"order_id": 1, "previous_status": "active", "current_status": "buyout"},
            {"order_id": 2, "previous_status": "active", "current_status": "cancelled"},
            {"order_id": 3, "previous_status": "buyout", "current_status": "return"}
        ]
        
        cancellation_changes = monitor.detect_cancellation_changes(changes)
        
        assert len(cancellation_changes) == 1
        assert cancellation_changes[0]["order_id"] == 2
        assert cancellation_changes[0]["current_status"] == "cancelled"
    
    def test_detect_return_changes(self):
        """Тест обнаружения возвратов заказов"""
        monitor = StatusChangeMonitor()
        
        changes = [
            {"order_id": 1, "previous_status": "active", "current_status": "buyout"},
            {"order_id": 2, "previous_status": "active", "current_status": "cancelled"},
            {"order_id": 3, "previous_status": "buyout", "current_status": "return"}
        ]
        
        return_changes = monitor.detect_return_changes(changes)
        
        assert len(return_changes) == 1
        assert return_changes[0]["order_id"] == 3
        assert return_changes[0]["current_status"] == "return"
    
    def test_no_changes_detected(self):
        """Тест отсутствия изменений"""
        monitor = StatusChangeMonitor()
        
        # Одинаковые состояния
        previous_state = {"1": "active", "2": "buyout"}
        current_orders = [
            {"order_id": 1, "status": "active", "amount": 1000},
            {"order_id": 2, "status": "buyout", "amount": 1500}
        ]
        
        changes = monitor.compare_order_states(previous_state, current_orders)
        
        # Не должно быть изменений
        assert len(changes) == 0
