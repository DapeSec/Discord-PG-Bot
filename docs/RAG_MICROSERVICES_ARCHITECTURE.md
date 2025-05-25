# RAG Microservices Architecture

## Overview

The RAG (Retrieval Augmented Generation) system has been architected as **two separate microservices** to optimize for different operational patterns, resource requirements, and scaling needs. This separation follows microservices best practices and provides significant operational benefits.

## Architecture Diagram

```mermaid
graph TD
    USER[Discord User] -->|Query| ORCH[Orchestrator]
    ORCH -->|POST /retrieve| RAG_RET[RAG Retriever Service<br/>Port 5005]
    RAG_RET -->|Vector Search| CHROMA[ChromaDB<br/>Vector Store]
    CHROMA -->|Results| RAG_RET
    RAG_RET -->|Context| ORCH
    
    ADMIN[Admin/Scheduler] -->|POST /crawl/trigger| ORCH
    ORCH -->|POST /crawl/start| RAG_CRAWL[RAG Crawler Service<br/>Port 5009]
    RAG_CRAWL -->|Web Scraping| WIKI[Family Guy Wiki]
    RAG_CRAWL -->|Populate/Update| CHROMA
    RAG_CRAWL -->|Status Updates| MONGO[MongoDB]
    
    RAG_RET -.->|Health Checks| MONGO
    
    subgraph "Shared Storage"
        CHROMA
        MONGO
    end
    
    subgraph "RAG Microservices"
        RAG_RET
        RAG_CRAWL
    end
```

## Service Separation Rationale

### 🎯 **Why Separate RAG Retriever and RAG Crawler?**

| Aspect | RAG Retriever | RAG Crawler |
|--------|---------------|-------------|
| **Operational Pattern** | High-frequency, real-time | Low-frequency, batch operations |
| **Request Volume** | Every user query (~100s/day) | Weekly/monthly crawls (~1/week) |
| **Response Time** | <100ms required | Minutes/hours acceptable |
| **Resource Usage** | Low CPU, fast I/O | High CPU, memory intensive |
| **Availability** | 99.9%+ uptime critical | Downtime acceptable |
| **Scaling** | Horizontal (multiple instances) | Vertical (more powerful instances) |
| **Dependencies** | Minimal (ChromaDB, embeddings) | Heavy (web scraping, ML processing) |

## Service Details

### 🔍 **RAG Retriever Service** (`rag-retriever`)

**Purpose**: Provides fast, real-time context retrieval for user queries.

**Key Features**:
- **High-performance vector search** using ChromaDB
- **Minimal dependencies** for fast startup and low resource usage
- **Read-only operations** - never modifies the vector database
- **Horizontal scaling** capability for high query loads
- **Sub-100ms response times** for optimal user experience

**API Endpoints**:
```
GET  /health                    # Service health check
POST /retrieve                  # Retrieve context for query
GET  /vector_store_status       # Vector store information
```

**Resource Requirements**:
- **CPU**: Low (vector search is optimized)
- **Memory**: Moderate (embeddings model + vector index)
- **Storage**: Read access to ChromaDB
- **Network**: High availability required

### 🕷️ **RAG Crawler Service** (`rag-crawler`)

**Purpose**: Handles web scraping and vector database population/updates.

**Key Features**:
- **Comprehensive web scraping** with BeautifulSoup and requests
- **Intelligent text processing** and chunking
- **Vector embedding generation** using sentence-transformers
- **Batch processing** for efficient resource utilization
- **Progress tracking** and status reporting
- **Graceful error handling** and retry mechanisms

**API Endpoints**:
```
GET  /health                    # Service health check
POST /crawl/start               # Start new crawl operation
GET  /crawl/status              # Get crawl progress/status
POST /crawl/stop                # Stop current crawl
GET  /vector_store/info         # Vector store statistics
```

**Resource Requirements**:
- **CPU**: High (text processing, embeddings generation)
- **Memory**: High (large documents, ML models)
- **Storage**: Write access to ChromaDB
- **Network**: Moderate (web scraping)

## Operational Workflows

### 📊 **Real-time Context Retrieval**

```mermaid
sequenceDiagram
    participant User
    participant Orchestrator
    participant RAG_Retriever
    participant ChromaDB

    User->>Orchestrator: "Tell me about Peter's chicken fights"
    Orchestrator->>RAG_Retriever: POST /retrieve {"query": "chicken fights", "num_results": 3}
    RAG_Retriever->>ChromaDB: Vector similarity search
    ChromaDB-->>RAG_Retriever: Matching document chunks
    RAG_Retriever-->>Orchestrator: Formatted context results
    Orchestrator->>User: Enhanced response with context
```

### 🔄 **Periodic Content Updates**

```mermaid
sequenceDiagram
    participant Admin
    participant Orchestrator
    participant RAG_Crawler
    participant Wiki
    participant ChromaDB
    participant MongoDB

    Admin->>Orchestrator: POST /crawl/trigger
    Orchestrator->>RAG_Crawler: POST /crawl/start
    RAG_Crawler->>MongoDB: Update status: "IN_PROGRESS"
    
    loop For each page
        RAG_Crawler->>Wiki: Scrape page content
        Wiki-->>RAG_Crawler: HTML content
        RAG_Crawler->>RAG_Crawler: Process & chunk text
        RAG_Crawler->>ChromaDB: Store vector embeddings
    end
    
    RAG_Crawler->>MongoDB: Update status: "SUCCESS"
    RAG_Crawler-->>Orchestrator: Crawl completion status
    Orchestrator-->>Admin: Crawl results
```

## Configuration

### Environment Variables

#### RAG Retriever Service
```bash
# Service configuration
RAG_RETRIEVER_PORT=5005
CHROMA_DB_PATH=/app/chroma_db
EMBEDDINGS_MODEL_NAME=all-MiniLM-L6-v2

# Database connections
MONGO_URI=mongodb://admin:adminpassword@mongodb:27017/?authSource=admin
MONGO_DB_NAME=discord_bot_conversations
```

#### RAG Crawler Service
```bash
# Service configuration
RAG_CRAWLER_PORT=5009
CHROMA_DB_PATH=/app/chroma_db
EMBEDDINGS_MODEL_NAME=all-MiniLM-L6-v2

# Crawling parameters
FANDOM_WIKI_START_URL=https://familyguy.fandom.com/wiki/Main_Page
FANDOM_WIKI_MAX_PAGES=100
FANDOM_WIKI_CRAWL_DELAY=1

# Database connections
MONGO_URI=mongodb://admin:adminpassword@mongodb:27017/?authSource=admin
MONGO_DB_NAME=discord_bot_conversations
```

#### Orchestrator Service
```bash
# RAG service URLs
RAG_RETRIEVER_API_URL=http://rag-retriever:5005/retrieve
RAG_CRAWLER_API_URL=http://rag-crawler:5009
```

## Deployment Strategies

### 🚀 **Standard Deployment**

Both services run continuously:

```bash
# Start all services including RAG
docker-compose up -d

# Check service health
curl http://localhost:5005/health  # RAG Retriever
curl http://localhost:5009/health  # RAG Crawler
```

### 🎯 **On-Demand Crawler Deployment**

RAG Crawler runs only when needed:

```bash
# Start core services (without crawler)
docker-compose up -d orchestrator rag-retriever mongodb

# Start crawler only for crawling operations
docker-compose --profile crawler up -d rag-crawler

# Trigger crawl
curl -X POST http://localhost:5003/crawl/trigger

# Stop crawler after completion
docker-compose stop rag-crawler
```

### ⚡ **High-Availability Retriever**

Scale RAG Retriever for high query loads:

```yaml
# docker-compose.override.yml
services:
  rag-retriever:
    deploy:
      replicas: 3
    ports:
      - "5005-5007:5005"
```

## Management Operations

### 📋 **Monitoring**

```bash
# Check service health
curl http://localhost:5005/health
curl http://localhost:5009/health

# Get vector store statistics
curl http://localhost:5009/vector_store/info

# Monitor crawl progress
curl http://localhost:5003/crawl/status
```

### 🔄 **Crawl Management**

```bash
# Trigger new crawl with custom parameters
curl -X POST http://localhost:5003/crawl/trigger \
  -H "Content-Type: application/json" \
  -d '{
    "start_url": "https://familyguy.fandom.com/wiki/Main_Page",
    "max_pages": 200,
    "delay": 2
  }'

# Check crawl status
curl http://localhost:5003/crawl/status

# Stop running crawl
curl -X POST http://localhost:5009/crawl/stop
```

### 🛠️ **Troubleshooting**

```bash
# Check service logs
docker-compose logs -f rag-retriever
docker-compose logs -f rag-crawler

# Restart specific service
docker-compose restart rag-retriever

# Check vector store integrity
curl http://localhost:5009/vector_store/info
```

## Performance Optimization

### 🔍 **RAG Retriever Optimization**

1. **Embeddings Model Caching**:
   - Pre-load embeddings model at startup
   - Use model quantization for memory efficiency

2. **Vector Search Optimization**:
   - Tune ChromaDB collection settings
   - Implement result caching for common queries

3. **Horizontal Scaling**:
   - Deploy multiple retriever instances
   - Use load balancer for query distribution

### 🕷️ **RAG Crawler Optimization**

1. **Batch Processing**:
   - Process multiple pages in parallel
   - Use connection pooling for web requests

2. **Resource Management**:
   - Implement memory-efficient text processing
   - Use streaming for large documents

3. **Incremental Updates**:
   - Track page modification dates
   - Only re-crawl changed content

## Security Considerations

### 🔒 **Access Control**

- **RAG Retriever**: Read-only access to vector store
- **RAG Crawler**: Write access to vector store, controlled via API
- **Network Isolation**: Services communicate only via defined APIs

### 🛡️ **Data Protection**

- **Input Validation**: All API endpoints validate input parameters
- **Rate Limiting**: Prevent abuse of crawling operations
- **Error Handling**: Avoid exposing internal system details

## Migration from Monolithic RAG

### 📋 **Migration Steps**

1. **Deploy New Services**:
   ```bash
   docker-compose up -d rag-retriever rag-crawler
   ```

2. **Update Orchestrator Configuration**:
   ```bash
   # Set environment variables
   RAG_RETRIEVER_API_URL=http://rag-retriever:5005/retrieve
   RAG_CRAWLER_API_URL=http://rag-crawler:5009
   ```

3. **Migrate Existing Data**:
   - Existing ChromaDB data is automatically accessible
   - No data migration required

4. **Update API Calls**:
   - Replace direct ChromaDB calls with HTTP API calls
   - Update crawling triggers to use new endpoints

### 🔄 **Rollback Plan**

If issues arise, rollback by:

1. **Revert Orchestrator Code**: Restore direct ChromaDB access
2. **Update Environment**: Remove microservice URLs
3. **Restart Services**: `docker-compose restart orchestrator`

## Benefits Achieved

### ✅ **Operational Benefits**

- **Independent Scaling**: Scale retriever and crawler separately
- **Resource Optimization**: Right-size resources for each workload
- **Fault Isolation**: Crawler issues don't affect retrieval
- **Deployment Flexibility**: Deploy services independently

### ✅ **Development Benefits**

- **Clear Separation**: Distinct codebases for different concerns
- **Independent Testing**: Test services in isolation
- **Technology Flexibility**: Use optimal tech stack per service
- **Team Ownership**: Different teams can own different services

### ✅ **Performance Benefits**

- **Optimized Response Times**: Retriever optimized for speed
- **Efficient Resource Usage**: Crawler runs only when needed
- **Better Caching**: Service-specific caching strategies
- **Reduced Contention**: No resource competition between services

## Future Enhancements

### 🚀 **Planned Improvements**

1. **Advanced Caching**:
   - Redis cache for frequent queries
   - Intelligent cache invalidation

2. **Enhanced Monitoring**:
   - Prometheus metrics
   - Grafana dashboards
   - Alert management

3. **Auto-scaling**:
   - Kubernetes deployment
   - Horizontal pod autoscaling
   - Resource-based scaling

4. **Content Intelligence**:
   - Smart crawl scheduling
   - Content change detection
   - Relevance scoring

This microservices architecture provides a robust, scalable foundation for the RAG system while maintaining operational simplicity and development efficiency. 