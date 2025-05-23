# Family Guy Discord Bots

An interactive Discord bot system featuring Peter Griffin, Brian Griffin, and Stewie Griffin from Family Guy. The bots use a **centralized LLM architecture** with **advanced AI systems** including **Supervised Fine-Tuning**, **Quality Control**, **RAG Integration**, and **Organic Conversation Coordination**. The orchestrator handles all language model processing through Ollama, generating responses in characteristic styles while continuously improving character accuracy through automated learning systems.

## Table of Contents
1. [System Architecture](#system-architecture)
2. [Advanced Systems Overview](#advanced-systems-overview) 
3. [System Interactions](#system-interactions)
4. [Features](#features)
5. [Project Structure](#project-structure)
6. [Prerequisites](#prerequisites)
7. [Installation](#installation)
8. [Docker Setup](#docker-setup)
9. [Usage](#usage)
10. [Technical Details](#technical-details)
11. [Architecture Benefits](#architecture-benefits)
12. [Contributing](#contributing)
13. [License](#license)

## System Architecture

```mermaid
graph TD
    subgraph Discord["🎮 Discord Platform"]
        DC[Discord Channels]
        DU[Discord Users]
    end

    subgraph Host["🖥️ Host Machine"]
        OL[Ollama LLM<br>🚀 GPU Accelerated]
        ML[Model Loading<br>& Caching]
    end

    subgraph Docker["🐳 Docker Environment"]
        subgraph Orchestrator["🎭 Orchestrator Container"]
            OS[Orchestrator Service<br>:5003]
            
            subgraph LLMSys["🧠 LLM Processing"]
                CL[Centralized LLM<br>Character Generation]
                CP[Character Prompts<br>& Personalities]
                LLMCoord[LLM Conversation<br>Coordinator]
            end
            
            subgraph FineTune["🎯 Fine-Tuning System"]
                PFT[Prompt Fine-Tuner]
                LLMAssess[LLM Auto-Assessment]
                QC[Quality Control Agent]
                ABTest[A/B Testing Engine]
            end
            
            subgraph OrgSys["🌱 Organic System"]
                OCC[Organic Conversation<br>Coordinator]
                PatternAnalyzer[Conversation Pattern<br>Analyzer]
                StarterGen[RAG-Enhanced<br>Starter Generator]
            end
            
            subgraph RAGSys["🔍 RAG System"]
                VDB[(Chroma Vector DB<br>Family Guy Wiki)]
                Embed[Sentence Transformers<br>Embeddings]
                ContextRet[Context Retrieval<br>& Augmentation]
            end
            
            subgraph ErrorSys["⚠️ Error Management"]
                DLQ[Dead Letter Queue]
                RetryWorker[Retry Worker<br>Background Process]
                ErrorHandler[Error Handler<br>& Fallbacks]
            end
        end

        subgraph Bots["🤖 Bot Containers"]
            PB[Peter Bot<br>:5005<br>Discord Interface Only]
            BB[Brian Bot<br>:5002<br>Discord Interface Only]
            SB[Stewie Bot<br>:5004<br>Discord Interface Only]
        end

        subgraph Storage["💾 Storage Layer"]
            MDB[(MongoDB :27017<br>📊 Conversations<br>📈 Ratings<br>🎯 Metrics<br>📝 Prompt Versions)]
            LogStore[(📋 Log Storage<br>System Events)]
        end
    end

    %% Data Flow Connections
    DC <--> DU
    DU <--> PB & BB & SB
    
    %% Bot to Orchestrator Flow
    PB & BB & SB --> OS
    
    %% Orchestrator Internal Flow
    OS --> LLMSys
    CL --> CP
    CL --> OL
    OL --> ML
    
    %% Fine-Tuning System Flow
    CL --> FineTune
    LLMAssess --> PFT
    PFT --> QC
    QC --> CL
    ABTest --> CP
    
    %% Organic Conversation Flow
    OCC --> LLMSys
    PatternAnalyzer --> OCC
    StarterGen --> RAGSys
    
    %% RAG System Flow
    RAGSys --> CL
    VDB --> ContextRet
    Embed --> VDB
    ContextRet --> CL
    
    %% Error Management Flow
    ErrorSys --> OS
    DLQ --> RetryWorker
    RetryWorker --> PB & BB & SB
    
    %% Storage Connections
    OS --> MDB
    FineTune --> MDB
    OCC --> MDB
    PB & BB & SB --> LogStore

    %% Styling
    style Discord fill:#7289DA,color:white
    style Docker fill:#4CAF50,color:white
    style Host fill:#FF9800,color:white
    style Storage fill:#2196F3,color:white
    style Orchestrator fill:#FF5722,color:white
    style LLMSys fill:#9C27B0,color:white
    style FineTune fill:#E91E63,color:white
    style OrgSys fill:#009688,color:white
    style RAGSys fill:#795548,color:white
    style ErrorSys fill:#607D8B,color:white
```

## Advanced Systems Overview

The Discord bot system includes several sophisticated AI-powered subsystems that work together to create an intelligent, self-improving conversational experience:

### 🎯 Supervised Fine-Tuning System
**Automatically improves character accuracy through continuous learning**
- **LLM Auto-Assessment**: Every response is automatically evaluated by the LLM for character accuracy (1-5 rating scale)
- **Quality Control Agent**: Pre-send filtering ensures only high-quality responses reach users
- **Prompt Optimization Engine**: Automatically improves character prompts based on accumulated feedback
- **A/B Testing System**: Safely tests optimized prompts on limited traffic before full deployment
- **Performance Tracking**: Comprehensive metrics and improvement analytics

### 🧠 Advanced Conversation Coordination
**Intelligent response selection and conversation management**
- **LLM Conversation Coordinator**: Uses character descriptions and context to intelligently select who should respond
- **RAG-Enhanced Decision Making**: Leverages Family Guy universe knowledge for character selection
- **Multi-Factor Analysis**: Considers topic relevance, character dynamics, recent activity, and personality triggers
- **Conversation Balance**: Ensures fair participation across all characters

### 🌱 Organic Conversation System
**Natural conversation initiation without rigid scheduling**
- **Context-Driven Triggers**: Analyzes conversation patterns to detect natural conversation opportunities
- **Intelligent Pattern Recognition**: Identifies conversation endings, unresolved topics, and follow-up opportunities
- **RAG-Enhanced Starters**: Generates contextual conversation starters using Family Guy universe knowledge
- **Character-Aware Initiation**: Uses the same coordinator logic to select appropriate conversation initiators
- **Natural Flow Management**: Respects conversation cooldowns and avoids interrupting active discussions

### 🔍 RAG (Retrieval-Augmented Generation) System
**Context-aware responses using Family Guy universe knowledge**
- **Vector Database**: Chroma DB storing Family Guy wiki content as searchable embeddings
- **Automatic Crawling**: Weekly automated updates of Family Guy universe knowledge
- **Context Integration**: Seamlessly incorporates relevant background information into responses
- **Multi-Purpose Usage**: Enhances responses, conversation coordination, and starter generation

### ⚠️ Robust Error Management
**Comprehensive failure handling and recovery**
- **Dead Letter Queue**: Failed messages are queued for intelligent retry with exponential backoff
- **Retry Worker**: Background process continuously attempts to resolve failed operations
- **Graceful Degradation**: System continues functioning even when components fail
- **Error Classification**: Different handling for LLM failures, Discord issues, and database problems

## System Interactions

### 📊 Complete Workflow: User Message to Response

```mermaid
sequenceDiagram
    participant User as 👤 Discord User
    participant Bot as 🤖 Character Bot
    participant Orch as 🎭 Orchestrator
    participant Coord as 🧠 LLM Coordinator
    participant RAG as 🔍 RAG System
    participant LLM as 🤖 Centralized LLM
    participant QC as 🛡️ Quality Control
    participant Assess as 📊 LLM Assessment
    participant FT as 🎯 Fine-Tuning
    participant DB as 💾 MongoDB

    User->>Bot: "Hey Peter, what's up?"
    Bot->>Orch: POST /orchestrate {user_query, channel_id}
    
    Orch->>DB: Fetch conversation history
    DB-->>Orch: Historical context
    
    Orch->>Coord: Analyze message + history
    Note over Coord: Uses character descriptions<br/>+ conversation patterns<br/>+ recent activity
    Coord-->>Orch: Selected character: Peter
    
    Orch->>RAG: Retrieve context for user query
    RAG->>RAG: Search Family Guy wiki vectors
    RAG-->>Orch: Relevant context
    
    Orch->>QC: Generate quality-controlled response
    
    loop Quality Control (max 3 attempts)
        QC->>LLM: Generate Peter response
        Note over LLM: Uses character prompt<br/>+ conversation history<br/>+ RAG context
        LLM-->>QC: Generated response
        
        QC->>Assess: Evaluate response quality
        Note over Assess: LLM assessment:<br/>- Speech patterns (25%)<br/>- Personality (25%)<br/>- Character knowledge (20%)<br/>- Humor style (20%)<br/>- Context appropriateness (10%)
        Assess-->>QC: Quality rating + feedback
        
        alt Quality >= 3.0/5
            QC-->>Orch: Approved response
        else Quality < 3.0/5
            Note over QC: Retry with feedback
        end
    end
    
    Orch->>DB: Store conversation + assessment
    Orch->>Bot: Send approved response
    Bot->>User: "Hehehehehe! Just watching TV!"
    
    Assess->>FT: Record quality assessment
    FT->>DB: Store rating + feedback
    
    Note over FT: Background optimization<br/>if ratings drop below 0.7
```

### 🌱 Organic Conversation Initiation Flow

```mermaid
sequenceDiagram
    participant OCC as 🌱 Organic Coordinator
    participant PA as 🔍 Pattern Analyzer
    participant Coord as 🧠 LLM Coordinator
    participant SG as 📝 Starter Generator
    participant RAG as 🔍 RAG System
    participant Orch as 🎭 Orchestrator
    participant Bot as 🤖 Selected Bot
    participant Discord as 💬 Discord

    Note over OCC: Every 5 minutes
    OCC->>PA: Analyze recent conversations
    PA->>PA: Check silence duration<br/>Look for conversation triggers<br/>Detect natural endpoints
    PA-->>OCC: Conversation opportunity detected
    
    OCC->>Coord: Select conversation initiator
    Note over Coord: Uses character personality<br/>+ recent activity balance<br/>+ conversation context
    Coord-->>OCC: Selected character: Brian
    
    OCC->>SG: Generate conversation starter
    SG->>RAG: Get Family Guy context
    RAG-->>SG: Relevant universe knowledge
    SG->>SG: Create character-appropriate starter
    SG-->>OCC: "I've been contemplating..."
    
    OCC->>Orch: Initiate organic conversation
    Note over Orch: Uses same workflow as<br/>user-initiated conversations
    Orch->>Bot: Send starter message
    Bot->>Discord: Post organic conversation starter
```

### 🎯 Fine-Tuning System Operation

```mermaid
graph LR
    subgraph RT["🔄 Real-Time Assessment"]
        Response[Generated Response] --> LLMAssess[LLM Auto-Assessment]
        LLMAssess --> QualityScore[Quality Score 1-5]
        QualityScore --> Record[Record Rating]
    end
    
    subgraph BG["⚙️ Background Optimization"]
        Record --> Monitor[Monitor Avg Rating]
        Monitor --> Trigger{Avg < 0.7?}
        Trigger -->|Yes| Optimize[Optimize Prompt]
        Optimize --> NewPrompt[Generate New Prompt]
        NewPrompt --> ABTest[A/B Test 20% Traffic]
        ABTest --> Validate[Validate Performance]
        Validate --> Deploy[Deploy if Better]
    end
    
    subgraph QC["🛡️ Quality Control"]
        QualityScore --> Check{Rating >= 3.0?}
        Check -->|No| Retry[Regenerate Response]
        Check -->|Yes| Approve[Approve Response]
        Retry --> Response
        Approve --> SendUser[Send to User]
    end

    style RT fill:#E1F5FE
    style BG fill:#F3E5F5
    style QC fill:#E8F5E8
```

### 💾 Data Flow and Storage

```mermaid
graph TD
    subgraph Input["📥 Input Sources"]
        UserMsg[User Messages]
        BotResp[Bot Responses]
        OrgConv[Organic Conversations]
    end
    
    subgraph Processing["⚙️ Real-Time Processing"]
        LLMGen[LLM Generation]
        QualAssess[Quality Assessment]
        RAGEnrich[RAG Enrichment]
        ConvCoord[Conversation Coordination]
    end
    
    subgraph Storage["💾 MongoDB Collections"]
        Conversations[(conversations<br/>💬 Message history<br/>📅 Timestamps<br/>🏷️ Session IDs)]
        Ratings[(response_ratings<br/>⭐ Quality scores<br/>💭 Feedback<br/>👤 Assessor ID)]
        PromptVersions[(prompt_versions<br/>📝 Prompt text<br/>🔢 Version numbers<br/>📊 Performance data)]
        Metrics[(performance_metrics<br/>📈 Avg ratings<br/>📊 Improvement trends<br/>🎯 Optimization history)]
        DLQ[(dead_letter_queue<br/>❌ Failed messages<br/>🔄 Retry attempts<br/>⏰ Next retry time)]
    end
    
    subgraph Analytics["📊 Analytics & Learning"]
        PerfMonitor[Performance Monitoring]
        TrendAnalysis[Trend Analysis]
        PromptOpt[Prompt Optimization]
        QualityTrends[Quality Trends]
    end
    
    Input --> Processing
    Processing --> Storage
    Storage --> Analytics
    Analytics --> Processing
    
    style Input fill:#E3F2FD
    style Processing fill:#F1F8E9
    style Storage fill:#FFF3E0
    style Analytics fill:#FCE4EC
```

## Features

- **🧠 Advanced AI Architecture**: Centralized LLM with sophisticated coordination and quality systems
- **🎯 Automatic Quality Improvement**: Supervised fine-tuning with LLM-based assessment and optimization
- **🛡️ Quality Control**: Pre-send filtering ensures only high-quality responses reach users
- **🔍 RAG-Enhanced Responses**: Context-aware responses using Family Guy universe knowledge
- **🌱 Organic Conversations**: Natural conversation initiation based on context and patterns
- **📊 Comprehensive Analytics**: Real-time performance monitoring and improvement tracking
- **⚡ Resource Efficient**: ~66% reduction in memory usage compared to distributed LLM setup
- **🎭 Three Distinct Personalities**:
  - **Peter**: Humorous, dim-witted, with tangents and "Heheheh" interjections
  - **Brian**: Intellectual, sarcastic, sophisticated vocabulary and cultural references
  - **Stewie**: Evil genius baby with British accent, scientific knowledge, and megalomaniacal plans
- **🐳 Containerized Microservices**: Each component runs in isolated containers
- **🚀 GPU-Accelerated Responses**: Leverages host Ollama for fast generation
- **💾 Persistent Everything**: MongoDB stores conversations, ratings, prompts, and metrics
- **🔄 Multi-Bot Interactions**: Natural conversation flow between characters
- **⚠️ Robust Error Handling**: Dead Letter Queue with intelligent retry mechanisms
- **🏥 Health Monitoring**: Comprehensive health checks for all system components

## Architecture Benefits

### 🎯 Continuous Improvement
- **Self-Learning System**: Automatically improves character accuracy without manual intervention
- **Quality Assurance**: Every response is pre-screened for quality before reaching users
- **Data-Driven Optimization**: Uses accumulated feedback to optimize character prompts
- **Safe Innovation**: A/B testing ensures changes only improve the system

### 🧠 Intelligent Coordination
- **Context-Aware Selection**: Who responds is determined by conversation context and character expertise
- **Natural Flow**: Conversations feel organic rather than scripted or random
- **Character Balance**: Ensures fair participation across all characters
- **Dynamic Adaptation**: System learns from conversation patterns over time

### 🔍 Enhanced Knowledge
- **Universe-Aware**: Responses incorporate deep Family Guy universe knowledge
- **Context Integration**: RAG system seamlessly weaves relevant information into conversations
- **Auto-Updating**: Weekly crawls keep knowledge base current
- **Multi-Purpose RAG**: Enhances responses, coordination decisions, and conversation starters

### ⚡ Performance & Reliability
- **Resource Efficiency**: Single LLM instance instead of three separate ones
- **Fault Tolerance**: System continues working even when components fail
- **Graceful Degradation**: Quality degrades gracefully rather than failing completely
- **Comprehensive Monitoring**: Real-time tracking of all system components

## Project Structure
```
discord-pg-bot/
├── src/                   # Source code
│   └── app/              # Application code
│       ├── bots/         # Bot implementations (Discord only)
│       │   ├── peter_bot.py       # Discord interface only
│       │   ├── brian_bot.py       # Discord interface only
│       │   └── stewie_bot.py      # Discord interface only
│       ├── orchestrator/ # Centralized LLM processing
│       │   └── server.py          # LLM, RAG, and coordination
│       ├── utils/       # Shared utilities
│       │   ├── rag.py
│       │   └── db.py
│       └── models/      # Data models
│           └── conversation.py
├── docker/               # Docker configuration
│   ├── Dockerfile.orchestrator
│   ├── Dockerfile.bot
│   └── docker-compose.yml
├── tests/               # Unit tests and validation
│   ├── conftest.py
│   ├── test_bots.py                    # Discord interface tests
│   ├── test_orchestrator.py            # Centralized LLM tests
│   ├── test_rag.py                     # RAG system tests
│   ├── test_centralized_llm.py         # Architecture-specific tests
│   └── test_architecture_validation.py # Complete architecture validation
├── scripts/            # Utility scripts
│   ├── start-bot.sh
│   ├── setup.sh
│   ├── wait-for-it.py
│   └── performance_benchmark.py        # Performance testing
├── config/             # Configuration files
│   └── env.template                    # Environment variables template
├── logs/              # Application logs
├── chroma_db/         # Vector store data
├── .env               # Environment variables
├── requirements.txt   # Python dependencies
└── README.md         # This documentation
```

## Prerequisites

## System Requirements

### Minimum Requirements
- CPU: 4 cores
- RAM: 8GB
- Storage: 4GB free space
- Operating System: Windows 10/11, macOS, or Linux
- Python 3.8 or higher

### Recommended Requirements (for GPU Acceleration)
- NVIDIA GPU with at least 4GB VRAM
- CUDA Toolkit 11.7 or higher
- NVIDIA drivers 470.x or higher
- RAM: 16GB
- Storage: 8GB free space

### Port Requirements
- 5002: Brian Bot Service
- 5003: Orchestrator Service
- 5004: Stewie Bot Service
- 5005: Peter Bot Service
- 11434: Ollama API
- 27017: MongoDB

2. **Required Software**
   - [Docker](https://www.docker.com/get-started) and Docker Compose
   - [Ollama](https://ollama.ai/) (installed on host machine)
   - [Git](https://git-scm.com/downloads)
   - Discord account and bot tokens

## Installation

1. **Clone the Repository**
   ```bash
   git clone https://github.com/DapeSec/discord-pg-bot.git
   cd discord-pg-bot
   ```

2. **Set up Ollama on Host Machine**
   ```bash
   # Start Ollama service
   ollama serve

   # In another terminal, pull the Mistral model
   ollama pull mistral
   ```

3. **Configure Environment**
   Create a `.env` file in the project root with these required variables:
   ```
   # REQUIRED: Discord Bot Tokens
   DISCORD_BOT_TOKEN_PETER=your_peter_bot_token_here
   DISCORD_BOT_TOKEN_BRIAN=your_brian_bot_token_here
   DISCORD_BOT_TOKEN_STEWIE=your_stewie_bot_token_here

   # REQUIRED: Bot Mention Strings (get these after creating bots)
   PETER_BOT_MENTION_STRING=<@1234567890123456789>
   BRIAN_BOT_MENTION_STRING=<@1234567890123456789>
   STEWIE_BOT_MENTION_STRING=<@1234567890123456789>

   # REQUIRED: Default Discord Channel for Organic Conversations
   DEFAULT_DISCORD_CHANNEL_ID=1234567890123456789

   # OPTIONAL: MongoDB Configuration (defaults provided)
   MONGO_URI=mongodb://admin:adminpassword@mongodb:27017/?authSource=admin
   MONGO_DB_NAME=discord_bot_conversations
   MONGO_COLLECTION_NAME=conversations

   # OPTIONAL: Ollama Configuration (defaults provided)
   OLLAMA_BASE_URL=http://host.docker.internal:11434
   
   # OPTIONAL: Supervised Fine-Tuning System Configuration
   FINE_TUNING_ENABLED=true                    # Enable/disable automatic optimization
   OPTIMIZATION_THRESHOLD=0.7                  # Trigger optimization when avg rating < 0.7
   MIN_RATINGS_FOR_OPTIMIZATION=10             # Minimum ratings before optimization
   AB_TEST_PERCENTAGE=0.2                      # 20% traffic for A/B testing optimized prompts

   # OPTIONAL: Quality Control System Configuration
   QUALITY_CONTROL_ENABLED=true                # Enable/disable pre-send quality filtering
   QUALITY_CONTROL_MIN_RATING=3.0             # Minimum acceptable rating (1-5)
   QUALITY_CONTROL_MAX_RETRIES=3              # Max retries for quality improvement

   # OPTIONAL: Dead Letter Queue Configuration
   DLQ_MAX_RETRY_ATTEMPTS=3                   # Maximum retry attempts for failed messages
   DLQ_RETRY_DELAY_BASE=2.0                   # Base delay for exponential backoff
   DLQ_MAX_RETRY_DELAY=300                    # Maximum delay between retries (seconds)
   DLQ_RETRY_WORKER_INTERVAL=60               # How often to check for retryable messages
   
   # OPTIONAL: Organic Conversation Tuning
   CONVERSATION_SILENCE_THRESHOLD_MINUTES=30  # Minutes of silence before considering new conversation
   MIN_TIME_BETWEEN_ORGANIC_CONVERSATIONS=10  # Minimum minutes between organic attempts
   
   # OPTIONAL: RAG Configuration for Family Guy Wiki
   FANDOM_WIKI_START_URL=https://familyguy.fandom.com/wiki/Main_Page
   FANDOM_WIKI_MAX_PAGES=100
   FANDOM_WIKI_CRAWL_DELAY=1

   # Note: Bot API URLs are automatically configured in Docker
   # Only set these if running outside Docker containers
   ```

## Docker Setup

1. **Build and Start Services**
   ```bash
   # Build and start all services
   docker-compose -f docker/docker-compose.yml up --build

   # Or run in detached mode
   docker-compose -f docker/docker-compose.yml up -d
   ```

2. **Verify Installation**
   ```bash
   # Check running containers
   docker-compose -f docker/docker-compose.yml ps

   # Check logs
   docker-compose -f docker/docker-compose.yml logs -f
   ```

3. **Container Management**
   ```bash
   # Stop all services
   docker-compose -f docker/docker-compose.yml down

   # Restart a specific service
   docker-compose -f docker/docker-compose.yml restart peter
   ```

### MongoDB Access

The MongoDB instance is accessible both from within the Docker network and from your host machine:

1. **From Docker containers:**
   ```
   mongodb://admin:adminpassword@mongodb:27017/
   ```

2. **From host machine:**
   ```
   mongodb://admin:adminpassword@localhost:27017/
   ```

Default credentials:
- Username: `admin`
- Password: `adminpassword`

You can connect using MongoDB Compass or any other MongoDB client using these credentials.

> **Note:** For production, make sure to change these default credentials and use environment variables.

## Usage

### Interacting with the Bots
- Send a message starting with the character's name:
  ```
  !peter Tell me about your day
  !brian What's your opinion on literature?
  !stewie What's your latest evil plan?
  ```
- Or mention any bot using their @mention (e.g., @PeterGriffin, @BrianGriffin, @StewieGriffin)

### Multi-Bot Conversations
When you interact with any bot:
1. The orchestrator receives and processes the message
2. **Quality Control**: The system ensures the response meets quality standards before sending
3. **LLM Auto-Assessment**: Every response is automatically evaluated for character accuracy
4. **Intelligent Selection**: The LLM coordinator determines the most appropriate character to respond
5. **RAG Enhancement**: Relevant Family Guy universe context is incorporated into responses
6. **Response Generation**: High-quality, character-accurate response is delivered
7. **Continuous Learning**: Response quality data is used to improve future responses
8. All conversations are stored in MongoDB for context and learning

### 🎯 Supervised Fine-Tuning System
The system automatically improves character accuracy through continuous learning:

#### Automatic Operation (No Manual Work Required)
- **Every Response Evaluated**: LLM automatically assesses each response for character accuracy (1-5 scale)
- **Quality Control**: Only responses scoring ≥3.0/5 are sent to users (configurable)
- **Automatic Optimization**: When average ratings drop below 0.7, prompts are automatically optimized
- **A/B Testing**: New optimized prompts are safely tested on 20% of traffic before full deployment
- **Performance Tracking**: Real-time monitoring of character accuracy and improvement trends

#### Manual Rating (Optional Enhancement)
You can also provide manual feedback to enhance the learning:
```bash
# Rate a character response via API
curl -X POST http://localhost:5003/rate_response -H "Content-Type: application/json" -d '{
  "character_name": "Peter",
  "response_text": "Hehehehehe! Holy crap, that\''s awesome!",
  "rating": 5,
  "feedback": "Perfect Peter voice with signature laugh and catchphrase"
}'
```

#### Fine-Tuning API Endpoints
- `GET /fine_tuning_stats` - Overall system performance statistics
- `GET /optimization_report?days=7` - Character optimization reports
- `GET /quality_control_status` - Quality control statistics and configuration
- `POST /trigger_optimization` - Manually trigger prompt optimization
- `GET /prompt_performance?character=Peter&days=30` - Detailed character performance metrics

### 🌱 Automated Conversations
The system includes an intelligent organic conversation feature that initiates natural conversations based on context and conversation flow:
- **Context-Driven Initiation**: Conversations start based on natural triggers rather than rigid schedules
- **Intelligent Pattern Analysis**: Detects conversation endings, follow-up opportunities, and silence periods
- **Character-Aware Selection**: Uses the same advanced coordinator that handles responses to choose conversation initiators
- **RAG-Enhanced Starters**: Generates contextual conversation starters using Family Guy universe knowledge
- **Natural Flow**: Respects conversation cooldowns and avoids interrupting active discussions
- **Organic Monitoring**: Continuously monitors for conversation opportunities every 5 minutes
- **Post-Response Analysis**: Checks for follow-up opportunities after each conversation response
- Helps maintain channel activity naturally without artificial scheduling

### 🔍 RAG System Management
The system automatically manages Family Guy universe knowledge:
- **Weekly Auto-Crawl**: Automatically updates Family Guy wiki knowledge weekly
- **Manual Crawl**: Trigger immediate knowledge update:
  ```bash
  curl -X POST http://localhost:5003/load_fandom_wiki -H "Content-Type: application/json" -d '{
    "url": "https://familyguy.fandom.com/wiki/Main_Page",
    "max_pages": 100,
    "delay": 1
  }'
  ```
- **Context Integration**: Knowledge seamlessly woven into all responses and conversations

### 📊 Monitoring and Analytics
Monitor system performance in real-time:
```bash
# Check overall system health
curl http://localhost:5003/health

# Get fine-tuning system statistics
curl http://localhost:5003/fine_tuning_stats

# Get quality control performance
curl http://localhost:5003/quality_control_status

# Get character-specific performance metrics
curl http://localhost:5003/prompt_performance?character=Peter&days=30
```

## Technical Details

### System Components
- **Orchestrator Server** (:5003): 
  - Central message handler and conversation manager
  - **Centralized LLM Processing**: Single Ollama instance for all character responses
  - **Character Prompts**: Maintains personality-specific prompt templates
  - **RAG Integration**: Context retrieval and augmentation
  - **Dead Letter Queue**: Error handling and message retry system
  - **Supervised Fine-Tuning System**: Continuous character improvement through automated learning
  - **Quality Control Agent**: Pre-send response filtering and quality assurance
  - **Organic Conversation Coordinator**: Natural conversation initiation and management
  - **LLM Auto-Assessment**: Automatic response quality evaluation
  - **A/B Testing Engine**: Safe deployment of optimized prompts
- **Character Bots**: 
  - **Peter Bot** (:5005): Discord interface only, no LLM processing
  - **Brian Bot** (:5002): Discord interface only, no LLM processing  
  - **Stewie Bot** (:5004): Discord interface only, no LLM processing
- **Storage Systems**:
  - **MongoDB Database**: Stores conversation history, quality ratings, prompt versions, and performance metrics
  - **Chroma Vector DB**: Vector database for RAG system, storing Family Guy wiki embeddings
- **External Dependencies**:
  - **Ollama**: Provides centralized AI language model capabilities
  - **Sentence Transformers**: Text embedding generation for RAG system

### Communication Flow
1. **Discord Message Reception**: Individual bots receive Discord messages
2. **Orchestrator Routing**: Messages sent to orchestrator for processing
3. **Conversation Analysis**: LLM coordinator analyzes message context and conversation history
4. **Character Selection**: Intelligent selection of most appropriate responding character based on:
   - Character personality and expertise areas
   - Recent activity balance
   - Topic relevance and triggers
   - RAG context about the conversation topic
5. **RAG Context Retrieval**: Relevant Family Guy universe knowledge retrieved from vector database
6. **Quality-Controlled Response Generation**: 
   - Generate response using character-specific prompts (optimized if available)
   - LLM auto-assessment evaluates response quality (1-5 scale)
   - Quality control agent ensures response meets minimum standards (≥3.0/5)
   - Retry generation if quality insufficient (max 3 attempts)
7. **Response Delivery**: Approved high-quality response sent to appropriate bot
8. **Discord Output**: Bot posts response to Discord channel
9. **Learning and Optimization**: 
   - Response quality data stored for continuous learning
   - Background optimization triggers when performance drops
   - A/B testing validates prompt improvements
10. **Persistence**: Conversations, ratings, and metrics stored in MongoDB

### Character Response Generation
The orchestrator maintains distinct personality prompts for each character:

#### Peter Griffin
- **Personality**: Lovably dim-witted, impulsive, childlike innocence
- **Speech Patterns**: "Hehehehehe" laugh, "Holy crap!", random tangents
- **Vocabulary**: Simple words, frequent mispronunciations, dated references

#### Brian Griffin  
- **Personality**: Pseudo-intellectual, aspiring writer, cynical worldview
- **Speech Patterns**: "Well, actually...", sophisticated vocabulary, literary quotes
- **Behavior**: Condescending, philosophical, occasional vulnerability

#### Stewie Griffin
- **Personality**: Evil genius baby, sophisticated intellect, British mannerisms  
- **Speech Patterns**: "What the deuce", "blast", dramatic declarations
- **Behavior**: Megalomaniacal plans mixed with baby moments

### API Endpoints

#### Orchestrator (:5003)
##### Core Functionality
- `POST /orchestrate` - **Main endpoint**: Handles all LLM processing and conversation management
- `GET /health` - Health check with component status

##### RAG System
- `POST /load_fandom_wiki` - RAG document loading and processing

##### Supervised Fine-Tuning System
- `POST /rate_response` - Rate character responses (manual or automated)
- `GET /fine_tuning_stats` - Overall system performance statistics
- `GET /optimization_report?days=7` - Character optimization reports
- `GET /prompt_performance?character=Peter&days=30` - Detailed character performance metrics
- `POST /trigger_optimization` - Manually trigger prompt optimization for character
- `GET /quality_control_status` - Quality control statistics and configuration

#### Individual Bots (:5002, :5004, :5005)
- `POST /send_discord_message` - Send orchestrator-generated message to Discord
- `POST /initiate_conversation` - Start new conversation (organic conversations)
- `GET /health` - Bot health and Discord connection status
- ~~`POST /generate_llm_response`~~ - **REMOVED** (now handled by orchestrator)

### Error Handling

The centralized architecture includes comprehensive error handling:

#### Orchestrator Level
- **LLM Generation Failures**: Retry logic with exponential backoff
- **Character Prompt Errors**: Fallback to generic responses
- **RAG System Issues**: Graceful degradation without context
- **Dead Letter Queue**: Failed messages queued for later retry

#### Bot Level  
- **Discord Connection Issues**: Automatic reconnection attempts
- **Message Delivery Failures**: Error reporting to orchestrator
- **API Communication**: Timeout handling and retry mechanisms

#### System Level
- **MongoDB Connection**: Connection pooling and retry logic
- **Vector Store Issues**: Fallback to non-RAG responses
- **Resource Exhaustion**: Graceful degradation and logging

### Performance Optimizations

#### Resource Efficiency
- **Single LLM Instance**: ~66% reduction in memory usage
- **Shared Context Processing**: Eliminate duplicate RAG operations  
- **Connection Pooling**: Efficient database and API connections
- **Response Caching**: Future enhancement for similar queries

#### Scalability Features
- **Horizontal Scaling**: Orchestrator can be scaled independently
- **Load Balancing**: Future support for multiple orchestrator instances
- **Async Processing**: Non-blocking message handling
- **Queue Management**: Buffering for high-traffic scenarios

## Contributing

Feel free to fork the repository and submit pull requests for any improvements you'd like to add. Some areas for potential enhancement:
- Additional Family Guy characters
- More sophisticated conversation handling
- Enhanced error recovery
- Improved natural language processing
- Advanced conversation orchestration
- Custom personality fine-tuning
- Extended conversation history analysis
- Enhanced organic conversation triggers and pattern detection
- **Metrics collection and monitoring system**
- **Centralized alerting and notification system**
- **Enhanced security and authentication layer**
- **Separate message queue system**
- **Advanced performance monitoring and analytics**

## Documentation

For detailed information about specific systems:
- **[Supervised Fine-Tuning System Guide](docs/FINE_TUNING_GUIDE.md)** - Complete documentation on the automatic quality improvement system
- **[Architecture Validation](tests/test_architecture_validation.py)** - Automated testing and validation
- **[Performance Benchmarking](scripts/performance_benchmark.py)** - System performance testing

## License

This project is licensed under the MIT License.

```text
MIT License

Copyright (c) 2024 DapeSec

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## Running Locally (Development)

1. Set up your virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Linux/macOS
   # OR
   .venv\Scripts\activate     # Windows
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Start the bots individually:
   ```bash
   # Start the orchestrator
   python -m src.app.orchestrator.server

   # Start individual bots (in separate terminals)
   python -m src.app.bots.peter_bot
   python -m src.app.bots.brian_bot
   python -m src.app.bots.stewie_bot
   ```

## Running with Docker

1. Build and start all services:
   ```bash
   docker-compose -f docker/docker-compose.yml up --build
   ```

2. Or run in detached mode:
   ```bash
   docker-compose -f docker/docker-compose.yml up -d
   ```

3. View logs:
   ```bash
   docker-compose -f docker/docker-compose.yml logs -f
   ```

4. Stop services:
   ```bash
   docker-compose -f docker/docker-compose.yml down
   ```

## Running Tests

The test suite is designed to validate the centralized LLM architecture:

```bash
# Run all tests
pytest tests/

# Run architecture validation test  
python tests/test_architecture_validation.py

# Run performance benchmark
python scripts/performance_benchmark.py

# Run specific test categories
pytest tests/test_orchestrator.py    # Centralized LLM processing tests
pytest tests/test_bots.py            # Discord interface tests  
pytest tests/test_rag.py             # RAG system tests
pytest tests/test_centralized_llm.py # Architecture-specific tests

# Run with coverage report
pytest --cov=src.app tests/

# Test specific components
pytest tests/test_orchestrator.py::TestCentralizedLLM::test_character_response_generation
pytest tests/test_bots.py::TestBotInterfaces::test_discord_message_handling
```

### Test Categories

#### Architecture Tests (`test_centralized_architecture.py`)
- **Health Endpoints**: Validates all services are running
- **Centralized LLM**: Tests orchestrator's character response generation  
- **Integration**: End-to-end communication between components

#### Orchestrator Tests (`tests/test_orchestrator.py`)
- **Character Response Generation**: Tests centralized LLM with different personalities
- **Prompt Template Processing**: Validates character-specific prompts
- **RAG Integration**: Tests context retrieval and augmentation
- **Dead Letter Queue**: Error handling and retry mechanisms

#### Bot Tests (`tests/test_bots.py`)  
- **Discord Interface**: Message handling and sending capabilities
- **Health Checks**: Bot status and connectivity validation
- **API Endpoints**: `/send_discord_message` and `/initiate_conversation`

#### RAG Tests (`tests/test_rag.py`)
- **Document Processing**: Vector store operations
- **Context Retrieval**: Similarity search functionality
- **Embedding Generation**: Text vectorization

### Running Architecture Validation

The `tests/test_architecture_validation.py` script provides comprehensive validation:
```bash
python tests/test_architecture_validation.py
```

Expected output:
```
============================================================
CENTRALIZED LLM ARCHITECTURE TEST
============================================================

Testing health endpoints...
Orchestrator: ✅ Healthy
Peter Bot: ✅ Healthy  
Brian Bot: ✅ Healthy
Stewie Bot: ✅ Healthy

Testing centralized LLM architecture...
✅ Centralized LLM architecture test passed!

============================================================
ARCHITECTURE SUMMARY:
- Orchestrator handles all LLM processing
- Each bot only handles Discord interactions  
- RAG context is centralized in orchestrator
- Character personalities maintained via prompts
============================================================
```

## Docker Setup

### Prerequisites
1. Install Docker and Docker Compose
2. Install Ollama on your host machine from [ollama.ai](https://ollama.ai/)
3. Make sure ports 5002-5005 and 27017 are available
4. Ensure your GPU drivers are properly installed (for Ollama)

### Setup Steps

1. **Start Ollama on your host machine**
   ```bash
   # Start Ollama service
   ollama serve

   # In another terminal, pull the Mistral model
   ollama pull mistral
   ```

2. **Configure Environment**
   Create a `.env` file with your configuration:
   ```
   # Discord Bot Tokens
   DISCORD_BOT_TOKEN_PETER=your_peter_bot_token_here
   DISCORD_BOT_TOKEN_BRIAN=your_brian_bot_token_here
   DISCORD_BOT_TOKEN_STEWIE=your_stewie_bot_token_here

   # MongoDB Configuration
   MONGO_URI=mongodb://mongodb:27017/
   MONGO_DB_NAME=discord_bot_conversations
   MONGO_COLLECTION_NAME=conversations

   # Ollama Configuration
   OLLAMA_BASE_URL=http://host.docker.internal:11434
   
   # Organic Conversation Configuration (Optional)
   CONVERSATION_SILENCE_THRESHOLD_MINUTES=30  # Minutes of silence before considering new conversation
   MIN_TIME_BETWEEN_ORGANIC_CONVERSATIONS=10  # Minimum minutes between organic attempts
   DEFAULT_DISCORD_CHANNEL_ID=your_default_channel_id  # For organic conversations
   
   # RAG System Configuration
   FANDOM_WIKI_START_URL=https://familyguy.fandom.com/wiki/Main_Page
   FANDOM_WIKI_MAX_PAGES=100
   FANDOM_WIKI_CRAWL_DELAY=1
   ```

3. **Build and Run Containers**
   ```bash
   # Build and start all services
   docker-compose up --build

   # Or run in detached mode
   docker-compose up -d
   ```

4. **Verify Setup**
   ```bash
   # Check running containers
   docker-compose ps

   # Check logs
   docker-compose logs -f
   ```

### Architecture Notes
- Ollama runs on the host machine to utilize GPU resources
- MongoDB runs in a container with persistent storage
- Bot services and orchestrator run in separate containers
- All services communicate over a dedicated Docker network
- Logs and Chroma DB are persisted through volume mounts

### Container Management
```bash
# Stop all services
docker-compose down

# Restart a specific service
docker-compose restart peter

# View logs for a specific service
docker-compose logs -f orchestrator
```

### Troubleshooting
1. **Ollama Connection Issues**
   - Verify Ollama is running on the host: `curl http://localhost:11434/api/tags`
   - Check if the model is pulled: `ollama list`
   - Ensure host.docker.internal resolves correctly
   - For Linux hosts, add `--add-host=host.docker.internal:host-gateway` to your docker run command

2. **GPU Access**
   - Verify GPU is recognized by Ollama: `nvidia-smi`