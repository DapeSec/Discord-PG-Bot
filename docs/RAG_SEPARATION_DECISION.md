# RAG Microservices Separation Decision

## Executive Summary

**Decision**: Separate the RAG (Retrieval Augmented Generation) system into two distinct microservices:
1. **RAG Retriever Service** (Port 5005) - Real-time context retrieval
2. **RAG Crawler Service** (Port 5009) - Web scraping and vector database population

**Status**: ✅ **IMPLEMENTED** - Both services are now operational with full API integration

## Problem Statement

The original RAG system combined two fundamentally different operational patterns in a single service:

1. **High-frequency retrieval operations** (every user query)
2. **Low-frequency crawling operations** (weekly/monthly batch jobs)

This created several issues:
- Resource contention between real-time and batch operations
- Difficulty in scaling for different workload patterns
- Complex deployment scenarios
- Monolithic dependencies affecting both operations

## Decision Rationale

### 📊 **Operational Pattern Analysis**

| Metric | RAG Retriever | RAG Crawler |
|--------|---------------|-------------|
| **Request Frequency** | ~100-1000/day | ~1-4/month |
| **Response Time SLA** | <100ms | Hours acceptable |
| **Resource Pattern** | Consistent, low | Bursty, high |
| **Availability Requirement** | 99.9%+ | Downtime OK |
| **Scaling Strategy** | Horizontal | Vertical |

### 🎯 **Benefits of Separation**

#### **Operational Benefits**
- **Independent Scaling**: Scale retriever for query load, crawler for processing speed
- **Resource Optimization**: Right-size containers for specific workloads
- **Fault Isolation**: Crawler issues don't affect real-time retrieval
- **Deployment Flexibility**: Deploy services independently based on needs

#### **Development Benefits**
- **Clear Separation of Concerns**: Distinct codebases for different responsibilities
- **Independent Testing**: Test services in isolation
- **Technology Flexibility**: Optimize tech stack per service
- **Team Ownership**: Different teams can own different services

#### **Performance Benefits**
- **Optimized Response Times**: Retriever optimized for speed
- **Efficient Resource Usage**: Crawler runs only when needed
- **Better Caching**: Service-specific caching strategies
- **Reduced Contention**: No resource competition

## Implementation Details

### 🏗️ **Architecture Changes**

#### **Before: Monolithic RAG**
```
Orchestrator → RAG Service (Combined)
                ├── Real-time retrieval
                ├── Web crawling
                ├── Vector processing
                └── ChromaDB management
```

#### **After: Microservices RAG**
```
Orchestrator → RAG Retriever (Port 5005) → ChromaDB (Read)
            → RAG Crawler (Port 5009) → ChromaDB (Write)
                                     → Web Scraping
```

### 🔧 **Service Specifications**

#### **RAG Retriever Service**
- **Purpose**: Fast, real-time context retrieval
- **Dependencies**: ChromaDB, SentenceTransformers (minimal)
- **Operations**: Read-only vector search
- **Scaling**: Horizontal (multiple instances)
- **Resource Profile**: Low CPU, moderate memory

#### **RAG Crawler Service**
- **Purpose**: Web scraping and vector database population
- **Dependencies**: BeautifulSoup, requests, ML models (heavy)
- **Operations**: Write operations, batch processing
- **Scaling**: Vertical (more powerful instances)
- **Resource Profile**: High CPU, high memory

### 📡 **API Design**

#### **RAG Retriever Endpoints**
```
GET  /health                    # Service health check
POST /retrieve                  # Retrieve context for query
GET  /vector_store_status       # Vector store information
```

#### **RAG Crawler Endpoints**
```
GET  /health                    # Service health check
POST /crawl/start               # Start new crawl operation
GET  /crawl/status              # Get crawl progress/status
POST /crawl/stop                # Stop current crawl
GET  /vector_store/info         # Vector store statistics
```

#### **Orchestrator Integration**
```
POST /crawl/trigger             # Trigger crawl via crawler service
GET  /crawl/status              # Get crawl status via crawler service
```

## Implementation Timeline

### ✅ **Phase 1: Service Creation** (Completed)
- [x] Created RAG Retriever Service with Flask API
- [x] Created RAG Crawler Service with Flask API
- [x] Implemented health checks and monitoring endpoints
- [x] Created service-specific Dockerfiles

### ✅ **Phase 2: Integration** (Completed)
- [x] Updated Orchestrator to use HTTP APIs instead of direct ChromaDB
- [x] Added crawler trigger endpoints to Orchestrator
- [x] Updated docker-compose.yml with new services
- [x] Configured environment variables and networking

### ✅ **Phase 3: Documentation** (Completed)
- [x] Created comprehensive architecture documentation
- [x] Updated README with new service breakdown
- [x] Created deployment and management guides
- [x] Documented API endpoints and workflows

## Deployment Strategies

### 🚀 **Standard Deployment**
Both services run continuously for full functionality:
```bash
docker-compose up -d
```

### 🎯 **On-Demand Crawler**
Crawler runs only when needed (resource-efficient):
```bash
# Start core services
docker-compose up -d orchestrator rag-retriever mongodb

# Start crawler for crawling operations
docker-compose --profile crawler up -d rag-crawler
```

### ⚡ **High-Availability Retriever**
Scale retriever for high query loads:
```yaml
services:
  rag-retriever:
    deploy:
      replicas: 3
```

## Performance Impact

### 📈 **Expected Improvements**

1. **Response Time**: 10-20% improvement in retrieval speed
2. **Resource Efficiency**: 30-50% reduction in idle resource usage
3. **Scalability**: Independent scaling based on actual load patterns
4. **Reliability**: Improved fault isolation and recovery

### 📊 **Monitoring Metrics**

- **Retriever**: Query response time, throughput, cache hit rate
- **Crawler**: Pages processed/hour, vector generation rate, error rate
- **Overall**: Service availability, resource utilization, cost efficiency

## Risk Assessment

### ⚠️ **Potential Risks**

1. **Increased Complexity**: More services to manage and monitor
2. **Network Latency**: HTTP calls instead of direct function calls
3. **Service Dependencies**: Failure modes between services

### 🛡️ **Mitigation Strategies**

1. **Comprehensive Monitoring**: Health checks and alerting for all services
2. **Graceful Degradation**: Fallback mechanisms for service failures
3. **Documentation**: Clear operational procedures and troubleshooting guides

## Success Criteria

### ✅ **Achieved Goals**

- [x] **Separation of Concerns**: Clear boundaries between retrieval and crawling
- [x] **Independent Scaling**: Services can scale based on their specific needs
- [x] **Resource Optimization**: Right-sized containers for each workload
- [x] **Operational Flexibility**: Different deployment strategies available
- [x] **Maintainability**: Cleaner codebase with focused responsibilities

### 📋 **Future Enhancements**

1. **Advanced Caching**: Redis cache for frequent queries
2. **Auto-scaling**: Kubernetes-based horizontal pod autoscaling
3. **Enhanced Monitoring**: Prometheus metrics and Grafana dashboards
4. **Content Intelligence**: Smart crawl scheduling and change detection

## Conclusion

The separation of RAG into specialized microservices represents a significant architectural improvement that:

- **Aligns with microservices best practices**
- **Optimizes resource utilization**
- **Improves system reliability and maintainability**
- **Provides operational flexibility**
- **Enables independent scaling and deployment**

This decision positions the system for better performance, easier maintenance, and future growth while maintaining the existing functionality and user experience.

**Recommendation**: ✅ **Proceed with separated RAG microservices architecture**

The benefits significantly outweigh the complexity costs, and the implementation provides a solid foundation for future enhancements and scaling requirements. 