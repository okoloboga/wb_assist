"""
Unit tests for Enhanced Queue Manager
"""
import pytest
import json
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timezone

from app.features.notifications.queue_manager import QueueManager


@pytest.fixture
def mock_redis():
    """Mock Redis client"""
    redis = Mock()
    redis.lpush = Mock()
    redis.rpop = Mock()
    redis.llen = Mock()
    redis.lrange = Mock()
    redis.delete = Mock()
    redis.expire = Mock()
    redis.get = Mock()
    redis.set = Mock()
    redis.incr = Mock()
    redis.decr = Mock()
    return redis


@pytest.fixture
def queue_manager(mock_redis):
    """Create QueueManager instance"""
    return QueueManager(mock_redis)


@pytest.fixture
def sample_notification():
    """Sample notification data"""
    return {
        "id": "notif_12345",
        "user_id": 1,
        "type": "new_order",
        "priority": "HIGH",
        "content": "New order notification",
        "webhook_url": "http://test.com/webhook",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "retry_count": 0,
        "max_retries": 3
    }


class TestQueueManager:
    """Test Queue Manager functionality"""

    def test_queue_manager_initialization(self, queue_manager, mock_redis):
        """Test QueueManager initialization"""
        assert queue_manager.redis_client == mock_redis
        assert queue_manager.queue_key == "notification_queue"
        assert queue_manager.priority_queues == {
            "CRITICAL": "notification_queue:critical",
            "HIGH": "notification_queue:high", 
            "MEDIUM": "notification_queue:medium",
            "LOW": "notification_queue:low"
        }

    def test_add_notification_to_queue(self, queue_manager, mock_redis, sample_notification):
        """Test adding notification to queue"""
        queue_manager.add_notification_to_queue(sample_notification)
        
        # Should add to high priority queue
        mock_redis.lpush.assert_called_once_with(
            "notification_queue:high",
            json.dumps(sample_notification)
        )

    def test_add_notification_to_queue_critical_priority(self, queue_manager, mock_redis):
        """Test adding critical priority notification"""
        notification = {
            "id": "notif_critical",
            "priority": "CRITICAL",
            "content": "Critical notification"
        }
        
        queue_manager.add_notification_to_queue(notification)
        
        mock_redis.lpush.assert_called_once_with(
            "notification_queue:critical",
            json.dumps(notification)
        )

    def test_add_notification_to_queue_low_priority(self, queue_manager, mock_redis):
        """Test adding low priority notification"""
        notification = {
            "id": "notif_low",
            "priority": "LOW",
            "content": "Low priority notification"
        }
        
        queue_manager.add_notification_to_queue(notification)
        
        mock_redis.lpush.assert_called_once_with(
            "notification_queue:low",
            json.dumps(notification)
        )

    def test_add_notification_to_queue_default_priority(self, queue_manager, mock_redis):
        """Test adding notification with default priority"""
        notification = {
            "id": "notif_default",
            "content": "Default priority notification"
        }
        
        queue_manager.add_notification_to_queue(notification)
        
        # Should default to MEDIUM priority
        mock_redis.lpush.assert_called_once_with(
            "notification_queue:medium",
            json.dumps(notification)
        )

    def test_get_next_notification(self, queue_manager, mock_redis, sample_notification):
        """Test getting next notification from queue"""
        mock_redis.rpop.return_value = json.dumps(sample_notification)
        
        result = queue_manager.get_next_notification()
        
        assert result == sample_notification
        mock_redis.rpop.assert_called_once_with("notification_queue:critical")

    def test_get_next_notification_empty_queue(self, queue_manager, mock_redis):
        """Test getting notification from empty queue"""
        mock_redis.rpop.return_value = None
        
        result = queue_manager.get_next_notification()
        
        assert result is None

    def test_get_next_notification_json_error(self, queue_manager, mock_redis):
        """Test handling JSON parsing error"""
        mock_redis.rpop.return_value = "invalid_json"
        
        result = queue_manager.get_next_notification()
        
        assert result is None

    def test_get_queue_status(self, queue_manager, mock_redis):
        """Test getting queue status"""
        mock_redis.llen.side_effect = [5, 10, 3, 1]  # critical, high, medium, low
        
        status = queue_manager.get_queue_status()
        
        expected = {
            "critical": 5,
            "high": 10,
            "medium": 3,
            "low": 1,
            "total": 19
        }
        assert status == expected

    def test_get_queue_status_empty(self, queue_manager, mock_redis):
        """Test getting status of empty queues"""
        mock_redis.llen.return_value = 0
        
        status = queue_manager.get_queue_status()
        
        expected = {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
            "total": 0
        }
        assert status == expected

    def test_clear_queue(self, queue_manager, mock_redis):
        """Test clearing all queues"""
        queue_manager.clear_queue()
        
        # Should delete all priority queues
        expected_calls = [
            (("notification_queue:critical",),),
            (("notification_queue:high",),),
            (("notification_queue:medium",),),
            (("notification_queue:low",),)
        ]
        assert mock_redis.delete.call_args_list == expected_calls

    def test_get_notifications_by_priority(self, queue_manager, mock_redis, sample_notification):
        """Test getting notifications by priority"""
        mock_redis.lrange.return_value = [json.dumps(sample_notification)]
        
        notifications = queue_manager.get_notifications_by_priority("HIGH", limit=10)
        
        assert len(notifications) == 1
        assert notifications[0] == sample_notification
        mock_redis.lrange.assert_called_once_with("notification_queue:high", 0, 9)

    def test_get_notifications_by_priority_empty(self, queue_manager, mock_redis):
        """Test getting notifications from empty priority queue"""
        mock_redis.lrange.return_value = []
        
        notifications = queue_manager.get_notifications_by_priority("HIGH")
        
        assert notifications == []

    def test_get_notifications_by_priority_json_error(self, queue_manager, mock_redis):
        """Test handling JSON parsing errors in priority queue"""
        mock_redis.lrange.return_value = ["invalid_json", '{"valid": "json"}']
        
        notifications = queue_manager.get_notifications_by_priority("HIGH")
        
        # Should skip invalid JSON and return valid ones
        assert len(notifications) == 1
        assert notifications[0] == {"valid": "json"}

    def test_requeue_notification(self, queue_manager, mock_redis, sample_notification):
        """Test requeuing a notification"""
        sample_notification["retry_count"] = 1
        
        queue_manager.requeue_notification(sample_notification)
        
        mock_redis.lpush.assert_called_once_with(
            "notification_queue:high",
            json.dumps(sample_notification)
        )

    def test_requeue_notification_max_retries(self, queue_manager, mock_redis):
        """Test requeuing notification that exceeded max retries"""
        notification = {
            "id": "notif_max_retries",
            "retry_count": 3,
            "max_retries": 3,
            "priority": "HIGH"
        }
        
        queue_manager.requeue_notification(notification)
        
        # Should not requeue if max retries exceeded
        mock_redis.lpush.assert_not_called()

    def test_requeue_notification_critical_priority(self, queue_manager, mock_redis):
        """Test requeuing critical priority notification"""
        notification = {
            "id": "notif_critical",
            "priority": "CRITICAL",
            "retry_count": 1
        }
        
        queue_manager.requeue_notification(notification)
        
        mock_redis.lpush.assert_called_once_with(
            "notification_queue:critical",
            json.dumps(notification)
        )

    def test_get_queue_metrics(self, queue_manager, mock_redis):
        """Test getting queue metrics"""
        mock_redis.llen.side_effect = [2, 5, 3, 1]  # critical, high, medium, low
        mock_redis.get.side_effect = ["10", "25", "15", "5"]  # processed counts
        
        metrics = queue_manager.get_queue_metrics()
        
        expected = {
            "queue_sizes": {
                "critical": 2,
                "high": 5,
                "medium": 3,
                "low": 1,
                "total": 11
            },
            "processed_counts": {
                "critical": 10,
                "high": 25,
                "medium": 15,
                "low": 5,
                "total": 55
            },
            "timestamp": metrics["timestamp"]
        }
        assert metrics == expected

    def test_increment_processed_count(self, queue_manager, mock_redis):
        """Test incrementing processed count"""
        queue_manager.increment_processed_count("HIGH")
        
        mock_redis.incr.assert_called_once_with("processed_count:high")

    def test_set_queue_expiry(self, queue_manager, mock_redis):
        """Test setting queue expiry"""
        queue_manager.set_queue_expiry("HIGH", 3600)
        
        mock_redis.expire.assert_called_once_with("notification_queue:high", 3600)

    def test_get_notification_by_id(self, queue_manager, mock_redis, sample_notification):
        """Test getting notification by ID"""
        mock_redis.lrange.return_value = [json.dumps(sample_notification)]
        
        result = queue_manager.get_notification_by_id("notif_12345")
        
        assert result == sample_notification

    def test_get_notification_by_id_not_found(self, queue_manager, mock_redis):
        """Test getting notification by ID when not found"""
        mock_redis.lrange.return_value = []
        
        result = queue_manager.get_notification_by_id("notif_nonexistent")
        
        assert result is None

    def test_remove_notification_by_id(self, queue_manager, mock_redis):
        """Test removing notification by ID"""
        notification = {"id": "notif_remove", "priority": "HIGH"}
        mock_redis.lrange.return_value = [json.dumps(notification)]
        mock_redis.lrem.return_value = 1
        
        result = queue_manager.remove_notification_by_id("notif_remove")
        
        assert result is True
        mock_redis.lrem.assert_called_once()

    def test_remove_notification_by_id_not_found(self, queue_manager, mock_redis):
        """Test removing notification by ID when not found"""
        mock_redis.lrange.return_value = []
        
        result = queue_manager.remove_notification_by_id("notif_nonexistent")
        
        assert result is False
