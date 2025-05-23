# Family Guy Discord Bots

An interactive Discord bot system featuring Peter Griffin, Brian Griffin, and Stewie Griffin from Family Guy. The bots use a **centralized LLM architecture** where the orchestrator handles all language model processing through Ollama, generating responses in characteristic styles for each bot. This design provides better resource efficiency, consistency, and maintainability while preserving the unique personalities of each character.

## Table of Contents
1. [System Architecture](#system-architecture)
2. [Features](#features)
3. [Project Structure](#project-structure)
4. [Prerequisites](#prerequisites)
5. [Installation](#installation)
6. [Docker Setup](#docker-setup)
7. [Usage](#usage)
8. [Technical Details](#technical-details)
9. [Architecture Benefits](#architecture-benefits)
10. [Contributing](#contributing)
11. [License](#license)

## System Architecture

```mermaid
graph TD
    subgraph Discord["Discord Platform"]
        DC[Discord Channels]
        DAuth[Discord Auth]
    end

    subgraph Host["Host Machine"]
        OL[Ollama LLM<br>GPU Accelerated]
        ML[Model Loading<br>& Caching]
    end

    subgraph Docker["Docker Environment"]
        subgraph Orchestrator["Orchestrator Container"]
            OS[Orchestrator Service<br>:5003]
            CL[Centralized LLM<br>Processing]
            CP[Character Prompts<br>& Personalities]
            DLQ[Dead Letter<br>Queue]
            
            subgraph RAG["RAG System (Integrated)"]
                VDB[(Chroma DB)]
            end
        end

        subgraph Bots["Bot Containers (Discord Only)"]
            PB[Peter Bot<br>:5005<br>Discord Interface]
            BB[Brian Bot<br>:5002<br>Discord Interface]
            SB[Stewie Bot<br>:5004<br>Discord Interface]
        end

        subgraph Storage["Storage Layer"]
            MDB[(MongoDB<br>:27017)]
            Log[(Log Storage)]
        end
    end

    DC <--> DAuth
    DAuth <--> PB & BB & SB
    
    PB & BB & SB --> OS
    OS --> CL
    CL --> CP
    CL --> OL
    OL --> ML
    
    OS --> DLQ
    
    OS --> VDB
    VDB --> CL
    
    OS --> MDB
    PB & BB & SB --> Log

    style Discord fill:#7289DA,color:white
    style Docker fill:#4CAF50,color:white
    style Host fill:#FF9800,color:white
    style Storage fill:#2196F3,color:white
    style RAG fill:#009688,color:white
    style Orchestrator fill:#FF5722,color:white
```

## Features

- **Centralized LLM Architecture**: Single Ollama instance handles all language processing
- **Character-Specific Prompts**: Unique personalities maintained through specialized prompt templates
- **Resource Efficient**: ~66% reduction in memory usage compared to distributed LLM setup
- Three distinct bot personalities:
  - **Peter**: Humorous, dim-witted, with tangents and "Heheheh" interjections
  - **Brian**: Intellectual, sarcastic, sophisticated vocabulary and cultural references
  - **Stewie**: Evil genius baby with British accent, scientific knowledge, and megalomaniacal plans
- **Simplified Bot Architecture**: Bots handle only Discord interactions, not LLM processing
- **Containerized Microservices**: Each component runs in isolated containers
- **GPU-Accelerated Responses**: Leverages host Ollama for fast generation
- **RAG System**: Context-aware responses using Chroma DB vector store
- **Persistent Conversations**: MongoDB stores complete conversation history
- **Multi-Bot Interactions**: Natural conversation flow between characters
- **Automated Conversations**: Daily scheduled interactions for continuous engagement
- **Dead Letter Queue**: Robust error handling and message retry system
- **Basic Health Checks**: Health endpoints for service monitoring

## Architecture Benefits

### Centralized LLM Processing
- **Resource Efficiency**: Single LLM instance instead of three separate ones
- **Consistency**: Unified prompt management and response processing
- **Maintainability**: Single point for LLM configuration and updates
- **Scalability**: Easier to implement load balancing and caching

### Simplified Bot Design
- **Focus**: Bots handle only Discord interactions
- **Reliability**: Reduced complexity means fewer failure points
- **Performance**: Faster startup and lower resource usage per bot
- **Debugging**: Easier to troubleshoot Discord-specific issues

### Enhanced Control
- **Rate Limiting**: Centralized control over LLM usage
- **Safety**: Single point for content filtering and moderation
- **Monitoring**: Unified metrics and logging for LLM operations
- **Cost Management**: Better tracking of token usage and API calls

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
   Create a `.env` file in the project root:
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
2. The primary bot generates its response
3. Other bots may join the conversation naturally
4. The orchestrator manages the conversation flow and timing
5. All conversations are stored in MongoDB for context

### Automated Conversations
The system includes an automated feature that initiates random conversations throughout the day:
- Configurable number of daily conversations
- Dynamic conversation starters based on context
- Natural interaction between characters
- Helps maintain channel activity

## Technical Details

### System Components
- **Orchestrator Server** (:5003): 
  - Central message handler and conversation manager
  - **Centralized LLM Processing**: Single Ollama instance for all character responses
  - **Character Prompts**: Maintains personality-specific prompt templates
  - **RAG Integration**: Context retrieval and augmentation
  - **Dead Letter Queue**: Error handling and message retry system
- **Character Bots**: 
  - **Peter Bot** (:5005): Discord interface only, no LLM processing
  - **Brian Bot** (:5002): Discord interface only, no LLM processing  
  - **Stewie Bot** (:5004): Discord interface only, no LLM processing
- **MongoDB Database**: Stores conversation history and context
- **Chroma DB**: Vector database for RAG system, storing embeddings for contextual retrieval
- **Ollama**: Provides centralized AI language model capabilities
- **RAG System**: Enhances responses with relevant context from the vector database

### Communication Flow
1. **Discord Message Reception**: Individual bots receive Discord messages
2. **Orchestrator Routing**: Messages sent to orchestrator for processing
3. **Centralized LLM Processing**: 
   - Orchestrator determines responding character
   - Applies character-specific prompt template
   - Retrieves RAG context if relevant
   - Generates response using centralized Ollama instance
4. **Response Delivery**: Orchestrator sends generated response back to appropriate bot
5. **Discord Output**: Bot posts response to Discord channel
6. **Persistence**: Conversations stored in MongoDB and vectorized for RAG

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
- `POST /orchestrate` - **Main endpoint**: Handles all LLM processing and conversation management
- `GET /health` - Health check with component status
- `POST /load_fandom_wiki` - RAG document loading and processing

#### Individual Bots (:5002, :5004, :5005)
- `POST /send_discord_message` - Send orchestrator-generated message to Discord
- `POST /initiate_conversation` - Start new conversation (scheduled conversations)
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
- Improved automated conversation triggers
- **Metrics collection and monitoring system**
- **Centralized alerting and notification system**
- **Enhanced security and authentication layer**
- **Separate message queue system**
- **Advanced performance monitoring and analytics**

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
   - Check Ollama logs for GPU initialization
   - Ensure CUDA drivers are installed
   - For Docker, ensure nvidia-container-toolkit is installed
   - Check GPU memory usage isn't maxed out

3. **MongoDB Connection Issues**
   - Verify MongoDB container is running: `docker ps | grep mongodb`
   - Check MongoDB logs: `docker-compose logs mongodb`
   - Ensure correct credentials in .env file
   - Check if MongoDB port is not conflicting with local installation

4. **Bot Communication Issues**
   - Verify all services are running: `docker-compose ps`
   - Check individual bot logs: `docker-compose logs <service_name>`
   - Ensure Discord bot tokens are valid
   - Check Discord bot permissions
   - Verify network connectivity between containers

5. **Performance Issues**
   - Monitor container resource usage: `docker stats`
   - Check host system resources
   - Verify GPU utilization if applicable
   - Consider adjusting container resource limits
   - Monitor MongoDB performance metrics

### Logs Location
- Container logs: `docker-compose logs`
- Application logs: `./logs/` directory
- Ollama logs: System-dependent location
  - Linux: `/var/log/ollama.log`
  - Windows: Event Viewer
  - macOS: Console.app

### Getting Help
- Open an issue on GitHub
- Check existing issues for similar problems
- Join our Discord community for support
- Review the documentation

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