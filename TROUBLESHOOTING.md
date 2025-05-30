# Discord Family Guy Bot - Troubleshooting Guide

## Quick Fix Commands

### 1. Stop and Restart Everything
```bash
cd docker
docker-compose down
docker-compose up -d
```

### 2. Check Service Status
```bash
cd docker
docker-compose ps
docker-compose logs -f
```

### 3. Check Individual Service Logs
```bash
cd docker
docker-compose logs rag-retriever
docker-compose logs orchestrator
docker-compose logs discord-handler
```

## Common Issues and Solutions

This guide covers the most common issues you might encounter with the Discord Family Guy Bot Enterprise Edition (12-microservice architecture).

---

## 🏗️ **Current Architecture Overview**

The system consists of **12 microservices**:
- **3 Discord Handlers**: Peter (6011), Brian (6012), Stewie (6013)
- **3 Core AI Services**: LLM Service (6001), Message Router (6005), Quality Control (6003)  
- **3 Intelligence Services**: Conversation Coordinator (6002), Fine Tuning (6004), Orchestrator (6008)
- **3 Knowledge Services**: Character Config (6006), RAG Retriever (6007), RAG Crawler (6009)
- **Infrastructure**: KeyDB (6379), KeyDB Commander (8081), ChromaDB, Ollama (11434)

---

## 🔧 **Quick Diagnostics**

### **Check All Services Status**
```bash
# Overall health check
docker-compose ps

# Individual service health checks
curl http://localhost:6001/health  # LLM Service
curl http://localhost:6002/health  # Conversation Coordinator  
curl http://localhost:6003/health  # Quality Control
curl http://localhost:6004/health  # Fine Tuning
curl http://localhost:6005/health  # Message Router
curl http://localhost:6006/health  # Character Config
curl http://localhost:6007/health  # RAG Retriever
curl http://localhost:6008/health  # Orchestrator
curl http://localhost:6009/health  # RAG Crawler
curl http://localhost:6011/health  # Peter Discord
curl http://localhost:6012/health  # Brian Discord
curl http://localhost:6013/health  # Stewie Discord

# KeyDB status
curl http://localhost:8081  # KeyDB Commander Web UI
```

---

## 🚨 **Most Common Issues**

### **1. Services Not Starting**

**Symptoms**: `docker-compose ps` shows services as "unhealthy" or "exited"

**Solutions**:
```bash
# Check logs for specific service
docker-compose logs -f <service-name>

# Common service log checks
docker-compose logs -f llm-service
docker-compose logs -f message-router
docker-compose logs -f orchestrator

# Restart specific service
docker-compose restart <service-name>

# Rebuild if code changes were made
docker-compose up --build -d <service-name>
```

### **2. Ollama Connection Issues**

**Symptoms**: "Connection to Ollama failed" in LLM service logs

**Solutions**:
```bash
# 1. Check if Ollama is running
Get-Process -Name "ollama"

# 2. Start Ollama if not running
ollama serve

# 3. Ensure mistral-nemo model is installed
ollama pull mistral-nemo
ollama list  # Verify model is available

# 4. Test Ollama directly
ollama run mistral-nemo "Hello, test message"

# 5. Check Docker can reach Ollama
docker run --rm alpine ping host.docker.internal
```

**Environment Check**:
```bash
# Verify correct Ollama configuration in .env
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=mistral-nemo
```

### **3. Discord Bot Token Issues**

**Symptoms**: Discord handlers failing to connect or authenticate

**Solutions**:
```bash
# 1. Verify tokens in .env file
DISCORD_BOT_TOKEN_PETER=your_peter_bot_token_here
DISCORD_BOT_TOKEN_BRIAN=your_brian_bot_token_here  
DISCORD_BOT_TOKEN_STEWIE=your_stewie_bot_token_here

# 2. Check bot permissions in Discord server
# Required permissions: Send Messages, Read Message History, Use Slash Commands

# 3. Test individual Discord handlers
curl http://localhost:6011/health  # Peter
curl http://localhost:6012/health  # Brian  
curl http://localhost:6013/health  # Stewie

# 4. Check Discord handler logs
docker-compose logs -f peter-discord
docker-compose logs -f brian-discord
docker-compose logs -f stewie-discord
```

### **4. KeyDB Cache Issues**

**Symptoms**: Slow response times, cache misses, services unable to connect to KeyDB

**Solutions**:
```bash
# 1. Check KeyDB status
docker-compose logs -f keydb
curl http://localhost:8081  # Web UI

# 2. Test KeyDB connectivity from services
docker-compose exec message-router ping keydb

# 3. Clear cache if needed
docker-compose exec keydb keydb-cli FLUSHALL

# 4. Monitor cache performance
# Visit http://localhost:8081 for real-time monitoring
```

### **5. RAG System Issues**

**Symptoms**: Responses lack context, ChromaDB errors, slow retrieval

**Solutions**:
```bash
# 1. Check RAG services
curl http://localhost:6007/health  # RAG Retriever
curl http://localhost:6009/health  # RAG Crawler

# 2. Check vector store status
curl http://localhost:6007/vector_store_status

# 3. Test RAG retrieval
curl -X POST http://localhost:6007/retrieve \
  -H "Content-Type: application/json" \
  -d '{"query": "chicken fight", "num_results": 3}'

# 4. Check ChromaDB data
docker-compose logs -f rag-retriever
docker-compose logs -f rag-crawler

# 5. Trigger crawl if needed
curl -X POST http://localhost:6009/crawl/start
```

### **6. Quality Control Issues**

**Symptoms**: Responses rejected, infinite retries, poor response quality

**Solutions**:
```bash
# 1. Check quality control status
curl http://localhost:6003/config

# 2. Adjust quality thresholds if needed (in .env)
COLD_START_THRESHOLD=30.0      # Lower = more lenient
WARM_CONVERSATION_THRESHOLD=60.0
HOT_CONVERSATION_THRESHOLD=75.0

# 3. Check quality control logs
docker-compose logs -f quality-control

# 4. Temporarily disable quality control for testing
# Set ENABLE_QUALITY_CONTROL=false in .env and restart
```

### **7. Organic Conversation Issues**

**Symptoms**: No organic conversations triggering, conversation loops

**Solutions**:
```bash
# 1. Check orchestrator status
curl http://localhost:6008/health
curl http://localhost:6008/organic_conversation_status

# 2. Test conversation starter generation
curl -X POST http://localhost:6008/test-starter \
  -H "Content-Type: application/json" \
  -d '{"character": "peter"}'

# 3. Manually trigger organic conversation
curl -X POST http://localhost:6008/trigger-organic

# 4. Adjust organic conversation settings in .env
MIN_TIME_BETWEEN_ORGANIC_CONVERSATIONS=5     # minutes
CONVERSATION_SILENCE_THRESHOLD_MINUTES=15    # minutes  
ORGANIC_CONVERSATION_PROBABILITY=0.4         # 40% chance

# 5. Check orchestrator logs
docker-compose logs -f orchestrator
```

---

## 🔍 **Advanced Diagnostics**

### **Service Communication Issues**

```bash
# Test inter-service communication
docker-compose exec message-router curl http://llm-service:6001/health
docker-compose exec orchestrator curl http://message-router:6005/health
docker-compose exec rag-retriever curl http://keydb:6379

# Check Docker network
docker network ls
docker network inspect discord-pg-bot_bot_network
```

### **Memory and Performance Issues**

```bash
# Monitor resource usage
docker stats

# Check individual service memory usage
docker-compose exec llm-service ps aux
docker-compose exec message-router ps aux

# Monitor KeyDB memory usage
docker-compose exec keydb keydb-cli INFO memory
```

### **Log Analysis**

```bash
# View all service logs
docker-compose logs --tail=100

# Focus on specific patterns
docker-compose logs | grep -i error
docker-compose logs | grep -i "failed"
docker-compose logs | grep -i "connection"

# Real-time log monitoring
docker-compose logs -f | grep -E "(ERROR|WARN|Failed)"
```

---

## 🔧 **Environment Configuration Issues**

### **Missing Environment Variables**

Create or verify your `.env` file has all required variables:

```bash
# Essential Discord tokens
DISCORD_BOT_TOKEN_PETER=bot_token_here
DISCORD_BOT_TOKEN_BRIAN=bot_token_here
DISCORD_BOT_TOKEN_STEWIE=bot_token_here
DEFAULT_DISCORD_CHANNEL_ID=your_channel_id

# LLM configuration  
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=mistral-nemo

# KeyDB caching
REDIS_URL=redis://keydb:6379
LLM_RESPONSE_CACHE_TTL=3600
CHARACTER_CONFIG_CACHE_TTL=86400

# Quality control
COLD_START_THRESHOLD=30.0
WARM_CONVERSATION_THRESHOLD=60.0
HOT_CONVERSATION_THRESHOLD=75.0

# Organic conversations
MIN_TIME_BETWEEN_ORGANIC_CONVERSATIONS=5
CONVERSATION_SILENCE_THRESHOLD_MINUTES=15
ORGANIC_CONVERSATION_PROBABILITY=0.4
```

---

## 🚀 **Performance Optimization**

### **Ollama Performance**
```bash
# For RTX GPUs, ensure GPU utilization
nvidia-smi  # Check GPU usage during conversations

# Optimize Ollama settings
export OLLAMA_NUM_PARALLEL=2
export OLLAMA_MAX_LOADED_MODELS=1
```

### **KeyDB Optimization**
```bash
# Monitor cache hit rates
docker-compose exec keydb keydb-cli INFO stats

# Adjust memory limits if needed (in docker-compose.yml)
command: >
  keydb-server 
  --appendonly yes 
  --maxmemory 4gb 
  --maxmemory-policy allkeys-lru
```

---

## 📞 **Getting Help**

If you're still having issues:

1. **Check the logs**: `docker-compose logs -f`
2. **Verify prerequisites**: Ensure Docker, Ollama, and mistral-nemo are working
3. **Check Discord bot permissions**: Ensure bots have proper permissions in your server
4. **Verify tokens**: Make sure Discord bot tokens are correct in `.env`
5. **Check network**: Ensure no firewall is blocking the ports

## Useful Monitoring Commands

```bash
# Watch logs in real-time
docker-compose logs -f

# Monitor specific service
docker-compose logs -f orchestrator

# Check resource usage
docker stats

# See running containers
docker ps

# Check Docker networks
docker network ls
```

---

## 🔄 **Complete System Reset**

If all else fails, perform a complete reset:

```bash
# Stop all services
docker-compose down

# Remove containers and volumes  
docker-compose down -v

# Remove images (optional)
docker-compose down --rmi all

# Rebuild everything
docker-compose up --build -d

# Wait for health checks
sleep 60
docker-compose ps
```

**Note**: This will clear all cached data and conversation history.

## Health Check Commands

### Check All Services
```bash
# Quick health check
curl http://localhost:5003/health
curl http://localhost:5004/health  
curl http://localhost:5005/health
curl http://localhost:5006/health
curl http://localhost:5007/health
curl http://localhost:5008/health

# Detailed status
curl http://localhost:5003/fine_tuning_stats
```

### Test RAG System
```bash
# Test RAG retrieval
curl -X POST http://localhost:5005/retrieve \
  -H "Content-Type: application/json" \
  -d '{"query": "Peter Griffin chicken fight", "num_results": 3}'

# Check vector store status
curl http://localhost:5005/health
```

### Test Orchestrator
```bash
# Test orchestration
curl -X POST http://localhost:5003/orchestrate \
  -H "Content-Type: application/json" \
  -d '{
    "user_query": "Hello Peter!",
    "channel_id": "your_channel_id",
    "user_id": "test_user",
    "user_display_name": "Test User"
  }'
```

## Performance Optimization

### If Services Are Slow
```bash
# 1. Check system resources
docker stats

# 2. Increase memory limits in docker-compose.yml
# Add under each service:
# deploy:
#   resources:
#     limits:
#       memory: 2G

# 3. Restart with new limits
cd docker
docker-compose down
docker-compose up -d
```

### If RAG Queries Are Slow
```bash
# 1. Check ChromaDB size
du -sh chroma_db/

# 2. If too large, reduce crawl scope in .env:
# FANDOM_WIKI_MAX_PAGES=50

# 3. Clear and re-crawl
rm -rf chroma_db/*
curl -X POST http://localhost:5003/crawl/trigger
```

## Complete Reset

If all else fails, here's how to completely reset the system:

```bash
# 1. Stop everything
cd docker
docker-compose down -v

# 2. Remove all data
docker volume prune -f
rm -rf ../chroma_db/*

# 3. Rebuild and restart
docker-compose build --no-cache
docker-compose up -d

# 4. Wait for services to start
sleep 30

# 5. Trigger initial crawl
curl -X POST http://localhost:5003/crawl/trigger

# 6. Check health
curl http://localhost:5003/health
```

## Getting Help

If you're still having issues:

1. **Check the logs**: `docker-compose logs -f`
2. **Verify prerequisites**: Ensure Docker, Ollama, and mistral-nemo are working
3. **Check Discord bot permissions**: Ensure bots have proper permissions in your server
4. **Verify tokens**: Make sure Discord bot tokens are correct in `.env`
5. **Check network**: Ensure no firewall is blocking the ports

## Useful Monitoring Commands

```bash
# Watch logs in real-time
cd docker
docker-compose logs -f

# Monitor specific service
docker-compose logs -f orchestrator

# Check resource usage
docker stats

# See running containers
docker ps

# Check Docker networks
docker network ls
``` 