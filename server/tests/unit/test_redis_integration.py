"""
Unit tests for Redis integration for queues and caching
"""
import pytest
import json
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timezone, timedelta

from app.features.notifications.redis_integration import RedisIntegration, CacheConfig


@pytest.fixture
def mock_redis():
    """Mock Redis client"""
    redis = Mock()
    redis.get = Mock()
    redis.set = Mock()
    redis.delete = Mock()
    redis.exists = Mock()
    redis.expire = Mock()
    redis.ttl = Mock()
    redis.lpush = Mock()
    redis.rpop = Mock()
    redis.llen = Mock()
    redis.lrange = Mock()
    redis.lrem = Mock()
    redis.incr = Mock()
    redis.decr = Mock()
    redis.hget = Mock()
    redis.hset = Mock()
    redis.hdel = Mock()
    redis.hgetall = Mock()
    redis.sadd = Mock()
    redis.srem = Mock()
    redis.smembers = Mock()
    redis.sismember = Mock()
    return redis


@pytest.fixture
def cache_config():
    """Cache configuration"""
    return CacheConfig(
        default_ttl=3600,
        max_cache_size=1000,
        cleanup_interval=300
    )


@pytest.fixture
def redis_integration(mock_redis, cache_config):
    """RedisIntegration instance"""
    return RedisIntegration(mock_redis, cache_config)


class TestRedisIntegration:
    """Test Redis Integration functionality"""

    def test_redis_integration_initialization(self, redis_integration, mock_redis, cache_config):
        """Test RedisIntegration initialization"""
        assert redis_integration.redis_client == mock_redis
        assert redis_integration.config == cache_config
        assert redis_integration.config.default_ttl == 3600
        assert redis_integration.config.max_cache_size == 1000

    def test_cache_config_defaults(self):
        """Test CacheConfig default values"""
        config = CacheConfig()
        assert config.default_ttl == 3600
        assert config.max_cache_size == 1000
        assert config.cleanup_interval == 300

    def test_set_cache(self, redis_integration, mock_redis):
        """Test setting cache value"""
        key = "test_key"
        value = {"data": "test_value"}
        ttl = 1800
        
        redis_integration.set_cache(key, value, ttl)
        
        mock_redis.set.assert_called_once_with(
            key,
            json.dumps(value),
            ex=ttl
        )

    def test_set_cache_default_ttl(self, redis_integration, mock_redis):
        """Test setting cache value with default TTL"""
        key = "test_key"
        value = {"data": "test_value"}
        
        redis_integration.set_cache(key, value)
        
        mock_redis.set.assert_called_once_with(
            key,
            json.dumps(value),
            ex=3600  # default_ttl
        )

    def test_get_cache(self, redis_integration, mock_redis):
        """Test getting cache value"""
        key = "test_key"
        cached_value = {"data": "test_value"}
        mock_redis.get.return_value = json.dumps(cached_value)
        
        result = redis_integration.get_cache(key)
        
        assert result == cached_value
        mock_redis.get.assert_called_once_with(key)

    def test_get_cache_not_found(self, redis_integration, mock_redis):
        """Test getting cache value when not found"""
        key = "test_key"
        mock_redis.get.return_value = None
        
        result = redis_integration.get_cache(key)
        
        assert result is None

    def test_get_cache_json_error(self, redis_integration, mock_redis):
        """Test getting cache value with JSON parsing error"""
        key = "test_key"
        mock_redis.get.return_value = "invalid_json"
        
        result = redis_integration.get_cache(key)
        
        assert result is None

    def test_delete_cache(self, redis_integration, mock_redis):
        """Test deleting cache value"""
        key = "test_key"
        mock_redis.delete.return_value = 1
        
        result = redis_integration.delete_cache(key)
        
        assert result is True
        mock_redis.delete.assert_called_once_with(key)

    def test_delete_cache_not_found(self, redis_integration, mock_redis):
        """Test deleting cache value when not found"""
        key = "test_key"
        mock_redis.delete.return_value = 0
        
        result = redis_integration.delete_cache(key)
        
        assert result is False

    def test_cache_exists(self, redis_integration, mock_redis):
        """Test checking if cache exists"""
        key = "test_key"
        mock_redis.exists.return_value = 1
        
        result = redis_integration.cache_exists(key)
        
        assert result is True
        mock_redis.exists.assert_called_once_with(key)

    def test_cache_exists_not_found(self, redis_integration, mock_redis):
        """Test checking if cache exists when not found"""
        key = "test_key"
        mock_redis.exists.return_value = 0
        
        result = redis_integration.cache_exists(key)
        
        assert result is False

    def test_get_cache_ttl(self, redis_integration, mock_redis):
        """Test getting cache TTL"""
        key = "test_key"
        mock_redis.ttl.return_value = 1800
        
        result = redis_integration.get_cache_ttl(key)
        
        assert result == 1800
        mock_redis.ttl.assert_called_once_with(key)

    def test_get_cache_ttl_not_found(self, redis_integration, mock_redis):
        """Test getting cache TTL when not found"""
        key = "test_key"
        mock_redis.ttl.return_value = -2
        
        result = redis_integration.get_cache_ttl(key)
        
        assert result is None

    def test_extend_cache_ttl(self, redis_integration, mock_redis):
        """Test extending cache TTL"""
        key = "test_key"
        new_ttl = 7200
        
        redis_integration.extend_cache_ttl(key, new_ttl)
        
        mock_redis.expire.assert_called_once_with(key, new_ttl)

    def test_set_user_settings_cache(self, redis_integration, mock_redis):
        """Test caching user settings"""
        user_id = 123
        settings = {
            "notifications_enabled": True,
            "new_orders_enabled": True,
            "negative_reviews_enabled": False
        }
        
        redis_integration.set_user_settings_cache(user_id, settings)
        
        expected_key = f"user_settings:{user_id}"
        mock_redis.set.assert_called_once_with(
            expected_key,
            json.dumps(settings),
            ex=3600
        )

    def test_get_user_settings_cache(self, redis_integration, mock_redis):
        """Test getting cached user settings"""
        user_id = 123
        settings = {
            "notifications_enabled": True,
            "new_orders_enabled": True
        }
        mock_redis.get.return_value = json.dumps(settings)
        
        result = redis_integration.get_user_settings_cache(user_id)
        
        assert result == settings
        mock_redis.get.assert_called_once_with(f"user_settings:{user_id}")

    def test_set_notification_queue_cache(self, redis_integration, mock_redis):
        """Test caching notification queue"""
        queue_name = "high_priority"
        notifications = [
            {"id": "notif_1", "content": "Notification 1"},
            {"id": "notif_2", "content": "Notification 2"}
        ]
        
        redis_integration.set_notification_queue_cache(queue_name, notifications)
        
        expected_key = f"queue_cache:{queue_name}"
        mock_redis.set.assert_called_once_with(
            expected_key,
            json.dumps(notifications),
            ex=1800  # 30 minutes
        )

    def test_get_notification_queue_cache(self, redis_integration, mock_redis):
        """Test getting cached notification queue"""
        queue_name = "high_priority"
        notifications = [
            {"id": "notif_1", "content": "Notification 1"}
        ]
        mock_redis.get.return_value = json.dumps(notifications)
        
        result = redis_integration.get_notification_queue_cache(queue_name)
        
        assert result == notifications
        mock_redis.get.assert_called_once_with(f"queue_cache:{queue_name}")

    def test_increment_counter(self, redis_integration, mock_redis):
        """Test incrementing counter"""
        counter_name = "processed_notifications"
        mock_redis.incr.return_value = 5
        
        result = redis_integration.increment_counter(counter_name)
        
        assert result == 5
        mock_redis.incr.assert_called_once_with(counter_name)

    def test_decrement_counter(self, redis_integration, mock_redis):
        """Test decrementing counter"""
        counter_name = "pending_notifications"
        mock_redis.decr.return_value = 3
        
        result = redis_integration.decrement_counter(counter_name)
        
        assert result == 3
        mock_redis.decr.assert_called_once_with(counter_name)

    def test_set_hash_field(self, redis_integration, mock_redis):
        """Test setting hash field"""
        hash_name = "user_stats"
        field = "total_notifications"
        value = "100"
        
        redis_integration.set_hash_field(hash_name, field, value)
        
        mock_redis.hset.assert_called_once_with(hash_name, field, value)

    def test_get_hash_field(self, redis_integration, mock_redis):
        """Test getting hash field"""
        hash_name = "user_stats"
        field = "total_notifications"
        mock_redis.hget.return_value = "100"
        
        result = redis_integration.get_hash_field(hash_name, field)
        
        assert result == "100"
        mock_redis.hget.assert_called_once_with(hash_name, field)

    def test_get_all_hash_fields(self, redis_integration, mock_redis):
        """Test getting all hash fields"""
        hash_name = "user_stats"
        fields = {"total_notifications": "100", "success_rate": "95.5"}
        mock_redis.hgetall.return_value = fields
        
        result = redis_integration.get_all_hash_fields(hash_name)
        
        assert result == fields
        mock_redis.hgetall.assert_called_once_with(hash_name)

    def test_add_to_set(self, redis_integration, mock_redis):
        """Test adding to set"""
        set_name = "processed_notifications"
        value = "notif_12345"
        mock_redis.sadd.return_value = 1
        
        result = redis_integration.add_to_set(set_name, value)
        
        assert result is True
        mock_redis.sadd.assert_called_once_with(set_name, value)

    def test_remove_from_set(self, redis_integration, mock_redis):
        """Test removing from set"""
        set_name = "processed_notifications"
        value = "notif_12345"
        mock_redis.srem.return_value = 1
        
        result = redis_integration.remove_from_set(set_name, value)
        
        assert result is True
        mock_redis.srem.assert_called_once_with(set_name, value)

    def test_is_in_set(self, redis_integration, mock_redis):
        """Test checking if value is in set"""
        set_name = "processed_notifications"
        value = "notif_12345"
        mock_redis.sismember.return_value = True
        
        result = redis_integration.is_in_set(set_name, value)
        
        assert result is True
        mock_redis.sismember.assert_called_once_with(set_name, value)

    def test_get_set_members(self, redis_integration, mock_redis):
        """Test getting set members"""
        set_name = "processed_notifications"
        members = {"notif_1", "notif_2", "notif_3"}
        mock_redis.smembers.return_value = members
        
        result = redis_integration.get_set_members(set_name)
        
        assert result == members
        mock_redis.smembers.assert_called_once_with(set_name)

    def test_clear_cache_pattern(self, redis_integration, mock_redis):
        """Test clearing cache by pattern"""
        pattern = "user_settings:*"
        mock_redis.keys.return_value = ["user_settings:1", "user_settings:2"]
        mock_redis.delete.return_value = 2
        
        result = redis_integration.clear_cache_pattern(pattern)
        
        assert result == 2
        mock_redis.keys.assert_called_once_with(pattern)
        mock_redis.delete.assert_called_once_with("user_settings:1", "user_settings:2")

    def test_get_cache_stats(self, redis_integration, mock_redis):
        """Test getting cache statistics"""
        mock_redis.info.return_value = {
            "used_memory": 1024000,
            "keyspace_hits": 1000,
            "keyspace_misses": 100,
            "expired_keys": 50
        }
        
        stats = redis_integration.get_cache_stats()
        
        expected = {
            "memory_usage": 1024000,
            "hit_rate": 1000 / (1000 + 100),
            "miss_rate": 100 / (1000 + 100),
            "expired_keys": 50
        }
        assert stats == expected

    def test_cleanup_expired_cache(self, redis_integration, mock_redis):
        """Test cleaning up expired cache"""
        mock_redis.keys.return_value = ["expired_key_1", "expired_key_2"]
        mock_redis.ttl.side_effect = [-2, -2]  # Expired keys (TTL = -2 means key doesn't exist)
        mock_redis.delete.return_value = 2
        
        result = redis_integration.cleanup_expired_cache()
        
        assert result == 2
        mock_redis.keys.assert_called_once_with("*")
        mock_redis.delete.assert_called_once_with("expired_key_1", "expired_key_2")

    def test_cleanup_expired_cache_no_expired(self, redis_integration, mock_redis):
        """Test cleanup when no expired keys"""
        mock_redis.keys.return_value = ["key_1", "key_2"]
        mock_redis.ttl.side_effect = [3600, 1800]  # Valid keys
        
        result = redis_integration.cleanup_expired_cache()
        
        assert result == 0
        mock_redis.delete.assert_not_called()
