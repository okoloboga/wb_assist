"""
Redis integration for queues and caching
"""
import json
import logging
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class CacheConfig:
    """
    Configuration for Redis caching
    """
    default_ttl: int = 3600  # 1 hour
    max_cache_size: int = 1000
    cleanup_interval: int = 300  # 5 minutes


class RedisIntegration:
    """
    Redis integration for caching and queue management
    """
    
    def __init__(self, redis_client, config: CacheConfig = None):
        """
        Initialize Redis integration
        
        Args:
            redis_client: Redis client instance
            config: Cache configuration
        """
        self.redis_client = redis_client
        self.config = config or CacheConfig()
    
    def set_cache(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Set cache value
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (uses default if None)
        """
        try:
            ttl = ttl or self.config.default_ttl
            serialized_value = json.dumps(value)
            
            self.redis_client.set(key, serialized_value, ex=ttl)
            logger.debug(f"Cached value for key: {key}")
            
        except Exception as e:
            logger.error(f"Failed to set cache for key {key}: {e}")
            raise
    
    def get_cache(self, key: str) -> Optional[Any]:
        """
        Get cache value
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found
        """
        try:
            cached_value = self.redis_client.get(key)
            if cached_value is None:
                return None
            
            return json.loads(cached_value)
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse cached value for key {key}: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to get cache for key {key}: {e}")
            return None
    
    def delete_cache(self, key: str) -> bool:
        """
        Delete cache value
        
        Args:
            key: Cache key
            
        Returns:
            True if deleted, False if not found
        """
        try:
            result = self.redis_client.delete(key)
            return result > 0
            
        except Exception as e:
            logger.error(f"Failed to delete cache for key {key}: {e}")
            return False
    
    def cache_exists(self, key: str) -> bool:
        """
        Check if cache key exists
        
        Args:
            key: Cache key
            
        Returns:
            True if exists, False otherwise
        """
        try:
            result = self.redis_client.exists(key)
            return result > 0
            
        except Exception as e:
            logger.error(f"Failed to check cache existence for key {key}: {e}")
            return False
    
    def get_cache_ttl(self, key: str) -> Optional[int]:
        """
        Get cache TTL
        
        Args:
            key: Cache key
            
        Returns:
            TTL in seconds or None if key doesn't exist
        """
        try:
            ttl = self.redis_client.ttl(key)
            return ttl if ttl > 0 else None
            
        except Exception as e:
            logger.error(f"Failed to get cache TTL for key {key}: {e}")
            return None
    
    def extend_cache_ttl(self, key: str, ttl: int) -> None:
        """
        Extend cache TTL
        
        Args:
            key: Cache key
            ttl: New TTL in seconds
        """
        try:
            self.redis_client.expire(key, ttl)
            logger.debug(f"Extended TTL for key {key} to {ttl} seconds")
            
        except Exception as e:
            logger.error(f"Failed to extend cache TTL for key {key}: {e}")
            raise
    
    def set_user_settings_cache(self, user_id: int, settings: Dict[str, Any]) -> None:
        """
        Cache user notification settings
        
        Args:
            user_id: User ID
            settings: User settings dictionary
        """
        key = f"user_settings:{user_id}"
        self.set_cache(key, settings, ttl=3600)  # 1 hour cache
    
    def get_user_settings_cache(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Get cached user notification settings
        
        Args:
            user_id: User ID
            
        Returns:
            User settings or None if not cached
        """
        key = f"user_settings:{user_id}"
        return self.get_cache(key)
    
    def set_notification_queue_cache(self, queue_name: str, notifications: List[Dict[str, Any]]) -> None:
        """
        Cache notification queue state
        
        Args:
            queue_name: Queue name
            notifications: List of notifications
        """
        key = f"queue_cache:{queue_name}"
        self.set_cache(key, notifications, ttl=1800)  # 30 minutes cache
    
    def get_notification_queue_cache(self, queue_name: str) -> Optional[List[Dict[str, Any]]]:
        """
        Get cached notification queue state
        
        Args:
            queue_name: Queue name
            
        Returns:
            List of notifications or None if not cached
        """
        key = f"queue_cache:{queue_name}"
        return self.get_cache(key)
    
    def increment_counter(self, counter_name: str) -> int:
        """
        Increment counter
        
        Args:
            counter_name: Counter name
            
        Returns:
            New counter value
        """
        try:
            return self.redis_client.incr(counter_name)
            
        except Exception as e:
            logger.error(f"Failed to increment counter {counter_name}: {e}")
            return 0
    
    def decrement_counter(self, counter_name: str) -> int:
        """
        Decrement counter
        
        Args:
            counter_name: Counter name
            
        Returns:
            New counter value
        """
        try:
            return self.redis_client.decr(counter_name)
            
        except Exception as e:
            logger.error(f"Failed to decrement counter {counter_name}: {e}")
            return 0
    
    def set_hash_field(self, hash_name: str, field: str, value: str) -> None:
        """
        Set hash field
        
        Args:
            hash_name: Hash name
            field: Field name
            value: Field value
        """
        try:
            self.redis_client.hset(hash_name, field, value)
            
        except Exception as e:
            logger.error(f"Failed to set hash field {hash_name}.{field}: {e}")
            raise
    
    def get_hash_field(self, hash_name: str, field: str) -> Optional[str]:
        """
        Get hash field
        
        Args:
            hash_name: Hash name
            field: Field name
            
        Returns:
            Field value or None if not found
        """
        try:
            return self.redis_client.hget(hash_name, field)
            
        except Exception as e:
            logger.error(f"Failed to get hash field {hash_name}.{field}: {e}")
            return None
    
    def get_all_hash_fields(self, hash_name: str) -> Dict[str, str]:
        """
        Get all hash fields
        
        Args:
            hash_name: Hash name
            
        Returns:
            Dictionary of field-value pairs
        """
        try:
            return self.redis_client.hgetall(hash_name)
            
        except Exception as e:
            logger.error(f"Failed to get all hash fields for {hash_name}: {e}")
            return {}
    
    def add_to_set(self, set_name: str, value: str) -> bool:
        """
        Add value to set
        
        Args:
            set_name: Set name
            value: Value to add
            
        Returns:
            True if added, False if already exists
        """
        try:
            result = self.redis_client.sadd(set_name, value)
            return result > 0
            
        except Exception as e:
            logger.error(f"Failed to add to set {set_name}: {e}")
            return False
    
    def remove_from_set(self, set_name: str, value: str) -> bool:
        """
        Remove value from set
        
        Args:
            set_name: Set name
            value: Value to remove
            
        Returns:
            True if removed, False if not found
        """
        try:
            result = self.redis_client.srem(set_name, value)
            return result > 0
            
        except Exception as e:
            logger.error(f"Failed to remove from set {set_name}: {e}")
            return False
    
    def is_in_set(self, set_name: str, value: str) -> bool:
        """
        Check if value is in set
        
        Args:
            set_name: Set name
            value: Value to check
            
        Returns:
            True if in set, False otherwise
        """
        try:
            return self.redis_client.sismember(set_name, value)
            
        except Exception as e:
            logger.error(f"Failed to check set membership {set_name}: {e}")
            return False
    
    def get_set_members(self, set_name: str) -> Set[str]:
        """
        Get all set members
        
        Args:
            set_name: Set name
            
        Returns:
            Set of members
        """
        try:
            return self.redis_client.smembers(set_name)
            
        except Exception as e:
            logger.error(f"Failed to get set members for {set_name}: {e}")
            return set()
    
    def clear_cache_pattern(self, pattern: str) -> int:
        """
        Clear cache by pattern
        
        Args:
            pattern: Key pattern (e.g., "user_settings:*")
            
        Returns:
            Number of keys deleted
        """
        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                return self.redis_client.delete(*keys)
            return 0
            
        except Exception as e:
            logger.error(f"Failed to clear cache pattern {pattern}: {e}")
            return 0
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics
        
        Returns:
            Dictionary with cache statistics
        """
        try:
            info = self.redis_client.info()
            
            # Calculate hit rate
            hits = info.get("keyspace_hits", 0)
            misses = info.get("keyspace_misses", 0)
            total_requests = hits + misses
            
            hit_rate = hits / total_requests if total_requests > 0 else 0
            miss_rate = misses / total_requests if total_requests > 0 else 0
            
            return {
                "memory_usage": info.get("used_memory", 0),
                "hit_rate": hit_rate,
                "miss_rate": miss_rate,
                "expired_keys": info.get("expired_keys", 0)
            }
            
        except Exception as e:
            logger.error(f"Failed to get cache stats: {e}")
            return {
                "memory_usage": 0,
                "hit_rate": 0,
                "miss_rate": 0,
                "expired_keys": 0
            }
    
    def cleanup_expired_cache(self) -> int:
        """
        Clean up expired cache entries
        
        Returns:
            Number of expired keys cleaned up
        """
        try:
            # Get all keys
            all_keys = self.redis_client.keys("*")
            expired_keys = []
            
            for key in all_keys:
                ttl = self.redis_client.ttl(key)
                if ttl == -1:  # Key exists but has no expiry
                    continue
                elif ttl == -2:  # Key doesn't exist (expired)
                    expired_keys.append(key)
            
            if expired_keys:
                return self.redis_client.delete(*expired_keys)
            
            return 0
            
        except Exception as e:
            logger.error(f"Failed to cleanup expired cache: {e}")
            return 0
