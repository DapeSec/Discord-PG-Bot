"""
Cache utility for Discord bot services using KeyDB/Redis.
Provides simple caching functionality with automatic fallback.
"""

import os
import json
import time
import logging
from typing import Any, Optional, Union
from datetime import timedelta

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None

logger = logging.getLogger(__name__)

class BotCache:
    """
    Simple cache implementation with KeyDB/Redis backend.
    Falls back to in-memory cache if Redis is unavailable.
    """
    
    def __init__(self, redis_url: Optional[str] = None, prefix: str = "bot"):
        self.prefix = prefix
        self.redis_client = None
        self.fallback_cache = {}  # In-memory fallback
        
        # Try to connect to Redis/KeyDB
        if REDIS_AVAILABLE and redis_url:
            try:
                self.redis_client = redis.from_url(redis_url, decode_responses=True)
                # Test connection
                self.redis_client.ping()
                logger.info(f"Connected to Redis/KeyDB at {redis_url}")
            except Exception as e:
                logger.warning(f"Failed to connect to Redis/KeyDB: {e}. Using in-memory cache.")
                self.redis_client = None
        else:
            logger.info("Redis not available or no URL provided. Using in-memory cache.")
    
    def _make_key(self, key: str) -> str:
        """Create a prefixed cache key."""
        return f"{self.prefix}:{key}"
    
    def set(self, key: str, value: Any, ttl: Optional[Union[int, timedelta]] = None) -> bool:
        """
        Set a value in the cache with optional TTL.
        
        Args:
            key: Cache key
            value: Value to cache (will be JSON serialized)
            ttl: Time to live in seconds or timedelta
            
        Returns:
            True if successful, False otherwise
        """
        try:
            cache_key = self._make_key(key)
            serialized_value = json.dumps(value)
            
            if self.redis_client:
                # Use Redis/KeyDB
                if ttl:
                    if isinstance(ttl, timedelta):
                        ttl = int(ttl.total_seconds())
                    return self.redis_client.setex(cache_key, ttl, serialized_value)
                else:
                    return self.redis_client.set(cache_key, serialized_value)
            else:
                # Use in-memory fallback
                expiry = None
                if ttl:
                    if isinstance(ttl, timedelta):
                        ttl = int(ttl.total_seconds())
                    expiry = time.time() + ttl
                
                self.fallback_cache[cache_key] = {
                    'value': serialized_value,
                    'expiry': expiry
                }
                return True
                
        except Exception as e:
            logger.error(f"Failed to set cache key {key}: {e}")
            return False
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a value from the cache.
        
        Args:
            key: Cache key
            default: Default value if key not found
            
        Returns:
            Cached value or default
        """
        try:
            cache_key = self._make_key(key)
            
            if self.redis_client:
                # Use Redis/KeyDB
                value = self.redis_client.get(cache_key)
                if value is not None:
                    return json.loads(value)
            else:
                # Use in-memory fallback
                cached_item = self.fallback_cache.get(cache_key)
                if cached_item:
                    # Check expiry
                    if cached_item['expiry'] is None or time.time() < cached_item['expiry']:
                        return json.loads(cached_item['value'])
                    else:
                        # Expired, remove it
                        del self.fallback_cache[cache_key]
            
            return default
            
        except Exception as e:
            logger.error(f"Failed to get cache key {key}: {e}")
            return default
    
    def delete(self, key: str) -> bool:
        """
        Delete a key from the cache.
        
        Args:
            key: Cache key to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            cache_key = self._make_key(key)
            
            if self.redis_client:
                return bool(self.redis_client.delete(cache_key))
            else:
                if cache_key in self.fallback_cache:
                    del self.fallback_cache[cache_key]
                    return True
                return False
                
        except Exception as e:
            logger.error(f"Failed to delete cache key {key}: {e}")
            return False
    
    def exists(self, key: str) -> bool:
        """
        Check if a key exists in the cache.
        
        Args:
            key: Cache key to check
            
        Returns:
            True if key exists, False otherwise
        """
        try:
            cache_key = self._make_key(key)
            
            if self.redis_client:
                return bool(self.redis_client.exists(cache_key))
            else:
                cached_item = self.fallback_cache.get(cache_key)
                if cached_item:
                    # Check expiry
                    if cached_item['expiry'] is None or time.time() < cached_item['expiry']:
                        return True
                    else:
                        # Expired, remove it
                        del self.fallback_cache[cache_key]
                return False
                
        except Exception as e:
            logger.error(f"Failed to check cache key {key}: {e}")
            return False
    
    def list_push(self, key: str, value: Any, max_length: Optional[int] = None) -> bool:
        """
        Push a value to a list and optionally trim to max length.
        Useful for storing recent responses, conversation history, etc.
        
        Args:
            key: List key
            value: Value to push
            max_length: Maximum list length (oldest items removed)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            cache_key = self._make_key(key)
            serialized_value = json.dumps(value)
            
            if self.redis_client:
                # Use Redis list operations
                self.redis_client.lpush(cache_key, serialized_value)
                if max_length:
                    self.redis_client.ltrim(cache_key, 0, max_length - 1)
                return True
            else:
                # Use in-memory list
                if cache_key not in self.fallback_cache:
                    self.fallback_cache[cache_key] = {'value': [], 'expiry': None}
                
                cache_list = json.loads(self.fallback_cache[cache_key]['value']) if isinstance(self.fallback_cache[cache_key]['value'], str) else self.fallback_cache[cache_key]['value']
                if not isinstance(cache_list, list):
                    cache_list = []
                
                cache_list.insert(0, value)  # Insert at beginning (like lpush)
                
                if max_length and len(cache_list) > max_length:
                    cache_list = cache_list[:max_length]
                
                self.fallback_cache[cache_key]['value'] = cache_list
                return True
                
        except Exception as e:
            logger.error(f"Failed to push to list {key}: {e}")
            return False
    
    def list_get(self, key: str, start: int = 0, end: int = -1) -> list:
        """
        Get items from a list.
        
        Args:
            key: List key
            start: Start index
            end: End index (-1 for all)
            
        Returns:
            List of items
        """
        try:
            cache_key = self._make_key(key)
            
            if self.redis_client:
                items = self.redis_client.lrange(cache_key, start, end)
                return [json.loads(item) for item in items]
            else:
                cached_item = self.fallback_cache.get(cache_key)
                if cached_item and isinstance(cached_item['value'], list):
                    cache_list = cached_item['value']
                    if end == -1:
                        return cache_list[start:]
                    else:
                        return cache_list[start:end+1]
                return []
                
        except Exception as e:
            logger.error(f"Failed to get list {key}: {e}")
            return []

# Global cache instance
_cache_instance = None

def get_cache(service_name: str = "bot") -> BotCache:
    """
    Get a cache instance for the service.
    
    Args:
        service_name: Name of the service (used as cache prefix)
        
    Returns:
        BotCache instance
    """
    global _cache_instance
    
    if _cache_instance is None:
        redis_url = os.getenv('REDIS_URL')
        _cache_instance = BotCache(redis_url=redis_url, prefix=service_name)
    
    return _cache_instance

# Convenience functions
def cache_recent_response(character: str, response: str, max_responses: int = 50) -> bool:
    """Cache a recent response for duplicate detection."""
    cache = get_cache("responses")
    return cache.list_push(f"recent:{character}", response, max_responses)

def get_recent_responses(character: str, limit: int = 50) -> list:
    """Get recent responses for a character."""
    cache = get_cache("responses")
    return cache.list_get(f"recent:{character}", 0, limit - 1)

def cache_discord_state(character: str, state_data: dict, ttl: int = 3600) -> bool:
    """Cache Discord connection state."""
    cache = get_cache("discord")
    return cache.set(f"state:{character}", state_data, ttl)

def get_discord_state(character: str) -> Optional[dict]:
    """Get Discord connection state."""
    cache = get_cache("discord")
    return cache.get(f"state:{character}") 