# 🏗️ Microservices Architecture Refactor Plan

## 📋 Current Architecture Issues

### **Orchestrator Monolith Problems:**
- **5,350 lines** of mixed responsibilities
- **Single point of failure** for all LLM operations
- **Poor separation of concerns** - quality control, fine-tuning, conversation coordination all mixed
- **Inconsistent caching** - each service implements its own cache logic
- **Difficult to scale** - can't scale individual components independently

## 🎯 **Proposed Microservices Architecture**

### **Core Principle: Single LLM Instance with Distributed Services**
- **LLM Service**: Single Ollama instance shared by all services
- **Fail-fast approach**: No fallbacks, clean error handling
- **Optimal caching**: Centralized cache strategy with service-specific patterns
- **Production-ready**: All services use Gunicorn with proper health checks

---

## 🔧 **Microservices Breakdown**

### **1. LLM Service** (`llm-service`)
**Responsibility**: Single source of truth for all LLM operations
- **Port**: 5001
- **Purpose**: Centralized LLM access point for all services
- **Features**:
  - Single Ollama instance management
  - Request queuing and rate limiting
  - LLM health monitoring
  - Response caching for identical prompts
- **Dependencies**: None (base service)
- **Cache Strategy**: Response caching with prompt hashing

### **2. Character Config Service** (`character-config`) ✅ **EXISTING**
**Responsibility**: Character prompt and configuration management
- **Port**: 5006
- **Status**: Already implemented and working
- **Features**: Character prompts, LLM settings, caching

### **3. Conversation Coordinator Service** (`conversation-coordinator`)
**Responsibility**: Intelligent conversation flow management
- **Port**: 5002
- **Purpose**: Decide who speaks next, manage conversation flow
- **Features**:
  - Speaker selection logic
  - Conversation state tracking
  - Turn management
  - Organic conversation initiation
- **Dependencies**: LLM Service, Character Config Service
- **Cache Strategy**: Conversation state caching

### **4. Quality Control Service** (`quality-control`)
**Responsibility**: Response quality assessment and filtering
- **Port**: 5003
- **Purpose**: Ensure high-quality responses before sending
- **Features**:
  - Response quality assessment
  - Adaptive quality thresholds
  - Retry logic for poor responses
  - Quality metrics tracking
- **Dependencies**: LLM Service
- **Cache Strategy**: Quality assessment caching

### **5. Fine-Tuning Service** (`fine-tuning`)
**Responsibility**: Prompt optimization and A/B testing
- **Port**: 5004
- **Purpose**: Continuously improve character prompts
- **Features**:
  - Response rating collection
  - Prompt optimization
  - A/B testing management
  - Performance analytics
- **Dependencies**: MongoDB, Character Config Service
- **Cache Strategy**: Performance metrics caching

### **6. Message Router Service** (`message-router`)
**Responsibility**: Central message routing and orchestration
- **Port**: 5005
- **Purpose**: Route messages between services and coordinate responses
- **Features**:
  - Request routing
  - Service discovery
  - Load balancing
  - Dead letter queue management
- **Dependencies**: All other services
- **Cache Strategy**: Routing table caching

### **7. RAG Retriever Service** (`rag-retriever`) ✅ **EXISTING**
**Responsibility**: Context retrieval from vector database
- **Port**: 5007
- **Status**: Already implemented
- **Features**: Vector search, context retrieval

### **8. RAG Crawler Service** (`rag-crawler`) ✅ **EXISTING**
**Responsibility**: Content crawling and indexing
- **Port**: 5009
- **Status**: Already implemented

### **9. Discord Handler Services** ✅ **EXISTING**
**Responsibility**: Discord bot interactions per character
- **Ports**: 5011 (Peter), 5012 (Brian), 5013 (Stewie)
- **Status**: Already implemented

---

## 📊 **Service Communication Flow**

```
Discord Message → Discord Handler → Message Router → Conversation Coordinator
                                                   ↓
Character Config ← LLM Service ← Quality Control ← Response Generation
                                                   ↓
Fine-Tuning Service ← Response Rating ← Discord Handler ← Final Response
```

---

## 🗂️ **Requirements.txt Strategy**

### **Base Requirements** (`requirements-base.txt`)
```
flask==2.3.3
gunicorn==21.2.0
python-dotenv==1.0.0
requests==2.31.0
redis==4.6.0
```

### **LLM Service** (`requirements-llm.txt`)
```
-r requirements-base.txt
langchain==0.0.350
langchain-community==0.0.38
ollama==0.1.7
```

### **Character Config** (`requirements-character-config.txt`)
```
-r requirements-base.txt
# Minimal dependencies - just config management
```

### **Conversation Coordinator** (`requirements-conversation-coordinator.txt`)
```
-r requirements-base.txt
langchain==0.0.350
# For conversation analysis
```

### **Quality Control** (`requirements-quality-control.txt`)
```
-r requirements-base.txt
langchain==0.0.350
# For quality assessment
```

### **Fine-Tuning** (`requirements-fine-tuning.txt`)
```
-r requirements-base.txt
pymongo==4.6.0
langchain==0.0.350
numpy==1.24.3
# For analytics and optimization
```

### **Message Router** (`requirements-message-router.txt`)
```
-r requirements-base.txt
# Minimal - just routing logic
```

---

## 🐳 **Docker Strategy**

### **Base Dockerfile Template**
```dockerfile
FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements-{service}.txt .
RUN pip install --no-cache-dir -r requirements-{service}.txt

# Copy service code
COPY src/app/{service}/ ./src/app/{service}/
COPY src/app/utils/ ./src/app/utils/

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:{port}/health || exit 1

# Run with Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:{port}", "--workers", "2", "--timeout", "120", "src.app.{service}.server:app"]
```

---

## 💾 **Optimal Caching Architecture**

### **Cache Layers**
1. **L1 Cache**: Service-local in-memory cache (Redis client-side)
2. **L2 Cache**: Shared KeyDB instance for cross-service data
3. **L3 Cache**: MongoDB for persistent data

### **Cache Patterns by Service**

#### **LLM Service Caching**
```python
# Cache identical prompts to avoid redundant LLM calls
cache_key = f"llm:prompt:{hash(prompt)}"
ttl = 3600  # 1 hour
```

#### **Character Config Caching**
```python
# Cache character configurations
cache_key = f"character:{character_name}:config"
ttl = 86400  # 24 hours (rarely changes)
```

#### **Conversation Coordinator Caching**
```python
# Cache conversation state
cache_key = f"conversation:{channel_id}:state"
ttl = 1800  # 30 minutes
```

#### **Quality Control Caching**
```python
# Cache quality assessments for identical responses
cache_key = f"quality:{hash(response)}:{character_name}"
ttl = 7200  # 2 hours
```

#### **Fine-Tuning Caching**
```python
# Cache performance metrics
cache_key = f"metrics:{character_name}:{date}"
ttl = 86400  # 24 hours
```

---

## 🚀 **Implementation Plan**

### **Phase 1: Extract Core Services**
1. **Create LLM Service** - Extract LLM logic from orchestrator
2. **Create Conversation Coordinator** - Extract conversation logic
3. **Create Quality Control Service** - Extract quality logic
4. **Create Message Router** - Central routing service

### **Phase 2: Extract Supporting Services**
1. **Create Fine-Tuning Service** - Extract fine-tuning logic
2. **Update existing services** - Optimize for new architecture
3. **Implement optimal caching** - Centralized cache strategy

### **Phase 3: Production Optimization**
1. **Performance testing** - Load testing each service
2. **Monitoring setup** - Health checks and metrics
3. **Documentation** - API documentation for each service

---

## 📈 **Benefits of New Architecture**

### **Scalability**
- **Independent scaling** - Scale services based on load
- **Resource optimization** - Right-size each service
- **Fault isolation** - Service failures don't cascade

### **Maintainability**
- **Single responsibility** - Each service has one job
- **Clear boundaries** - Well-defined service interfaces
- **Easier testing** - Test services independently

### **Performance**
- **Optimal caching** - Service-specific cache strategies
- **Reduced latency** - Eliminate unnecessary service hops
- **Better resource usage** - Single LLM instance shared efficiently

### **Reliability**
- **Fail-fast design** - Clean error handling
- **Health monitoring** - Per-service health checks
- **Dead letter queues** - Handle failed requests gracefully

---

## 🔧 **Service Dependencies**

```
LLM Service (base)
├── Character Config Service
├── Conversation Coordinator Service
├── Quality Control Service
└── Fine-Tuning Service

Message Router Service
├── All above services
└── Discord Handler Services

RAG Services (independent)
├── RAG Retriever
└── RAG Crawler

Infrastructure
├── KeyDB (caching)
├── MongoDB (persistence)
└── Ollama (LLM runtime)
```

---

## 🎯 **Success Metrics**

### **Performance Targets**
- **Response time**: < 2s for 95% of requests
- **Availability**: 99.9% uptime per service
- **Cache hit rate**: > 80% for frequently accessed data
- **Resource usage**: < 50% CPU/memory per service

### **Quality Targets**
- **Response quality**: > 85% average rating
- **Error rate**: < 1% failed requests
- **Service isolation**: No cascading failures

---

**Next Steps**: Begin implementation with Phase 1 services, starting with LLM Service extraction. 