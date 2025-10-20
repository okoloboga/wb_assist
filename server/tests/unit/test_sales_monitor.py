"""
Unit тесты для SalesMonitor
"""
import pytest
import json
from unittest.mock import Mock, patch
from datetime import datetime, timezone

from app.features.notifications.sales_monitor import SalesMonitor


class TestSalesMonitor:
    """Тесты для SalesMonitor"""
    
    @pytest.fixture
    def mock_redis(self):
        """Мок Redis клиента"""
        return Mock()
    
    @pytest.fixture
    def sales_monitor(self, mock_redis):
        """Экземпляр SalesMonitor с мок Redis"""
        return SalesMonitor(mock_redis)
    
    def test_get_previous_sales_state_empty(self, sales_monitor, mock_redis):
        """Тест получения пустого состояния продаж"""
        mock_redis.get.return_value = None
        
        result = sales_monitor.get_previous_sales_state(123)
        
        assert result == {}
        mock_redis.get.assert_called_once_with("notifications:sales_state:123")
    
    def test_get_previous_sales_state_json_string(self, sales_monitor, mock_redis):
        """Тест получения состояния продаж из JSON строки"""
        state_data = {"sales": {"sale_1": {"type": "buyout"}}}
        mock_redis.get.return_value = json.dumps(state_data)
        
        result = sales_monitor.get_previous_sales_state(123)
        
        assert result == state_data
        mock_redis.get.assert_called_once_with("notifications:sales_state:123")
    
    def test_get_previous_sales_state_dict(self, sales_monitor, mock_redis):
        """Тест получения состояния продаж из словаря"""
        state_data = {"sales": {"sale_1": {"type": "buyout"}}}
        mock_redis.get.return_value = state_data
        
        result = sales_monitor.get_previous_sales_state(123)
        
        assert result == state_data
        mock_redis.get.assert_called_once_with("notifications:sales_state:123")
    
    def test_save_current_sales_state(self, sales_monitor, mock_redis):
        """Тест сохранения текущего состояния продаж"""
        state_data = {"sales": {"sale_1": {"type": "buyout"}}}
        
        sales_monitor.save_current_sales_state(123, state_data)
        
        mock_redis.set.assert_called_once_with(
            "notifications:sales_state:123",
            json.dumps(state_data, default=str)
        )
    
    def test_compare_sales_states_new_buyout(self, sales_monitor):
        """Тест сравнения состояний - новый выкуп"""
        previous_state = {
            "sales": {
                "sale_1": {"type": "buyout", "order_id": "order_1", "product_name": "Product 1"}
            }
        }
        current_state = {
            "sales": {
                "sale_1": {"type": "buyout", "order_id": "order_1", "product_name": "Product 1"},
                "sale_2": {"type": "buyout", "order_id": "order_2", "product_name": "Product 2"}
            }
        }
        
        changes = sales_monitor.compare_sales_states(previous_state, current_state)
        
        assert len(changes) == 1
        assert changes[0]["type"] == "new_buyout"
        assert changes[0]["sale_id"] == "sale_2"
    
    def test_compare_sales_states_new_return(self, sales_monitor):
        """Тест сравнения состояний - новый возврат"""
        previous_state = {
            "sales": {
                "sale_1": {"type": "buyout", "order_id": "order_1", "product_name": "Product 1"}
            }
        }
        current_state = {
            "sales": {
                "sale_1": {"type": "buyout", "order_id": "order_1", "product_name": "Product 1"},
                "sale_2": {"type": "return", "order_id": "order_2", "product_name": "Product 2"}
            }
        }
        
        changes = sales_monitor.compare_sales_states(previous_state, current_state)
        
        assert len(changes) == 1
        assert changes[0]["type"] == "new_return"
        assert changes[0]["sale_id"] == "sale_2"
    
    def test_compare_sales_states_status_change(self, sales_monitor):
        """Тест сравнения состояний - изменение статуса"""
        previous_state = {
            "sales": {
                "sale_1": {"type": "buyout", "status": "pending", "order_id": "order_1"}
            }
        }
        current_state = {
            "sales": {
                "sale_1": {"type": "buyout", "status": "completed", "order_id": "order_1"}
            }
        }
        
        changes = sales_monitor.compare_sales_states(previous_state, current_state)
        
        assert len(changes) == 1
        assert changes[0]["type"] == "status_change"
        assert changes[0]["sale_id"] == "sale_1"
        assert changes[0]["previous_status"] == "pending"
        assert changes[0]["current_status"] == "completed"
    
    def test_compare_sales_states_cancellation_change(self, sales_monitor):
        """Тест сравнения состояний - изменение отмены"""
        previous_state = {
            "sales": {
                "sale_1": {"type": "buyout", "is_cancel": False, "order_id": "order_1"}
            }
        }
        current_state = {
            "sales": {
                "sale_1": {"type": "buyout", "is_cancel": True, "order_id": "order_1"}
            }
        }
        
        changes = sales_monitor.compare_sales_states(previous_state, current_state)
        
        assert len(changes) == 1
        assert changes[0]["type"] == "cancellation_change"
        assert changes[0]["sale_id"] == "sale_1"
        assert changes[0]["was_cancelled"] == False
        assert changes[0]["is_cancelled"] == True
    
    def test_track_sales_change(self, sales_monitor, mock_redis):
        """Тест отслеживания изменения в продаже"""
        change_data = {
            "type": "new_buyout",
            "sale_id": "sale_1",
            "order_id": "order_1"
        }
        
        sales_monitor.track_sales_change(123, change_data)
        
        mock_redis.lpush.assert_called_once()
        mock_redis.ltrim.assert_called_once_with("notifications:sales_changes:123", 0, 99)
    
    def test_get_pending_sales_changes(self, sales_monitor, mock_redis):
        """Тест получения ожидающих изменений в продажах"""
        changes_data = [
            json.dumps({"type": "new_buyout", "sale_id": "sale_1"}),
            json.dumps({"type": "new_return", "sale_id": "sale_2"})
        ]
        mock_redis.lrange.return_value = changes_data
        
        changes = sales_monitor.get_pending_sales_changes(123)
        
        assert len(changes) == 2
        assert changes[0]["type"] == "new_buyout"
        assert changes[1]["type"] == "new_return"
        mock_redis.lrange.assert_called_once_with("notifications:sales_changes:123", 0, -1)
    
    def test_mark_sales_change_processed(self, sales_monitor, mock_redis):
        """Тест отметки изменения как обработанного"""
        changes_data = [
            json.dumps({"sale_id": "sale_1", "type": "new_buyout"}),
            json.dumps({"sale_id": "sale_2", "type": "new_return"})
        ]
        mock_redis.lrange.return_value = changes_data
        
        sales_monitor.mark_sales_change_processed(123, "sale_1")
        
        mock_redis.lrem.assert_called_once()
    
    def test_clear_sales_changes(self, sales_monitor, mock_redis):
        """Тест очистки всех изменений в продажах"""
        sales_monitor.clear_sales_changes(123)
        
        mock_redis.delete.assert_called_once_with("notifications:sales_changes:123")
