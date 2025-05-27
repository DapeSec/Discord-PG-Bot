# KeyDB Implementation Guide

## Overview

This guide walks you through implementing KeyDB in your Discord Family Guy Bot to make services more stateless and improve performance.

## What's Been Set Up

### ✅ **Infrastructure Added**
1. **KeyDB Service** - Added to `docker/docker-compose.yml`
2. **KeyDB Commander** - Web UI for debugging at `http://localhost:8081`
3. **Dependencies** - KeyDB client libraries added to requirements files
4. **Cache Utility** - Created `src/app/utils/cache.py` with fallback support

### ✅ **Services Updated**
- **Orchestrator** - Now has `KEYDB_URL` environment variable
- **Discord Handlers** - All three handlers have KeyDB connectivity
- **RAG Retriever** - Connected to KeyDB for caching

## Quick Start

### 1. **Start the Services**
```bash
cd docker
docker-compose up -d keydb keydb-commander
```

### 2. **Verify KeyDB is Running**
```bash
# Check KeyDB health
docker-compose exec keydb keydb-cli ping
# Should return: PONG

# Check web UI
open http://localhost:8081
```

### 3. **Test the Cache Utility**
```python
# In any service
from src.app.utils.cache import get_cache

cache = get_cache("test")
cache.set("hello", "world", ttl=60)
print(cache.get("hello"))  # Should print: world
```

## Implementation Phases

### 📋 **Phase 1: Basic Caching (Start Here)**

#### **Replace In-Memory Response Cache in Orchestrator**

Current code in `src/app/orchestrator/server.py`:
```python
# Current: In-memory cache
recent_responses_cache = {}

def is_duplicate_response(character_name, response_text, conversation_history):
    if character_name not in recent_responses_cache:
        recent_responses_cache[character_name] = []
    # ... rest of function
```

**Replace with:**
```python
from src.app.utils.cache import cache_recent_response, get_recent_responses

def is_duplicate_response(character_name, response_text, conversation_history):
    """Check if response is duplicate using KeyDB cache."""
    try:
        # Get recent responses from cache
        recent_responses = get_recent_responses(character_name, limit=50)
        
        # Check for duplicates (existing logic)
        cleaned_response = response_text.lower().strip()
        
        for recent_response in recent_responses:
            # Your existing similarity logic here
            if similarity_check(cleaned_response, recent_response):
                print(f"🔄 Duplicate detected for {character_name}")
                return True
        
        # Cache this response
        cache_recent_response(character_name, cleaned_response)
        return False
        
    except Exception as e:
        print(f"⚠️ Error in duplicate detection: {e}")
        return False
```

### 📋 **Phase 2: Discord State Management**

#### **Make Discord Handlers Stateless**

Current code in Discord handlers:
```python
# Current: In-memory state
peter_ready = False
peter_mention = None
peter_id = None
```

**Replace with:**
```python
from src.app.utils.cache import cache_discord_state, get_discord_state

@peter_client.event
async def on_ready():
    """Event fired when Peter Discord client is ready."""
    user = peter_client.user
    
    # Cache state in KeyDB instead of memory
    state_data = {
        'ready': True,
        'mention': f"<@{user.id}>",
        'user_id': user.id,
        'username': user.name,
        'timestamp': datetime.now().isoformat()
    }
    
    cache_discord_state('peter', state_data, ttl=3600)
    print(f"INFO: Peter Bot state cached - {user}")

def get_peter_state():
    """Get Peter's current state from cache."""
    return get_discord_state('peter') or {'ready': False}
```

### 📋 **Phase 3: Session Management**

#### **Cache Conversation Context**

```python
from src.app.utils.cache import get_cache

def cache_conversation_context(channel_id, context_data, ttl=3600):
    """Cache conversation context for a channel."""
    cache = get_cache("conversations")
    return cache.set(f"context:{channel_id}", context_data, ttl)

def get_conversation_context(channel_id):
    """Get cached conversation context."""
    cache = get_cache("conversations")
    return cache.get(f"context:{channel_id}", {})
```

### 📋 **Phase 4: RAG Query Caching**

#### **Cache Frequent RAG Queries**

```python
# In RAG Retriever service
from src.app.utils.cache import get_cache
import hashlib

def retrieve_with_cache(query, num_results=3):
    """Retrieve context with caching."""
    cache = get_cache("rag")
    
    # Create cache key from query
    query_hash = hashlib.md5(query.encode()).hexdigest()
    cache_key = f"query:{query_hash}:{num_results}"
    
    # Check cache first
    cached_result = cache.get(cache_key)
    if cached_result:
        print(f"Cache hit for query: {query[:50]}...")
        return cached_result
    
    # Perform actual retrieval
    result = perform_vector_search(query, num_results)
    
    # Cache result for 1 hour
    cache.set(cache_key, result, ttl=3600)
    
    return result
```

## Monitoring and Debugging

### **KeyDB Commander Web UI**
- **URL**: `http://localhost:8081`
- **Features**: Browse keys, view values, monitor performance
- **Usage**: Great for debugging cache issues

### **Command Line Monitoring**
```bash
# Connect to KeyDB CLI
docker-compose exec keydb keydb-cli

# Monitor commands in real-time
MONITOR

# Check memory usage
INFO memory

# List all keys
KEYS *

# Get specific key
GET bot:responses:recent:peter
```

### **Health Checks**
```python
from src.app.utils.cache import get_cache

def check_cache_health():
    """Check if cache is working."""
    cache = get_cache("health")
    
    # Test basic operations
    test_key = "health_check"
    test_value = {"timestamp": time.time()}
    
    # Set and get
    cache.set(test_key, test_value, ttl=60)
    retrieved = cache.get(test_key)
    
    return retrieved == test_value
```

## Performance Benefits

### **Before KeyDB**
- ❌ In-memory state lost on restart
- ❌ No sharing between service instances
- ❌ Memory usage grows over time
- ❌ Duplicate detection limited to single instance

### **After KeyDB**
- ✅ Persistent state across restarts
- ✅ Shared state between instances
- ✅ Automatic memory management with TTL
- ✅ Global duplicate detection
- ✅ Horizontal scaling capability

## Troubleshooting

### **KeyDB Won't Start**
```bash
# Check logs
docker-compose logs keydb

# Common issues:
# 1. Port 6379 already in use
# 2. Insufficient memory
# 3. Permission issues with volume
```

### **Cache Not Working**
```bash
# Test connection
docker-compose exec keydb keydb-cli ping

# Check if services can connect
docker-compose exec orchestrator python -c "
from src.app.utils.cache import get_cache
cache = get_cache('test')
print('Cache working:', cache.set('test', 'value'))
"
```

### **Performance Issues**
```bash
# Monitor KeyDB performance
docker-compose exec keydb keydb-cli --latency

# Check memory usage
docker-compose exec keydb keydb-cli info memory
```

## Next Steps

1. **Start with Phase 1** - Replace response cache
2. **Test thoroughly** - Ensure no regressions
3. **Move to Phase 2** - Discord state management
4. **Monitor performance** - Use KeyDB Commander
5. **Scale as needed** - Add more KeyDB instances if required

## Configuration Options

### **KeyDB Tuning**
```yaml
# In docker-compose.yml
keydb:
  command: >
    keydb-server 
    --appendonly yes 
    --maxmemory 1gb                    # Increase if needed
    --maxmemory-policy allkeys-lru     # Eviction policy
    --server-threads 4                 # Match your CPU cores
    --multi-threading yes              # Enable multi-threading
    --save 900 1                       # Persistence settings
```

### **Environment Variables**
```bash
# In .env file
REDIS_URL=redis://keydb:6379
CACHE_TTL_DEFAULT=3600
CACHE_MAX_MEMORY=512mb
```

This implementation gives you a solid foundation for making your Discord bot services more stateless and scalable! 