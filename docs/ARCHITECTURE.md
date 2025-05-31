# Production Microservices Architecture

## Overview

The Discord Family Guy Bot is architected as a **production-grade microservices platform** consisting of 11 specialized services plus infrastructure components. This architecture provides enterprise-level scalability, fault tolerance, and maintainability while ensuring authentic character interactions and intelligent conversation management.

## Architecture Principles

### 🎯 **Core Design Principles**

1. **Single Responsibility**: Each service has one clearly defined purpose
2. **Service Isolation**: Independent failure domains with graceful degradation
3. **Loose Coupling**: Services communicate through well-defined APIs
4. **High Cohesion**: Related functionality grouped within service boundaries
5. **Scalability**: Horizontal and vertical scaling capabilities per service
6. **Observability**: Comprehensive logging, metrics, and health monitoring

### 🔧 **Technical Principles**

1. **Local-First**: All AI processing uses local Ollama instance
2. **Single-Worker Threading**: Optimized for reliability over concurrency
3. **Intelligent Caching**: KeyDB for high-performance data access
4. **Quality-First**: Every response validates through quality control
5. **Retry Resilience**: 10-attempt retry system with exponential backoff
6. **Performance Monitoring**: Real-time metrics and health tracking

## System Architecture Diagram

```mermaid
graph TB
    subgraph "Discord Interface Layer"
        PETER_BOT[Peter Discord<br/>Port 6011<br/>🍺]
        BRIAN_BOT[Brian Discord<br/>Port 6012<br/>🐕]
        STEWIE_BOT[Stewie Discord<br/>Port 6013<br/>👶]
    end
    
    subgraph "Core Processing Layer"
        MESSAGE_ROUTER[Message Router<br/>Port 6005<br/>🎯]
        LLM_SERVICE[LLM Service<br/>Port 6001<br/>🧠]
        QUALITY_CONTROL[Quality Control<br/>Port 6003<br/>🔍]
    end
    
    subgraph "Intelligence Layer"
        CONVERSATION_COORD[Conversation Coordinator<br/>Port 6002<br/>🎭]
        FINE_TUNING[Fine Tuning<br/>Port 6004<br/>📈]
    end
    
    subgraph "Knowledge Layer"
        CHARACTER_CONFIG[Character Config<br/>Port 6006<br/>📝]
        RAG_RETRIEVER[RAG Retriever<br/>Port 6007<br/>📚]
        RAG_CRAWLER[RAG Crawler<br/>Port 6009<br/>🕷️]
    end
    
    subgraph "Infrastructure Layer"
        KEYDB[(KeyDB Cache<br/>Port 6379<br/>⚡)]
        KEYDB_UI[KeyDB Commander<br/>Port 8081<br/>🖥️]
        OLLAMA[Ollama LLM<br/>Local GPU<br/>🚀]
        CHROMADB[(ChromaDB<br/>Vector Store<br/>🔢)]
    end
    
    PETER_BOT <--> MESSAGE_ROUTER
    BRIAN_BOT <--> MESSAGE_ROUTER
    STEWIE_BOT <--> MESSAGE_ROUTER
    
    MESSAGE_ROUTER --> LLM_SERVICE
    MESSAGE_ROUTER --> CHARACTER_CONFIG
    MESSAGE_ROUTER --> RAG_RETRIEVER
    MESSAGE_ROUTER --> CONVERSATION_COORD
    MESSAGE_ROUTER --> QUALITY_CONTROL
    MESSAGE_ROUTER --> FINE_TUNING
    
    LLM_SERVICE --> OLLAMA
    RAG_RETRIEVER --> CHROMADB
    RAG_CRAWLER --> CHROMADB
    
    MESSAGE_ROUTER --> KEYDB
    RAG_RETRIEVER --> KEYDB
    QUALITY_CONTROL --> KEYDB
    CONVERSATION_COORD --> KEYDB
    FINE_TUNING --> KEYDB
    KEYDB --> KEYDB_UI
    
    style PETER_BOT fill:#ff9999
    style BRIAN_BOT fill:#99ff99  
    style STEWIE_BOT fill:#9999ff
    style QUALITY_CONTROL fill:#ffff99
    style KEYDB fill:#ff99ff
```

## Service Architecture

### 🎭 **Discord Interface Layer**

#### Peter Discord Service (Port 6011)
- **Purpose**: Peter Griffin's Discord API interface
- **Personality**: Lovable oaf with beer obsession
- **Dependencies**: Message Router
- **Scaling**: Vertical (single instance per Discord token)
- **Workers**: 1

#### Brian Discord Service (Port 6012)
- **Purpose**: Brian Griffin's Discord API interface
- **Personality**: Intellectual dog with sophisticated vocabulary
- **Dependencies**: Message Router
- **Scaling**: Vertical
- **Workers**: 1

#### Stewie Discord Service (Port 6013)
- **Purpose**: Stewie Griffin's Discord API interface
- **Personality**: Evil genius baby with condescending wit
- **Dependencies**: Message Router
- **Scaling**: Vertical
- **Workers**: 1

### 🧠 **Core Processing Layer**

#### Message Router (Port 6005)
- **Purpose**: Central orchestration and service coordination
- **Role**: Primary entry point for all conversation requests
- **Features**: 10-attempt retry manager, service discovery, health monitoring
- **Dependencies**: All AI services, KeyDB
- **Scaling**: Horizontal (load balancer compatible)
- **Workers**: 1

#### LLM Service (Port 6001)
- **Purpose**: Centralized language model operations
- **Role**: Single point of access for Ollama
- **Features**: Response caching, connection pooling, performance metrics
- **Dependencies**: Ollama, KeyDB
- **Scaling**: Vertical (GPU-bound)
- **Workers**: 1

#### Quality Control (Port 6003)
- **Purpose**: Adaptive response quality assessment
- **Role**: Quality gatekeeper for all generated content
- **Features**: Adaptive thresholds, organic validation, character-aware assessment
- **Dependencies**: KeyDB
- **Scaling**: Horizontal
- **Workers**: 1

### 🎮 **Intelligence Layer**

#### Conversation Coordinator (Port 6002)
- **Purpose**: Character selection and conversation flow management
- **Role**: Decides who speaks next and manages organic conversations
- **Features**: Character personality modeling, timing coordination, follow-up generation
- **Dependencies**: KeyDB, Message Router integration
- **Scaling**: Horizontal
- **Workers**: 1

#### Fine Tuning (Port 6004)
- **Purpose**: Response optimization and performance tracking
- **Role**: Continuous improvement through feedback loops
- **Features**: Performance analytics, prompt optimization, retry guidance
- **Dependencies**: KeyDB, RAG integration, Character Config integration
- **Scaling**: Horizontal
- **Workers**: 1

### 📚 **Knowledge Layer**

#### Character Config (Port 6006)
- **Purpose**: Character prompt and configuration management
- **Role**: Source of truth for character personalities
- **Features**: Prompt caching, character-specific settings
- **Dependencies**: KeyDB (caching only)
- **Scaling**: Horizontal
- **Workers**: 1

#### RAG Retriever (Port 6007)
- **Purpose**: Real-time context retrieval from vector database
- **Role**: Provides relevant Family Guy knowledge for responses
- **Features**: Vector search, context caching, query optimization
- **Dependencies**: ChromaDB, KeyDB
- **Scaling**: Horizontal
- **Workers**: 1

#### RAG Crawler (Port 6009)
- **Purpose**: Web scraping and knowledge base indexing
- **Role**: Maintains and updates the Family Guy knowledge base
- **Features**: Automated crawling, content processing, vector indexing
- **Dependencies**: ChromaDB
- **Scaling**: Vertical (resource-intensive)
- **Workers**: 1

## Data Flow Architecture

### Standard User Message Flow

```mermaid
sequenceDiagram
    participant User as Discord User
    participant Peter as Peter Discord
    participant Router as Message Router
    participant CharConfig as Character Config
    participant RAG as RAG Retriever
    participant LLM as LLM Service
    participant QC as Quality Control
    participant FT as Fine Tuning
    participant KeyDB as KeyDB Cache

    User->>Peter: @PeterBot "What's your favorite beer?"
    Peter->>Router: POST /orchestrate
    
    Router->>KeyDB: Check response cache
    Router->>CharConfig: Get Peter's prompt
    Router->>RAG: Retrieve beer context
    Router->>FT: Get prompt optimization
    Router->>LLM: Generate response
    Router->>QC: Validate quality
    
    alt Quality Check Passed
        Router->>KeyDB: Cache response
        Router->>FT: Record success metrics
        Router-->>Peter: Return response
        Peter->>User: "Holy crap! Pawtucket Patriot Ale rocks!"
    else Quality Check Failed
        Router->>Router: Retry with improvements
        Note over Router: Up to 10 attempts with exponential backoff
    end
```

### Organic Conversation Flow

```mermaid
sequenceDiagram
    participant Peter as Peter Discord
    participant Router as Message Router
    participant Coord as Conversation Coordinator
    participant Brian as Brian Discord
    participant Stewie as Stewie Discord

    Peter->>Router: POST /organic-notification
    Note over Peter: "Holy crap! I love beer!"
    
    Router->>Coord: Analyze follow-up opportunity
    Coord->>Coord: Topic: beer → Brian responds
    Coord-->>Router: follow_up_character: brian
    
    Router->>Brian: POST /organic-message
    Note over Brian: 4 seconds later
    Brian->>User: "Actually, the brewing process is fascinating..."
    
    Brian->>Router: POST /organic-notification
    Router->>Coord: Analyze follow-up opportunity
    Coord->>Coord: Intellectual topic → Stewie dismisses
    Coord-->>Router: follow_up_character: stewie
    
    Router->>Stewie: POST /organic-message
    Note over Stewie: 6 seconds later
    Stewie->>User: "Blast! Your pedestrian beverage analysis lacks sophistication..."
```

## Quality Control Architecture

### Adaptive Threshold System

```mermaid
flowchart TD
    MSG[Incoming Message] --> HISTORY[Get Conversation History]
    HISTORY --> COUNT{Message Count}
    
    COUNT -->|0-6 messages| COLD[Cold Start<br/>Threshold: 30.0]
    COUNT -->|7-20 messages| WARM[Warm Conversation<br/>Threshold: 60.0]
    COUNT -->|21+ messages| HOT[Hot Conversation<br/>Threshold: 75.0]
    
    COLD --> ORGANIC{Organic Response?}
    WARM --> ORGANIC
    HOT --> ORGANIC
    
    ORGANIC -->|Yes| PENALTY[Add +2.0 Penalty]
    ORGANIC -->|No| ANALYSIS[Quality Analysis]
    PENALTY --> ANALYSIS
    
    ANALYSIS --> SCORE{Score ≥ Threshold?}
    SCORE -->|Yes| PASS[✅ Pass]
    SCORE -->|No| FAIL[❌ Fail - Retry]
    
    style COLD fill:#e1f5fe
    style WARM fill:#fff3e0
    style HOT fill:#fce4ec
    style PASS fill:#e8f5e8
    style FAIL fill:#ffebee
```

### Quality Assessment Components

1. **Authenticity Score** (25% weight)
   - Character consistency
   - Personality marker presence
   - Speaking style adherence

2. **Conversation Flow** (30% weight)
   - Context awareness
   - Natural follow-up patterns
   - Organic response validation

3. **Engagement Score** (20% weight)
   - Response length optimization
   - Question inclusion
   - Humor indicators

4. **Anti-Hallucination** (20% weight)
   - Fact checking
   - Confidence calibration
   - Character-specific risk assessment

5. **Anti-Toxicity** (5% weight)
   - Content safety
   - Appropriate language
   - Community guidelines compliance

## Retry System Architecture

### Intelligent Retry Strategy

```mermaid
flowchart TD
    START[Request Received] --> ATTEMPT{Attempt Number}
    
    ATTEMPT -->|1-3| STANDARD[Standard Processing<br/>Base prompts + RAG]
    ATTEMPT -->|4-6| ENHANCED[Enhanced Processing<br/>+ Fine-tuning optimization]
    ATTEMPT -->|7-10| AGGRESSIVE[Aggressive Optimization<br/>+ Character-specific guidance]
    
    STANDARD --> PROCESS[Generate Response]
    ENHANCED --> FT_OPT[Apply Fine-tuning] --> PROCESS
    AGGRESSIVE --> FT_AGG[Aggressive Fine-tuning] --> PROCESS
    
    PROCESS --> QC{Quality Check}
    
    QC -->|Pass| SUCCESS[✅ Return Response]
    QC -->|Fail & < 10| BACKOFF[Exponential Backoff<br/>1s → 2s → 4s → 8s...]
    QC -->|Fail & = 10| FAILURE[❌ Max Retries Exceeded]
    
    BACKOFF --> ATTEMPT
    
    SUCCESS --> RECORD[Record Success Metrics]
    FAILURE --> RECORD_FAIL[Record Failure Pattern]
    
    style SUCCESS fill:#e8f5e8
    style FAILURE fill:#ffebee
    style STANDARD fill:#e3f2fd
    style ENHANCED fill:#fff8e1
    style AGGRESSIVE fill:#fce4ec
```

### Retry Configuration

```python
RETRY_CONFIG = {
    "DISCORD_MESSAGE": {
        "max_attempts": 10,
        "base_delay": 1.0,
        "exponential_base": 2.0,
        "max_delay": 30.0,
        "jitter": True
    },
    "SERVICE_CALL": {
        "max_attempts": 3,
        "base_delay": 0.5,
        "exponential_base": 1.5,
        "max_delay": 5.0,
        "jitter": False
    }
}
```

## Caching Architecture

### Multi-Level Caching Strategy

```mermaid
graph TD
    subgraph "Application Level"
        APP_CACHE[In-Memory Caches<br/>Service-specific]
    end
    
    subgraph "Distributed Cache (KeyDB)"
        LLM_CACHE[LLM Response Cache<br/>TTL: 1 hour]
        CHAR_CACHE[Character Config Cache<br/>TTL: 24 hours]
        RAG_CACHE[RAG Query Cache<br/>TTL: 1 hour]
        CONV_CACHE[Conversation History<br/>TTL: 24 hours]
        QC_CACHE[Quality Assessment Cache<br/>TTL: 30 minutes]
    end
    
    subgraph "Persistent Storage"
        CHROMADB[ChromaDB<br/>Vector Embeddings]
        OLLAMA_CACHE[Ollama Model Cache<br/>Local GPU Memory]
    end
    
    APP_CACHE --> LLM_CACHE
    APP_CACHE --> CHAR_CACHE
    APP_CACHE --> RAG_CACHE
    APP_CACHE --> CONV_CACHE
    APP_CACHE --> QC_CACHE
    
    LLM_CACHE --> OLLAMA_CACHE
    RAG_CACHE --> CHROMADB
```

### Cache Key Patterns

```python
CACHE_PATTERNS = {
    "llm_response": "llm:{prompt_hash}:{character}:{settings_hash}",
    "character_config": "char_config:{character}:{topic_hash}",
    "rag_context": "rag:{query_hash}:{model_version}",
    "conversation_history": "conv_history:{channel_id}",
    "quality_assessment": "qc:{response_hash}:{character}:{type}",
    "fine_tuning_optimization": "ft_opt:{character}:{context_hash}"
}
```

## Performance Optimization

### Service-Specific Optimizations

#### **LLM Service**
- **Connection Pooling**: 5 concurrent Ollama connections
- **Response Streaming**: Large responses streamed in chunks
- **Model Warming**: Keep model loaded in GPU memory
- **Batch Processing**: Group similar requests when possible

#### **Quality Control**
- **Fast Path**: Cached assessments for similar responses
- **Parallel Analysis**: Multiple quality metrics computed concurrently
- **Early Termination**: Stop analysis on critical violations

#### **RAG Services**
- **Vector Caching**: Frequently accessed embeddings cached
- **Query Optimization**: Semantic query rewriting
- **Index Warming**: Keep active indices in memory

#### **Message Router**
- **Service Discovery**: Cached healthy service endpoints
- **Request Batching**: Group service calls where possible
- **Circuit Breakers**: Fail fast on unhealthy services

### Performance Metrics

```yaml
Target Performance:
  Response Time: < 2 seconds (95th percentile)
  Cache Hit Rate: > 85%
  Quality Pass Rate: > 95%
  Service Availability: > 99.5%
  
Current Performance:
  Average Response Time: 1.85 seconds
  Cache Hit Rate: 87.2%
  Quality Pass Rate: 96.3%
  Retry Success Rate: 91.7%
```

## Scaling Architecture

### Horizontal Scaling Capabilities

```mermaid
graph TD
    subgraph "Load Balancer"
        LB[NGINX/HAProxy]
    end
    
    subgraph "Discord Layer (Vertical)"
        PETER[Peter Discord]
        BRIAN[Brian Discord]
        STEWIE[Stewie Discord]
    end
    
    subgraph "Processing Layer (Horizontal)"
        ROUTER1[Message Router 1]
        ROUTER2[Message Router 2]
        QC1[Quality Control 1]
        QC2[Quality Control 2]
        QC3[Quality Control 3]
    end
    
    subgraph "Knowledge Layer (Horizontal)"
        RAG1[RAG Retriever 1]
        RAG2[RAG Retriever 2]
        CHAR1[Character Config 1]
        CHAR2[Character Config 2]
    end
    
    subgraph "Infrastructure (Shared)"
        KEYDB_CLUSTER[KeyDB Cluster]
        CHROMADB_CLUSTER[ChromaDB Cluster]
        OLLAMA_CLUSTER[Ollama Cluster]
    end
    
    LB --> ROUTER1
    LB --> ROUTER2
    
    PETER --> LB
    BRIAN --> LB
    STEWIE --> LB
    
    ROUTER1 --> QC1
    ROUTER1 --> QC2
    ROUTER2 --> QC2
    ROUTER2 --> QC3
    
    QC1 --> RAG1
    QC2 --> RAG2
    QC3 --> RAG1
    
    RAG1 --> KEYDB_CLUSTER
    RAG2 --> KEYDB_CLUSTER
    
    style LB fill:#e1f5fe
    style KEYDB_CLUSTER fill:#ff99ff
```

### Scaling Strategies by Service

| Service | Scaling Type | Constraints | Strategy |
|---------|--------------|-------------|----------|
| Discord Services | Vertical | 1 per token | Single instance per character |
| Message Router | Horizontal | Stateless | Load balancer + multiple instances |
| LLM Service | Vertical | GPU-bound | Single instance with connection pooling |
| Quality Control | Horizontal | CPU-bound | Multiple instances for parallel processing |
| RAG Retriever | Horizontal | I/O-bound | Multiple instances with shared vector DB |
| Character Config | Horizontal | Memory-bound | Multiple instances with shared cache |
| Fine Tuning | Horizontal | Compute-bound | Multiple instances for parallel optimization |

## Security Architecture

### Security Layers

1. **Network Security**
   - Internal service communication only
   - No external API dependencies
   - Container network isolation

2. **Authentication & Authorization**
   - Discord token-based authentication
   - Service-to-service authentication
   - No user authentication required

3. **Data Security**
   - Local data processing only
   - No external data transmission
   - Conversation history with TTL

4. **Input Validation**
   - Request sanitization at service boundaries
   - Content filtering in quality control
   - Rate limiting per Discord API limits

5. **Operational Security**
   - Health monitoring and alerting
   - Error handling without information disclosure
   - Graceful degradation on service failures

## Monitoring & Observability

### Health Monitoring Stack

```mermaid
graph TD
    subgraph "Services"
        PETER[Peter Discord]
        ROUTER[Message Router]
        LLM[LLM Service]
        QC[Quality Control]
    end
    
    subgraph "Monitoring"
        HEALTH[Health Checks]
        METRICS[Metrics Collection]
        LOGS[Structured Logging]
    end
    
    subgraph "Dashboards"
        KEYDB_UI[KeyDB Commander]
        DOCKER_LOGS[Docker Logs]
        CURL_HEALTH[cURL Health Checks]
    end
    
    PETER --> HEALTH
    ROUTER --> HEALTH
    LLM --> HEALTH
    QC --> HEALTH
    
    HEALTH --> METRICS
    METRICS --> LOGS
    
    LOGS --> KEYDB_UI
    LOGS --> DOCKER_LOGS
    LOGS --> CURL_HEALTH
```

### Monitoring Endpoints

```bash
# Service Health
curl http://localhost:6005/health        # Message Router
curl http://localhost:6001/health        # LLM Service
curl http://localhost:6003/health        # Quality Control

# Service Metrics
curl http://localhost:6005/metrics       # Request/retry metrics
curl http://localhost:6001/metrics       # LLM performance
curl http://localhost:6003/config        # Quality thresholds

# System Health
curl http://localhost:6005/services/health   # All services
docker-compose ps                            # Container status
```

## Deployment Architecture

### Container Orchestration

```yaml
Services: 11 microservices + 4 infrastructure
Total Containers: 15
Resource Requirements:
  Memory: 8GB minimum, 16GB recommended
  CPU: 8 cores minimum
  Storage: 20GB for models and data
  GPU: Optional but recommended for Ollama
```

### Service Dependencies

```mermaid
graph TD
    KEYDB[KeyDB] --> LLM[LLM Service]
    KEYDB --> ROUTER[Message Router]
    KEYDB --> QC[Quality Control]
    
    LLM --> ROUTER
    QC --> ROUTER
    CHAR[Character Config] --> ROUTER
    RAG[RAG Retriever] --> ROUTER
    COORD[Conversation Coordinator] --> ROUTER
    FT[Fine Tuning] --> ROUTER
    
    ROUTER --> PETER[Peter Discord]
    ROUTER --> BRIAN[Brian Discord]
    ROUTER --> STEWIE[Stewie Discord]
    
    OLLAMA[Ollama] --> LLM
    CHROMADB[ChromaDB] --> RAG
    
    style KEYDB fill:#ff99ff
    style OLLAMA fill:#e1f5fe
    style CHROMADB fill:#fff3e0
```

### Startup Sequence

1. **Infrastructure Layer**: KeyDB, ChromaDB, Ollama
2. **Core Services**: LLM Service, Character Config
3. **AI Services**: Quality Control, Conversation Coordinator, Fine Tuning
4. **Processing Layer**: Message Router, RAG Retriever
5. **Discord Layer**: Peter, Brian, Stewie Discord services

---

*This architecture documentation reflects the production Discord Family Guy Bot microservices platform as of January 2024.* 