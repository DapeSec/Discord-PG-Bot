# Discord Family Guy Bot Documentation

**Complete technical documentation for the Enterprise Microservices Edition featuring 12 specialized services, organic conversations, and advanced AI capabilities.**

---

## 🏗️ **Current Architecture Overview**

The Discord Family Guy Bot is built as a **12-microservice architecture** running entirely locally with no external API dependencies:

### **🎯 Core Services (12 Total)**
- **3 Discord Handlers** - Peter (6011), Brian (6012), Stewie (6013)
- **3 Core AI Services** - LLM Service (6001), Message Router (6005), Quality Control (6003)
- **3 Intelligence Services** - Conversation Coordinator (6002), Fine Tuning (6004), Orchestrator (6008)
- **3 Knowledge Services** - Character Config (6006), RAG Retriever (6007), RAG Crawler (6009)

### **🔧 Technology Stack**
- **Language**: Python 3.11+ with asyncio
- **LLM**: Mistral-Nemo via Ollama (local)
- **Caching**: KeyDB (Redis-compatible, faster)
- **Vector Store**: ChromaDB 0.4.22
- **Web Framework**: Flask 2.0.1
- **Discord**: discord.py 2.3.2
- **AI/ML**: LangChain 0.0.350, SentenceTransformers 2.7.0, PyTorch 2.1.0

### **⚡ Infrastructure**
- **KeyDB Cache** (6379) - High-performance caching
- **KeyDB Commander** (8081) - Web UI for cache monitoring
- **ChromaDB** - Embedded vector database
- **Ollama** (11434) - Local LLM inference

---

## 📚 **Documentation Structure**

This documentation covers every aspect of the system, from quick setup to advanced customization:

### **🚀 Getting Started**
- **[QUICKSTART.md](QUICKSTART.md)** - 5-minute setup guide with zero external dependencies
- **[MISTRAL_SETUP.md](MISTRAL_SETUP.md)** - Local LLM configuration for RTX GPUs
- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Production deployment strategies

### **🏗️ Architecture & Design**
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - High-level system overview
- **[System_Architecture.md](System_Architecture.md)** - Detailed 12-microservice breakdown
- **[RAG_MICROSERVICES_ARCHITECTURE.md](RAG_MICROSERVICES_ARCHITECTURE.md)** - Knowledge retrieval system
- **[KEYDB_IMPLEMENTATION_GUIDE.md](KEYDB_IMPLEMENTATION_GUIDE.md)** - High-performance caching layer

### **🧠 Advanced AI Features**
- **[Organic_Conversation_Orchestrator.md](Organic_Conversation_Orchestrator.md)** - 🌱 Dynamic conversation system
- **[Quality_Control.md](Quality_Control.md)** - Adaptive quality assessment (30-75/100 thresholds)
- **[No_Fallback_Mode.md](No_Fallback_Mode.md)** - Infinite retry system for quality responses
- **[RAG_System.md](RAG_System.md)** - Family Guy knowledge base and context retrieval
- **[FINE_TUNING_GUIDE.md](FINE_TUNING_GUIDE.md)** - Response optimization and A/B testing

### **⚙️ Operations & Management**
- **[Data_Management.md](Data_Management.md)** - KeyDB caching patterns and data flow
- **[REQUIREMENTS_OPTIMIZATION.md](REQUIREMENTS_OPTIMIZATION.md)** - Dependency management across 12 services
- **[../TROUBLESHOOTING.md](../TROUBLESHOOTING.md)** - Common issues and monitoring

---

## 🎭 **Character AI System**

### **Authentic Personality Implementation**
Each character features deeply researched personality traits, speaking patterns, and interaction dynamics:

- **🍺 Peter Griffin**: Impulsive, beer-loving, "Holy crap!" energy (50% conversation initiation)
- **🐕 Brian Griffin**: Intellectual, literary, philosophical discussions (30% initiation)  
- **👶 Stewie Griffin**: Evil genius, sophisticated vocabulary, condescending (40% initiation)

### **Dynamic Conversation Features**
- **LLM-Generated Starters**: Character-specific conversation prompts with Family Guy context
- **Follow-up Analysis**: Content triggers for multi-character responses (2-8 second delays)
- **Organic Timing**: 15+ minute silence detection with 40% probability triggers

---

## 🚀 **Key Innovations**

### **🌱 Organic Conversation Orchestrator**
Revolutionary system for natural character interactions:
```bash
# Test dynamic conversation generation
curl -X POST http://localhost:6008/test-starter \
  -H "Content-Type: application/json" \
  -d '{"character": "peter"}'

# Monitor organic conversation status
curl http://localhost:6008/organic_conversation_status
```

### **📊 Adaptive Quality Control**
Quality thresholds that adapt to conversation richness:
- **Cold Start** (0-6 messages): 30/100 threshold - lenient for first interactions
- **Warm** (7-20 messages): 60/100 threshold - moderate with developing context  
- **Hot** (21+ messages): 75/100 threshold - high standards with rich history

### **⚡ KeyDB Performance Caching**
High-performance caching system:
- **LLM Response Cache**: 1-hour TTL for generated responses
- **Character Config Cache**: 24-hour TTL for character prompts
- **RAG Query Cache**: 1-hour TTL for context retrieval
- **Web UI**: Monitor cache performance at `http://localhost:8081`

### **📚 Dual-Microservice RAG System**
Optimized knowledge retrieval architecture:
- **RAG Retriever** (6007): <100ms real-time context retrieval
- **RAG Crawler** (6009): Batch Family Guy wiki crawling and indexing

---

## 🎯 **Service Health Monitoring**

### **Health Check Endpoints**
```bash
# Core AI Services
curl http://localhost:6001/health  # LLM Service
curl http://localhost:6005/health  # Message Router
curl http://localhost:6003/health  # Quality Control

# Intelligence Services  
curl http://localhost:6002/health  # Conversation Coordinator
curl http://localhost:6004/health  # Fine Tuning
curl http://localhost:6008/health  # Orchestrator

# Knowledge Services
curl http://localhost:6006/health  # Character Config
curl http://localhost:6007/health  # RAG Retriever
curl http://localhost:6009/health  # RAG Crawler

# Discord Handlers
curl http://localhost:6011/health  # Peter Discord
curl http://localhost:6012/health  # Brian Discord  
curl http://localhost:6013/health  # Stewie Discord
```

### **Performance Testing**
```bash
# Test LLM service performance
curl -X POST http://localhost:6001/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Hello", "character_name": "Peter"}'

# Check RAG retrieval speed
curl -X POST http://localhost:6007/retrieve \
  -H "Content-Type: application/json" \
  -d '{"query": "chicken fight", "num_results": 3}'

# Trigger organic conversation manually
curl -X POST http://localhost:6008/trigger-organic
```

---

## 📈 **System Requirements & Performance**

### **Minimum Requirements**
- **RAM**: 16GB (4GB for Mistral-Nemo + 12GB for services)
- **Storage**: 20GB free (model + Docker images + ChromaDB)
- **CPU**: 8+ cores (optimized for multi-threading)
- **Optional**: RTX 4070+ for GPU acceleration

### **Expected Performance**
- **Response Time**: <2 seconds for standard queries
- **RAG Retrieval**: <100ms for context lookup
- **Organic Conversations**: 15-min silence → 40% trigger probability
- **Memory Usage**: ~8-12GB total system usage
- **Cache Hit Rate**: >80% for repeated queries

---

## 🔧 **Configuration Management**

### **Environment Variables**
```bash
# Discord Integration
DISCORD_BOT_TOKEN_PETER=your_peter_token
DISCORD_BOT_TOKEN_BRIAN=your_brian_token  
DISCORD_BOT_TOKEN_STEWIE=your_stewie_token
DEFAULT_DISCORD_CHANNEL_ID=your_channel_id

# LLM Configuration
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=mistral-nemo

# KeyDB Caching
REDIS_URL=redis://keydb:6379
LLM_RESPONSE_CACHE_TTL=3600
CHARACTER_CONFIG_CACHE_TTL=86400
RAG_QUERY_CACHE_TTL=3600

# Quality Control
COLD_START_THRESHOLD=30.0
WARM_CONVERSATION_THRESHOLD=60.0
HOT_CONVERSATION_THRESHOLD=75.0

# Organic Conversations
MIN_TIME_BETWEEN_ORGANIC_CONVERSATIONS=5
CONVERSATION_SILENCE_THRESHOLD_MINUTES=15
ORGANIC_CONVERSATION_PROBABILITY=0.4
```

---

## 📊 Documentation Status

### **Current Version**: Enterprise Edition v3.0
### **Last Updated**: January 2025  
### **Documentation Coverage**: ✅ Complete
### **System Status**: ✅ Production Ready

**Key Features in This Version:**
- 🌱 **Organic Conversation Orchestrator** with LLM-generated starters
- 📊 **Enhanced Adaptive Quality Control** with character-specific tuning
- 🏗️ **Complete 12-microservice architecture** with comprehensive documentation
- 🎭 **Character personality system** with authentic AI interactions
- 📚 **Advanced dual-microservice RAG system** for optimal performance

---

**🎭 Welcome to the most sophisticated Family Guy Discord bot ecosystem ever created - where enterprise-grade architecture meets authentic character AI!** 