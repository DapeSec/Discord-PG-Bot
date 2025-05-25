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

### Issue 1: "Vector store not initialized" Error

**Symptoms:**
- RAG Retriever service returns 503 errors
- Logs show "Vector store not initialized"

**Solution:**
```bash
# 1. Check if ChromaDB directory exists and has proper permissions
ls -la chroma_db/

# 2. If directory is missing or empty, create it
mkdir -p chroma_db
chmod 755 chroma_db

# 3. Restart RAG services
cd docker
docker-compose restart rag-retriever rag-crawler

# 4. Trigger initial crawl to populate the database
curl -X POST http://localhost:5003/crawl/trigger
```

### Issue 2: "Quality Control Assessment Failed"

**Symptoms:**
- Logs show "LLM assessment failed to parse rating"
- Quality control keeps failing

**Solution:**
This has been fixed in the updated code. If you still see issues:

```bash
# 1. Restart orchestrator service
cd docker
docker-compose restart orchestrator

# 2. Check Ollama is working
curl http://localhost:11434/api/tags

# 3. If Ollama is down, restart it
ollama serve
```

### Issue 3: Discord Handler Connection Refused

**Symptoms:**
- "Connection refused" errors between services
- Bots don't respond in Discord

**Solution:**
```bash
# 1. Check all services are running
cd docker
docker-compose ps

# 2. Restart all services in correct order
docker-compose down
docker-compose up -d mongodb
sleep 10
docker-compose up -d rag-retriever peter brian stewie
sleep 10
docker-compose up -d orchestrator
sleep 5
docker-compose up -d discord-handler
```

### Issue 4: Ollama Connection Issues

**Symptoms:**
- "Failed to connect to Ollama" errors
- LLM generation fails

**Solution:**
```bash
# 1. Check if Ollama is running
curl http://localhost:11434/api/tags

# 2. If not running, start Ollama
ollama serve

# 3. Ensure mistral-nemo model is installed
ollama pull mistral-nemo

# 4. Test the model
ollama run mistral-nemo "Hello, test message"

# 5. Restart orchestrator
cd docker
docker-compose restart orchestrator
```

### Issue 5: Missing .env File

**Symptoms:**
- Services fail to start
- "Environment variable not found" errors

**Solution:**
```bash
# 1. Run the setup script
python setup_discord_bot.py

# OR create .env manually with required variables:
# DISCORD_BOT_TOKEN_PETER=your_token_here
# DISCORD_BOT_TOKEN_BRIAN=your_token_here  
# DISCORD_BOT_TOKEN_STEWIE=your_token_here
# DEFAULT_DISCORD_CHANNEL_ID=your_channel_id
# OLLAMA_BASE_URL=http://host.docker.internal:11434
# OLLAMA_MODEL=mistral-nemo
```

### Issue 6: MongoDB Connection Issues

**Symptoms:**
- "Failed to connect to MongoDB" errors
- Conversation history not saving

**Solution:**
```bash
# 1. Check MongoDB container
cd docker
docker-compose logs mongodb

# 2. Restart MongoDB
docker-compose restart mongodb

# 3. Wait for MongoDB to fully start, then restart other services
sleep 15
docker-compose restart orchestrator rag-retriever rag-crawler
```

### Issue 7: Port Conflicts

**Symptoms:**
- "Port already in use" errors
- Services fail to start

**Solution:**
```bash
# 1. Check what's using the ports
netstat -tulpn | grep :5003
netstat -tulpn | grep :5004
netstat -tulpn | grep :5005

# 2. Stop conflicting services or change ports in docker-compose.yml

# 3. Restart with new ports
cd docker
docker-compose down
docker-compose up -d
```

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