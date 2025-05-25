# RAG Microservice Migration Guide

## Overview

This document outlines the migration from a monolithic RAG (Retrieval Augmented Generation) implementation within the Orchestrator service to a dedicated RAG microservice architecture. This change improves separation of concerns, enables independent scaling, and provides a cleaner, more maintainable system.

## Migration Summary

### Before: Monolithic RAG
- RAG functionality was embedded within the Orchestrator service
- ChromaDB was directly managed by the Orchestrator
- Vector operations and LLM orchestration were tightly coupled
- Scaling RAG operations required scaling the entire Orchestrator

### After: RAG Microservice
- RAG functionality is isolated in a dedicated `rag-retriever` service
- ChromaDB is managed exclusively by the RAG service
- Vector operations are accessed via HTTP API
- RAG service can be scaled independently

## Architectural Changes

### New Service: RAG Retriever (`rag-retriever`)

**Port**: 5005  
**Technology**: Python, Flask, LangChain, SentenceTransformers, ChromaDB  
**Responsibilities**:
- Vector database management
- Wiki crawling and content processing
- Embedding generation and storage
- Context retrieval via HTTP API

**Key Endpoints**:
- `POST /retrieve` - Main context retrieval endpoint
- `GET /health` - Health check and service status
- `POST /load_fandom_wiki` - Trigger wiki crawling
- `GET /vector_store_status` - Vector database status

### Modified Service: Orchestrator

**Changes**:
- Removed direct ChromaDB dependencies
- Removed embedding model loading
- Added HTTP client for RAG service communication
- Updated `retrieve_context()` function to use HTTP API
- Modified health checks to show RAG service status

**New Configuration**:
- `RAG_RETRIEVER_API_URL`: URL for RAG service (default: `http://rag-retriever:5005`)
- Removed `CHROMA_DB_PATH` (now managed by RAG service)

### Updated Port Assignments

| Service | Old Port | New Port | Notes |
|---------|----------|----------|-------|
| RAG Retriever | N/A | 5005 | New service |
| Peter Bot | 5005 | 5006 | Port shifted |
| Brian Bot | 5006 | 5007 | Port shifted |
| Stewie Bot | 5007 | 5008 | Port shifted |

## Code Changes

### 1. Orchestrator Service Changes

#### Before (Monolithic):
```python
# Direct ChromaDB usage
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import SentenceTransformerEmbeddings

def retrieve_context(query, num_results=3):
    embeddings = get_embeddings_model()
    vector_store = initialize_vector_store()
    results = vector_store.similarity_search(query, k=num_results)
    return results
```

#### After (Microservice):
```python
# HTTP API usage
import requests

def retrieve_context(query, num_results=3):
    rag_url = os.getenv("RAG_RETRIEVER_API_URL", "http://rag-retriever:5005")
    payload = {
        "query": query,
        "num_results": num_results,
        "min_relevance_score": 0.7
    }
    response = requests.post(f"{rag_url}/retrieve", json=payload)
    if response.status_code == 200:
        return response.json()["results"]
    return []
```

### 2. Docker Compose Changes

#### New Service Definition:
```yaml
rag-retriever:
  build:
    context: ..
    dockerfile: docker/Dockerfile.rag_retriever
  container_name: rag-retriever
  ports:
    - "5005:5005"
  environment:
    - RAG_RETRIEVER_PORT=5005
    - CHROMA_DB_PATH=/app/chroma_db
    - EMBEDDINGS_MODEL=all-MiniLM-L6-v2
  volumes:
    - chroma_db_data:/app/chroma_db
  networks:
    - bot_network
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:5005/health"]
    interval: 30s
    timeout: 10s
    retries: 3
```

#### Updated Orchestrator:
```yaml
orchestrator:
  # ... existing configuration ...
  environment:
    - RAG_RETRIEVER_API_URL=http://rag-retriever:5005
    # Removed CHROMA_DB_PATH
  depends_on:
    - rag-retriever  # New dependency
  # Removed chroma_db volume mount
```

## API Changes

### New RAG Service API

#### Context Retrieval
```http
POST /retrieve
Content-Type: application/json

{
  "query": "chicken fight construction site",
  "num_results": 3,
  "min_relevance_score": 0.7
}
```

**Response**:
```json
{
  "success": true,
  "results": [
    {
      "content": "In the episode 'Da Boom', Peter Griffin engages in a prolonged fight...",
      "source": "familyguy.fandom.com/wiki/Da_Boom",
      "relevance_score": 0.89
    }
  ],
  "query_processed": "chicken fight construction site",
  "total_results": 1
}
```

#### Health Check
```http
GET /health
```

**Response**:
```json
{
  "status": "healthy",
  "service": "RAG_Retriever_Service",
  "timestamp": "2024-01-15T10:30:00Z",
  "vector_store_status": "ready",
  "embeddings_model": "all-MiniLM-L6-v2"
}
```

### Modified Orchestrator API

The orchestrator's public API remains unchanged, but internally it now communicates with the RAG service instead of directly managing ChromaDB.

## Configuration Changes

### Environment Variables

#### New RAG Service Variables:
```env
# RAG Retriever Service
RAG_RETRIEVER_PORT=5005
CHROMA_DB_PATH=/app/chroma_db
EMBEDDINGS_MODEL=all-MiniLM-L6-v2
FANDOM_WIKI_START_URL=https://familyguy.fandom.com/wiki/Main_Page
FANDOM_WIKI_MAX_PAGES=100
FANDOM_WIKI_CRAWL_DELAY=1
```

#### Updated Orchestrator Variables:
```env
# Orchestrator
RAG_RETRIEVER_API_URL=http://rag-retriever:5005
RAG_ENABLED=true
RAG_NUM_RESULTS=3
RAG_MIN_RELEVANCE_SCORE=0.7
# Removed: CHROMA_DB_PATH
```

## Migration Steps

### 1. Pre-Migration Backup
```bash
# Backup existing ChromaDB data
docker-compose exec orchestrator tar -czf /tmp/chroma_backup.tar.gz /app/chroma_db
docker cp orchestrator:/tmp/chroma_backup.tar.gz ./chroma_backup.tar.gz
```

### 2. Update Docker Compose
```bash
# Pull latest changes
git pull origin main

# Update docker-compose.yml with new service definitions
# Update port mappings for character services
```

### 3. Build New Services
```bash
# Build the new RAG retriever service
docker-compose build rag-retriever

# Rebuild orchestrator with updated dependencies
docker-compose build orchestrator
```

### 4. Deploy Updated System
```bash
# Stop existing services
docker-compose down

# Start with new architecture
docker-compose up -d

# Verify all services are healthy
docker-compose ps
```

### 5. Restore Data (if needed)
```bash
# If ChromaDB data needs to be restored
docker cp ./chroma_backup.tar.gz rag-retriever:/tmp/
docker-compose exec rag-retriever tar -xzf /tmp/chroma_backup.tar.gz -C /app/
```

### 6. Verify Migration
```bash
# Test RAG service health
curl http://localhost:5005/health

# Test context retrieval
curl -X POST http://localhost:5005/retrieve \
  -H "Content-Type: application/json" \
  -d '{"query": "Peter Griffin", "num_results": 3}'

# Test orchestrator integration
curl -X POST http://localhost:5003/orchestrate \
  -H "Content-Type: application/json" \
  -d '{
    "user_query": "Tell me about the chicken fight",
    "channel_id": "123456789",
    "initiator_bot_name": "Peter",
    "initiator_mention": "<@peter>",
    "human_user_display_name": "TestUser"
  }'
```

## Benefits of Migration

### 1. Separation of Concerns
- RAG operations isolated from LLM orchestration
- Cleaner, more focused codebases
- Easier debugging and maintenance

### 2. Independent Scaling
- Scale RAG service based on retrieval load
- Scale orchestrator based on conversation volume
- Optimize resources for specific workloads

### 3. Improved Reliability
- RAG service failures don't crash orchestrator
- Graceful degradation when RAG is unavailable
- Better fault isolation

### 4. Development Efficiency
- Teams can work on RAG and orchestrator independently
- Faster development cycles
- Easier testing of individual components

### 5. Technology Flexibility
- RAG service can use different vector databases
- Embedding models can be updated independently
- Optimization specific to vector operations

## Troubleshooting

### Common Issues

#### 1. RAG Service Not Starting
```bash
# Check logs
docker-compose logs rag-retriever

# Common causes:
# - Port conflicts (check if 5005 is in use)
# - Volume mount issues
# - Missing environment variables
```

#### 2. Orchestrator Can't Reach RAG Service
```bash
# Verify network connectivity
docker-compose exec orchestrator curl http://rag-retriever:5005/health

# Check environment variables
docker-compose exec orchestrator env | grep RAG
```

#### 3. Context Retrieval Failures
```bash
# Check RAG service status
curl http://localhost:5005/vector_store_status

# Verify ChromaDB data
docker-compose exec rag-retriever ls -la /app/chroma_db
```

### Performance Monitoring

#### Key Metrics to Monitor:
- RAG service response times
- Context retrieval success rates
- Vector database size and performance
- Memory usage of RAG service
- Network latency between services

#### Monitoring Commands:
```bash
# Service health checks
curl http://localhost:5005/health
curl http://localhost:5003/health

# Performance metrics
docker stats rag-retriever orchestrator

# Log analysis
docker-compose logs -f rag-retriever | grep "retrieve"
```

## Future Considerations

### 1. Caching Layer
- Implement Redis cache for frequent queries
- Cache embeddings for common queries
- Reduce load on vector database

### 2. Load Balancing
- Multiple RAG service instances
- Load balancer for high availability
- Geographic distribution for latency

### 3. Advanced Features
- Real-time vector updates
- Hybrid search (semantic + keyword)
- Query optimization and rewriting
- Context re-ranking

### 4. Monitoring and Observability
- Distributed tracing across services
- Metrics collection and alerting
- Performance dashboards
- Automated health checks

## Conclusion

The migration to a RAG microservice architecture provides significant benefits in terms of maintainability, scalability, and reliability. While it introduces some complexity in terms of service coordination, the benefits far outweigh the costs for a production system.

The new architecture positions the system for future growth and enables more sophisticated RAG capabilities while maintaining the existing user experience. 