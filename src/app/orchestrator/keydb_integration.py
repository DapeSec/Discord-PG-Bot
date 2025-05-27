"""
KeyDB integration functions for the orchestrator service.
Provides caching functionality with fallback to in-memory cache.
"""

# Import cache utilities for KeyDB integration
try:
    from src.app.utils.cache import cache_recent_response, get_recent_responses, get_cache
    CACHE_AVAILABLE = True
    print("✅ KeyDB cache utilities imported successfully")
except ImportError as e:
    print(f"⚠️ Cache utilities not available: {e}. Using fallback in-memory cache.")
    CACHE_AVAILABLE = False

# Configuration constants
DUPLICATE_CACHE_SIZE = 50  # Keep last 50 responses per character
DUPLICATE_SIMILARITY_THRESHOLD = 0.8  # 80% similarity threshold

# Fallback in-memory cache
recent_responses_cache = {}

def is_duplicate_response_keydb(character_name, response_text, conversation_history):
    """
    Check if the response is too similar to recent responses from the same character.
    Uses KeyDB cache when available, falls back to in-memory cache.
    Returns True if it's a duplicate, False otherwise.
    """
    try:
        # Clean the response for comparison
        cleaned_response = response_text.lower().strip()
        
        if CACHE_AVAILABLE:
            # Use KeyDB cache for duplicate detection
            recent_responses = get_recent_responses(character_name, limit=DUPLICATE_CACHE_SIZE)
            
            # Check for duplicates against cached responses
            for recent_response in recent_responses:
                if _check_response_similarity(cleaned_response, recent_response):
                    print(f"🔄 KeyDB: Duplicate detected for {character_name}")
                    return True
            
            # Cache this response for future duplicate detection
            cache_recent_response(character_name, cleaned_response, max_responses=DUPLICATE_CACHE_SIZE)
            print(f"💾 KeyDB: Cached response for {character_name}")
            return False
            
        else:
            # Fallback to original in-memory cache logic
            global recent_responses_cache
            if character_name not in recent_responses_cache:
                recent_responses_cache[character_name] = []
            
            # Check against recent responses from this character
            for recent_response in recent_responses_cache[character_name]:
                if _check_response_similarity(cleaned_response, recent_response):
                    print(f"🔄 Memory: Duplicate detected for {character_name}")
                    return True
            
            # Add this response to the cache
            recent_responses_cache[character_name].append(cleaned_response)
            
            # Keep cache size manageable
            if len(recent_responses_cache[character_name]) > DUPLICATE_CACHE_SIZE:
                recent_responses_cache[character_name].pop(0)
            
            return False
        
    except Exception as e:
        print(f"⚠️ Error in duplicate detection: {e}")
        return False

def _check_response_similarity(cleaned_response, recent_response):
    """
    Helper function to check similarity between two responses.
    Extracted for reuse between KeyDB and fallback implementations.
    """
    try:
        # Simple similarity check - could be improved with more sophisticated methods
        if len(cleaned_response) > 0 and len(recent_response) > 0:
            # Calculate similarity based on character overlap
            shorter = min(len(cleaned_response), len(recent_response))
            longer = max(len(cleaned_response), len(recent_response))
            
            if shorter > 0:
                # If responses are very similar length and content
                if abs(len(cleaned_response) - len(recent_response)) < 10:
                    common_chars = sum(1 for a, b in zip(cleaned_response, recent_response) if a == b)
                    similarity = common_chars / longer
                    
                    if similarity > DUPLICATE_SIMILARITY_THRESHOLD:
                        return True
            
            # Also check for exact substring matches (common with the golf repetition)
            if len(cleaned_response) > 50 and cleaned_response in recent_response:
                return True
            if len(recent_response) > 50 and recent_response in cleaned_response:
                return True
        
        return False
        
    except Exception as e:
        print(f"⚠️ Error in similarity check: {e}")
        return False

def cache_conversation_context(channel_id, context_data, ttl=3600):
    """Cache conversation context for a channel."""
    if CACHE_AVAILABLE:
        cache = get_cache("conversations")
        return cache.set(f"context:{channel_id}", context_data, ttl)
    return False

def get_conversation_context(channel_id):
    """Get cached conversation context."""
    if CACHE_AVAILABLE:
        cache = get_cache("conversations")
        return cache.get(f"context:{channel_id}", {})
    return {}

def cache_health_check():
    """Check if cache is working properly."""
    if CACHE_AVAILABLE:
        try:
            cache = get_cache("health")
            test_key = "health_check"
            test_value = {"timestamp": "test"}
            
            # Test basic operations
            cache.set(test_key, test_value, ttl=60)
            retrieved = cache.get(test_key)
            
            return retrieved == test_value
        except Exception as e:
            print(f"⚠️ Cache health check failed: {e}")
            return False
    return False 