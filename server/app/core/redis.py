"""
Redis client configuration
"""
import os
import redis
import logging

logger = logging.getLogger(__name__)

def get_redis_client():
    """Get Redis client instance"""
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    try:
        # Parse Redis URL
        if redis_url.startswith("redis://"):
            # Simple Redis connection
            client = redis.from_url(redis_url, decode_responses=True)
        else:
            # Fallback to localhost
            client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
        
        # Test connection
        client.ping()
        logger.info(f"Redis client connected successfully to {redis_url}")
        return client
        
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")
        # Return a mock client for development
        return MockRedisClient()

class MockRedisClient:
    """Mock Redis client for development when Redis is not available"""
    
    def __init__(self):
        self._data = {}
        logger.warning("Using MockRedisClient - Redis not available")
    
    def get(self, key):
        return self._data.get(key)
    
    def set(self, key, value, ex=None):
        self._data[key] = value
        return True
    
    def delete(self, *keys):
        count = 0
        for key in keys:
            if key in self._data:
                del self._data[key]
                count += 1
        return count
    
    def exists(self, key):
        return key in self._data
    
    def ttl(self, key):
        return -1  # No expiry for mock
    
    def expire(self, key, time):
        return True
    
    def incr(self, name):
        current = int(self._data.get(name, 0))
        new_value = current + 1
        self._data[name] = str(new_value)
        return new_value
    
    def decr(self, name):
        current = int(self._data.get(name, 0))
        new_value = current - 1
        self._data[name] = str(new_value)
        return new_value
    
    def hset(self, name, key, value):
        if name not in self._data:
            self._data[name] = {}
        self._data[name][key] = value
        return True
    
    def hget(self, name, key):
        return self._data.get(name, {}).get(key)
    
    def hgetall(self, name):
        return self._data.get(name, {})
    
    def sadd(self, name, *values):
        if name not in self._data:
            self._data[name] = set()
        count = 0
        for value in values:
            if value not in self._data[name]:
                self._data[name].add(value)
                count += 1
        return count
    
    def srem(self, name, *values):
        if name not in self._data:
            return 0
        count = 0
        for value in values:
            if value in self._data[name]:
                self._data[name].remove(value)
                count += 1
        return count
    
    def sismember(self, name, value):
        return value in self._data.get(name, set())
    
    def smembers(self, name):
        return self._data.get(name, set())
    
    def keys(self, pattern):
        # Simple pattern matching for mock
        if pattern == "*":
            return list(self._data.keys())
        return [key for key in self._data.keys() if key.startswith(pattern.replace("*", ""))]
    
    def info(self):
        return {
            "used_memory": 0,
            "keyspace_hits": 0,
            "keyspace_misses": 0,
            "expired_keys": 0
        }
    
    def lpush(self, name, *values):
        if name not in self._data:
            self._data[name] = []
        for value in values:
            self._data[name].insert(0, value)
        return len(self._data[name])
    
    def rpop(self, name):
        if name not in self._data or not self._data[name]:
            return None
        return self._data[name].pop()
    
    def llen(self, name):
        return len(self._data.get(name, []))
