import pytest
import json
import time
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

class TestBotCache:
    """Test suite for BotCache class."""

    def test_bot_cache_initialization_with_redis(self):
        """Test BotCache initialization with Redis connection."""
        with patch('redis.Redis') as mock_redis:
            mock_redis_instance = Mock()
            mock_redis.return_value = mock_redis_instance
            mock_redis_instance.ping.return_value = True
            
            from app.utils.cache import BotCache
            cache = BotCache("test_service", redis_url="redis://localhost:6379")
            
            assert cache.service_name == "test_service"
            assert cache.redis_available is True
            mock_redis.assert_called_once()

    def test_bot_cache_initialization_fallback(self):
        """Test BotCache initialization with fallback to in-memory."""
        with patch('redis.Redis') as mock_redis:
            mock_redis.side_effect = Exception("Redis connection failed")
            
            from app.utils.cache import BotCache
            cache = BotCache("test_service", redis_url="redis://localhost:6379")
            
            assert cache.service_name == "test_service"
            assert cache.redis_available is False
            assert cache.memory_cache == {}

    def test_set_and_get_with_redis(self):
        """Test set and get operations with Redis."""
        with patch('redis.Redis') as mock_redis:
            mock_redis_instance = Mock()
            mock_redis.return_value = mock_redis_instance
            mock_redis_instance.ping.return_value = True
            mock_redis_instance.setex.return_value = True
            mock_redis_instance.get.return_value = json.dumps({"test": "value"}).encode()
            
            from app.utils.cache import BotCache
            cache = BotCache("test_service")
            
            # Test set
            result = cache.set("test_key", {"test": "value"}, ttl=60)
            assert result is True
            mock_redis_instance.setex.assert_called_once()
            
            # Test get
            result = cache.get("test_key")
            assert result == {"test": "value"}
            mock_redis_instance.get.assert_called_once()

    def test_set_and_get_with_fallback(self):
        """Test set and get operations with in-memory fallback."""
        with patch('redis.Redis') as mock_redis:
            mock_redis.side_effect = Exception("Redis unavailable")
            
            from app.utils.cache import BotCache
            cache = BotCache("test_service")
            
            # Test set
            result = cache.set("test_key", {"test": "value"}, ttl=60)
            assert result is True
            assert "test_service:test_key" in cache.memory_cache
            
            # Test get
            result = cache.get("test_key")
            assert result == {"test": "value"}

    def test_delete_with_redis(self):
        """Test delete operation with Redis."""
        with patch('redis.Redis') as mock_redis:
            mock_redis_instance = Mock()
            mock_redis.return_value = mock_redis_instance
            mock_redis_instance.ping.return_value = True
            mock_redis_instance.delete.return_value = 1
            
            from app.utils.cache import BotCache
            cache = BotCache("test_service")
            
            result = cache.delete("test_key")
            assert result is True
            mock_redis_instance.delete.assert_called_once()

    def test_exists_with_redis(self):
        """Test exists operation with Redis."""
        with patch('redis.Redis') as mock_redis:
            mock_redis_instance = Mock()
            mock_redis.return_value = mock_redis_instance
            mock_redis_instance.ping.return_value = True
            mock_redis_instance.exists.return_value = 1
            
            from app.utils.cache import BotCache
            cache = BotCache("test_service")
            
            result = cache.exists("test_key")
            assert result is True
            mock_redis_instance.exists.assert_called_once()

    def test_list_operations_with_redis(self):
        """Test list operations (lpush, lrange, ltrim) with Redis."""
        with patch('redis.Redis') as mock_redis:
            mock_redis_instance = Mock()
            mock_redis.return_value = mock_redis_instance
            mock_redis_instance.ping.return_value = True
            mock_redis_instance.lpush.return_value = 1
            mock_redis_instance.lrange.return_value = [b'{"item": "value"}']
            mock_redis_instance.ltrim.return_value = True
            
            from app.utils.cache import BotCache
            cache = BotCache("test_service")
            
            # Test lpush
            result = cache.lpush("test_list", {"item": "value"})
            assert result is True
            mock_redis_instance.lpush.assert_called_once()
            
            # Test lrange
            result = cache.lrange("test_list", 0, 10)
            assert result == [{"item": "value"}]
            mock_redis_instance.lrange.assert_called_once()
            
            # Test ltrim
            result = cache.ltrim("test_list", 0, 50)
            assert result is True
            mock_redis_instance.ltrim.assert_called_once()

    def test_memory_cache_ttl_expiration(self):
        """Test TTL expiration in memory cache."""
        with patch('redis.Redis') as mock_redis:
            mock_redis.side_effect = Exception("Redis unavailable")
            
            from app.utils.cache import BotCache
            cache = BotCache("test_service")
            
            # Set with short TTL
            cache.set("test_key", {"test": "value"}, ttl=1)
            
            # Should exist immediately
            assert cache.get("test_key") == {"test": "value"}
            
            # Wait for expiration
            time.sleep(1.1)
            
            # Should be expired
            assert cache.get("test_key") is None

class TestCacheUtilityFunctions:
    """Test suite for cache utility functions."""

    def test_get_cache_function(self):
        """Test get_cache function returns BotCache instance."""
        with patch('app.utils.cache.BotCache') as mock_bot_cache:
            mock_instance = Mock()
            mock_bot_cache.return_value = mock_instance
            
            from app.utils.cache import get_cache
            result = get_cache("test_service")
            
            assert result == mock_instance
            mock_bot_cache.assert_called_once_with("test_service")

    def test_cache_recent_response(self):
        """Test cache_recent_response function."""
        with patch('app.utils.cache.get_cache') as mock_get_cache:
            mock_cache = Mock()
            mock_cache.lpush.return_value = True
            mock_cache.ltrim.return_value = True
            mock_get_cache.return_value = mock_cache
            
            from app.utils.cache import cache_recent_response
            result = cache_recent_response("peter", "test response")
            
            assert result is True
            mock_cache.lpush.assert_called_once()
            mock_cache.ltrim.assert_called_once()

    def test_get_recent_responses(self):
        """Test get_recent_responses function."""
        with patch('app.utils.cache.get_cache') as mock_get_cache:
            mock_cache = Mock()
            mock_cache.lrange.return_value = ["response1", "response2"]
            mock_get_cache.return_value = mock_cache
            
            from app.utils.cache import get_recent_responses
            result = get_recent_responses("peter", limit=10)
            
            assert result == ["response1", "response2"]
            mock_cache.lrange.assert_called_once_with("responses:recent:peter", 0, 9)

    def test_cache_discord_state(self):
        """Test cache_discord_state function."""
        with patch('app.utils.cache.get_cache') as mock_get_cache:
            mock_cache = Mock()
            mock_cache.set.return_value = True
            mock_get_cache.return_value = mock_cache
            
            from app.utils.cache import cache_discord_state
            state_data = {
                'ready': True,
                'mention': '<@123456789>',
                'user_id': 123456789,
                'username': 'Peter Griffin'
            }
            
            result = cache_discord_state("peter", state_data, ttl=3600)
            
            assert result is True
            mock_cache.set.assert_called_once_with("discord:state:peter", state_data, ttl=3600)

    def test_get_discord_state(self):
        """Test get_discord_state function."""
        with patch('app.utils.cache.get_cache') as mock_get_cache:
            mock_cache = Mock()
            expected_state = {
                'ready': True,
                'mention': '<@123456789>',
                'user_id': 123456789,
                'username': 'Peter Griffin'
            }
            mock_cache.get.return_value = expected_state
            mock_get_cache.return_value = mock_cache
            
            from app.utils.cache import get_discord_state
            result = get_discord_state("peter")
            
            assert result == expected_state
            mock_cache.get.assert_called_once_with("discord:state:peter")

class TestCacheIntegrationScenarios:
    """Test real-world cache integration scenarios."""

    def test_response_deduplication_workflow(self):
        """Test complete response deduplication workflow."""
        with patch('redis.Redis') as mock_redis:
            mock_redis_instance = Mock()
            mock_redis.return_value = mock_redis_instance
            mock_redis_instance.ping.return_value = True
            
            # Mock Redis operations for the workflow
            mock_redis_instance.lrange.return_value = [
                json.dumps("previous response").encode(),
                json.dumps("another response").encode()
            ]
            mock_redis_instance.lpush.return_value = 1
            mock_redis_instance.ltrim.return_value = True
            
            from app.utils.cache import cache_recent_response, get_recent_responses
            
            # Get recent responses
            recent = get_recent_responses("peter", limit=50)
            assert len(recent) == 2
            
            # Cache new response
            result = cache_recent_response("peter", "new response")
            assert result is True

    def test_discord_state_persistence_workflow(self):
        """Test Discord state persistence across restarts."""
        with patch('redis.Redis') as mock_redis:
            mock_redis_instance = Mock()
            mock_redis.return_value = mock_redis_instance
            mock_redis_instance.ping.return_value = True
            
            # Mock state retrieval
            cached_state = {
                'ready': True,
                'mention': '<@123456789>',
                'user_id': 123456789,
                'username': 'Peter Griffin',
                'timestamp': '2024-01-15T10:30:00Z'
            }
            mock_redis_instance.get.return_value = json.dumps(cached_state).encode()
            mock_redis_instance.setex.return_value = True
            
            from app.utils.cache import cache_discord_state, get_discord_state
            
            # Simulate service restart - get cached state
            state = get_discord_state("peter")
            assert state == cached_state
            
            # Update state
            new_state = cached_state.copy()
            new_state['timestamp'] = '2024-01-15T11:00:00Z'
            result = cache_discord_state("peter", new_state, ttl=3600)
            assert result is True

    def test_rag_query_caching_workflow(self):
        """Test RAG query result caching workflow."""
        with patch('redis.Redis') as mock_redis:
            mock_redis_instance = Mock()
            mock_redis.return_value = mock_redis_instance
            mock_redis_instance.ping.return_value = True
            
            # Mock query result caching
            query_results = [
                {
                    "content": "Peter Griffin is the main character...",
                    "source": "familyguy.fandom.com/wiki/Peter_Griffin",
                    "relevance_score": 0.89
                }
            ]
            mock_redis_instance.get.return_value = json.dumps(query_results).encode()
            mock_redis_instance.setex.return_value = True
            
            from app.utils.cache import BotCache
            cache = BotCache("rag")
            
            # Simulate cache hit
            cached_results = cache.get("query:chicken_fight:3")
            assert cached_results == query_results
            
            # Simulate cache miss and set
            cache.set("query:new_query:3", query_results, ttl=3600)

    def test_cache_health_monitoring(self):
        """Test cache health monitoring functionality."""
        with patch('redis.Redis') as mock_redis:
            mock_redis_instance = Mock()
            mock_redis.return_value = mock_redis_instance
            mock_redis_instance.ping.return_value = True
            mock_redis_instance.info.return_value = {
                'used_memory': 1024000,
                'used_memory_human': '1000K',
                'connected_clients': 5
            }
            
            from app.utils.cache import BotCache
            cache = BotCache("health_test")
            
            # Test health check
            assert cache.redis_available is True
            
            # Test Redis info (would be used in health endpoints)
            info = mock_redis_instance.info()
            assert 'used_memory' in info
            assert 'connected_clients' in info

class TestCacheErrorHandling:
    """Test cache error handling and fallback scenarios."""

    def test_redis_connection_failure_graceful_fallback(self):
        """Test graceful fallback when Redis connection fails."""
        with patch('redis.Redis') as mock_redis:
            mock_redis.side_effect = Exception("Connection refused")
            
            from app.utils.cache import BotCache
            cache = BotCache("test_service")
            
            # Should fallback to memory cache
            assert cache.redis_available is False
            
            # Operations should still work
            assert cache.set("key", "value") is True
            assert cache.get("key") == "value"
            assert cache.exists("key") is True
            assert cache.delete("key") is True

    def test_redis_operation_failure_fallback(self):
        """Test fallback when Redis operations fail."""
        with patch('redis.Redis') as mock_redis:
            mock_redis_instance = Mock()
            mock_redis.return_value = mock_redis_instance
            mock_redis_instance.ping.return_value = True
            
            # Simulate Redis operation failure
            mock_redis_instance.get.side_effect = Exception("Redis operation failed")
            
            from app.utils.cache import BotCache
            cache = BotCache("test_service")
            
            # Should handle error gracefully
            result = cache.get("test_key")
            assert result is None  # Should return None on error

    def test_json_serialization_error_handling(self):
        """Test handling of JSON serialization errors."""
        with patch('redis.Redis') as mock_redis:
            mock_redis_instance = Mock()
            mock_redis.return_value = mock_redis_instance
            mock_redis_instance.ping.return_value = True
            
            from app.utils.cache import BotCache
            cache = BotCache("test_service")
            
            # Test with non-serializable object
            class NonSerializable:
                pass
            
            result = cache.set("test_key", NonSerializable())
            assert result is False  # Should fail gracefully

    def test_corrupted_cache_data_handling(self):
        """Test handling of corrupted cache data."""
        with patch('redis.Redis') as mock_redis:
            mock_redis_instance = Mock()
            mock_redis.return_value = mock_redis_instance
            mock_redis_instance.ping.return_value = True
            mock_redis_instance.get.return_value = b"invalid json data"
            
            from app.utils.cache import BotCache
            cache = BotCache("test_service")
            
            # Should handle corrupted data gracefully
            result = cache.get("test_key")
            assert result is None  # Should return None for corrupted data

class TestCachePerformance:
    """Test cache performance characteristics."""

    def test_memory_cache_cleanup(self):
        """Test memory cache cleanup of expired entries."""
        with patch('redis.Redis') as mock_redis:
            mock_redis.side_effect = Exception("Redis unavailable")
            
            from app.utils.cache import BotCache
            cache = BotCache("test_service")
            
            # Add multiple entries with different TTLs
            cache.set("key1", "value1", ttl=1)
            cache.set("key2", "value2", ttl=2)
            cache.set("key3", "value3", ttl=3)
            
            # All should exist initially
            assert cache.exists("key1") is True
            assert cache.exists("key2") is True
            assert cache.exists("key3") is True
            
            # Wait for first expiration
            time.sleep(1.1)
            
            # First should be expired
            assert cache.exists("key1") is False
            assert cache.exists("key2") is True
            assert cache.exists("key3") is True

    def test_cache_key_prefixing(self):
        """Test proper cache key prefixing."""
        with patch('redis.Redis') as mock_redis:
            mock_redis_instance = Mock()
            mock_redis.return_value = mock_redis_instance
            mock_redis_instance.ping.return_value = True
            mock_redis_instance.setex.return_value = True
            
            from app.utils.cache import BotCache
            cache = BotCache("test_service")
            
            cache.set("test_key", "value")
            
            # Should call Redis with prefixed key
            call_args = mock_redis_instance.setex.call_args
            assert call_args[0][0] == "bot:test_service:test_key" 